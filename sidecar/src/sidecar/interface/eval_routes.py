"""The /eval routes: run the golden set against the live index and stream what each query did."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from queue import Queue
from typing import Any

from flask import Blueprint, Response, request

from sidecar.application.run_golden_set import RunGoldenSet
from sidecar.domain.errors import ValidationError
from sidecar.domain.evaluation import GoldenQuery, QueryOutcome
from sidecar.interface.errors import error_response
from sidecar.interface.sse import encode_event

logger = logging.getLogger(__name__)

_RUN_FAILED_MESSAGE = "The golden run stopped before it finished. Check the sidecar log for the cause."

# A buffering proxy would hold thirty queries' worth of events until the run
# ends, which turns a progress stream into one report delivered afterwards.
_STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


class _InvalidGoldenSetError(Exception):
    """The body is not a golden set. The message names the first thing wrong with it."""


class _ClientGoneError(Exception):
    """Raised inside a callback once the response generator has been closed."""


def build_eval_blueprint(run_golden_set: RunGoldenSet) -> Blueprint:
    """Build the /eval blueprint bound to one RunGoldenSet use case.

    The stream is `progress` before each query, `query` after it, and exactly
    one `done` carrying the aggregates. A body that is not a golden set is a
    400 before the stream opens, because once the response is on the wire the
    only way left to report a bad request is an event inside a 200.
    """
    bp = Blueprint("eval", __name__)

    @bp.post("/eval/golden/run")
    def run_golden() -> Response:
        try:
            corpus_root, queries = _parse_golden_set(request.get_json(silent=True))
        except _InvalidGoldenSetError as exc:
            return error_response("invalid_golden_set", str(exc), status=400)
        stream = _GoldenRunStream(run_golden_set, corpus_root, queries)
        return Response(stream.events(), mimetype="text/event-stream", headers=_STREAM_HEADERS)

    return bp


def _parse_golden_set(body: object) -> tuple[Path, list[GoldenQuery]]:
    if not isinstance(body, dict):
        raise _InvalidGoldenSetError("The body is a JSON object with corpus_root and queries.")
    corpus_root = body.get("corpus_root")
    if not isinstance(corpus_root, str) or not Path(corpus_root).is_absolute():
        raise _InvalidGoldenSetError("corpus_root is an absolute path.")
    rows = body.get("queries")
    if not isinstance(rows, list) or not rows:
        raise _InvalidGoldenSetError("queries is a list with at least one query.")
    return Path(corpus_root), [_parse_query(row, position) for position, row in enumerate(rows, start=1)]


def _parse_query(row: object, position: int) -> GoldenQuery:
    if not isinstance(row, dict):
        raise _InvalidGoldenSetError(f"Query {position} is a JSON object.")
    try:
        return GoldenQuery(
            id=_field(row, "id", str, position),
            query=_field(row, "query", str, position),
            expected_file=Path(_field(row, "expected_file", str, position)),
            expected_page=_field(row, "expected_page", int, position),
            text_free=_field(row, "text_free", bool, position),
            match_channel=_field(row, "match_channel", str, position),
        )
    except ValidationError as exc:
        raise _InvalidGoldenSetError(f"Query {position}: {exc.message}") from exc


def _field(row: dict[str, Any], key: str, kind: type, position: int) -> Any:
    value = row.get(key)
    # bool is an int in Python, and a page number of `true` is a typo, not page 1.
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise _InvalidGoldenSetError(f"Query {position} needs {key} as a {kind.__name__}.")
    return value


class _GoldenRunStream:
    """Turns the use case's callbacks into SSE events.

    The use case runs on a worker thread and the response drains a queue,
    because a Flask generator cannot yield from inside a callback. Closing
    the generator, which is what a client hanging up does, marks the stream
    abandoned, and the next callback raises to stop the run instead of
    embedding pages for nobody.
    """

    def __init__(self, run_golden_set: RunGoldenSet, corpus_root: Path, queries: list[GoldenQuery]) -> None:
        self._run_golden_set = run_golden_set
        self._corpus_root = corpus_root
        self._queries = queries
        self._events: Queue[str | None] = Queue()
        self._abandoned = False

    def events(self) -> Iterator[str]:
        threading.Thread(target=self._work, name="golden-run", daemon=True).start()
        try:
            while (event := self._events.get()) is not None:
                yield event
        finally:
            self._abandoned = True

    def _work(self) -> None:
        try:
            aggregates = self._run_golden_set.run(self._corpus_root, self._queries, self._on_progress, self._on_outcome)
            self._events.put(encode_event("done", {"aggregates": asdict(aggregates)}))
        except _ClientGoneError:
            logger.info("golden run abandoned: the client went away")
        except Exception:
            logger.exception("golden run failed")
            self._events.put(encode_event("error", {"code": "golden_run_failed", "message": _RUN_FAILED_MESSAGE}))
        finally:
            self._events.put(None)

    def _on_progress(self, done: int, total: int) -> None:
        self._emit("progress", {"done": done, "total": total})

    def _on_outcome(self, outcome: QueryOutcome) -> None:
        self._emit("query", _query_payload(outcome))

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self._abandoned:
            raise _ClientGoneError
        self._events.put(encode_event(name, payload))


def _query_payload(outcome: QueryOutcome) -> dict[str, Any]:
    golden = outcome.golden
    return {
        "id": golden.id,
        "query": golden.query,
        "expected": {"file": str(golden.expected_file), "page": golden.expected_page},
        "text_free": golden.text_free,
        "match_channel": golden.match_channel,
        "candidates": outcome.candidates,
        "stage1_rank": outcome.stage1_rank,
        "embedded_before_run": outcome.embedded_before_run,
        "cap_miss": outcome.cap_miss,
        "visual_only": outcome.visual_only,
        "top10": [
            {
                "page_id": page.page_id,
                "file": str(page.file),
                "page": page.page,
                "score": page.score,
                "stage": page.stage,
            }
            for page in outcome.top10
        ],
        "rank": outcome.rank,
        "hit1": outcome.hit1,
        "hit5": outcome.hit5,
        "hit10": outcome.hit10,
        "stage1_ms": outcome.stage1_ms,
        "stage2_ms": outcome.stage2_ms,
        "cold_pages": outcome.cold_pages,
    }
