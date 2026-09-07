"""The /search route: stage 1 candidates at once, stage 2 progress and results as they come."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Iterator
from typing import Any

from flask import Blueprint, Response, request

from sidecar.application.search import STAGE_ONE_CANDIDATE_LIMIT, Search
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.search import PageHit
from sidecar.interface.errors import error_response
from sidecar.interface.sse import encode_event

logger = logging.getLogger(__name__)

_MISSING_QUERY_MESSAGE = "A search needs a q parameter. Add q to the URL, empty when nothing is typed."
_INVALID_LIMIT_MESSAGE = "The limit takes a whole number above zero. Pass one, or leave it out for the default."

# A buffering proxy holds a streamed response until it closes, which would land
# a stage 1 event that took milliseconds only once the whole stream is over.
_STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}

StageTwoEvent = tuple[str, Any]


def build_search_blueprint(search: Search) -> Blueprint:
    """Build the /search blueprint bound to one Search use case.

    The stream is `candidates`, zero or more `progress`, `results`, then exactly
    one `done`. `done` carries the count and whether stage 2 ran, so a client
    that reads only the terminal event still knows what it got.

    A blank or whitespace q streams an empty candidate list and closes without
    touching the model: nothing typed is neither an error nor a request for
    the whole index. A missing q and a limit that is not a positive integer
    are both 400 before the stream opens, because a caller that built the URL
    wrong needs a status code rather than a stream that ends empty.
    """
    bp = Blueprint("search", __name__)

    @bp.get("/search")
    def stream_search() -> Response:
        query = request.args.get("q")
        if query is None:
            return error_response("missing_query", _MISSING_QUERY_MESSAGE, status=400)

        limit = _limit_from(request.args.get("limit"))
        if limit is None:
            return error_response("invalid_limit", _INVALID_LIMIT_MESSAGE, status=400)

        # Stage one runs before the response opens. Once the stream is on the
        # wire, the only way left to report a failure is an event inside a 200.
        hits, took_ms = _timed_stage_one(search, query, limit)
        events = _events(search, query, hits, took_ms) if query.strip() else _blank_events(took_ms)
        return Response(events, mimetype="text/event-stream", headers=_STREAM_HEADERS)

    return bp


def _limit_from(raw: str | None) -> int | None:
    """The requested limit, the use case default when none was asked for, `None` when it is not a positive integer."""
    if raw is None:
        return STAGE_ONE_CANDIDATE_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        return None
    return limit if limit > 0 else None


def _timed_stage_one(search: Search, query: str, limit: int) -> tuple[list[PageHit], int]:
    started = time.perf_counter()
    hits = search.stage_one(query, limit)
    return hits, round((time.perf_counter() - started) * 1000)


def _blank_events(took_ms: int) -> Iterator[str]:
    yield encode_event("candidates", {"hits": [], "took_ms": took_ms})
    yield encode_event("done", {"count": 0, "stage2": "skipped"})


def _events(search: Search, query: str, candidates: list[PageHit], stage1_ms: int) -> Iterator[str]:
    """Stage 2 runs on its own thread so progress can be written while the model works.

    The generator drains a queue the worker fills. Closing the generator, which
    is what a client hanging up does, sets the flag stage 2 checks between
    chunks, so an abandoned search stops costing model time within one chunk.
    A failure in stage 2 is logged and the stream still ends in `done`: the
    stage 1 candidates on screen are real results, and blanking them for an
    enhancement that failed would be worse than the failure.
    """
    yield encode_event("candidates", {"hits": [_hit_payload(hit) for hit in candidates], "took_ms": stage1_ms})

    events: queue.Queue[StageTwoEvent] = queue.Queue()
    cancelled = threading.Event()

    def work() -> None:
        started = time.perf_counter()
        try:
            results = search.stage_two(
                query,
                candidates,
                on_progress=lambda progress: events.put(("progress", progress)),
                is_cancelled=cancelled.is_set,
            )
            events.put(("results", (results, round((time.perf_counter() - started) * 1000))))
        except Exception:
            logger.exception("stage 2 failed for %r", query)
            events.put(("failed", None))

    threading.Thread(target=work, name="search-stage-two", daemon=True).start()
    try:
        while True:
            kind, payload = events.get()
            if kind == "progress":
                yield encode_event("progress", _progress_payload(payload))
            elif kind == "results":
                results, stage2_ms = payload
                yield encode_event("results", {"hits": [_hit_payload(hit) for hit in results], "took_ms": stage2_ms})
                yield encode_event("done", {"count": len(results), "stage2": "ok"})
                return
            else:
                yield encode_event("done", {"count": len(candidates), "stage2": "failed"})
                return
    finally:
        cancelled.set()


def _progress_payload(progress: EmbedProgress) -> dict[str, Any]:
    return {
        "pages_read": progress.pages_read,
        "pages_total": progress.pages_total,
        "current_page_id": progress.current_page_id,
    }


def _hit_payload(hit: PageHit) -> dict[str, Any]:
    return {
        "page_id": hit.page_id,
        "file_id": hit.file_id,
        "path": str(hit.path),
        "page_no": hit.page_no,
        "kind": hit.kind.value,
        "score": hit.score,
        "stage": hit.stage,
        "snippet": hit.snippet,
    }
