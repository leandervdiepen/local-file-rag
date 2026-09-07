"""The /search route: stage 1 full text candidates, streamed."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from flask import Blueprint, Response, request

from sidecar.application.search import STAGE_ONE_CANDIDATE_LIMIT, Search
from sidecar.domain.search import PageHit
from sidecar.interface.errors import error_response
from sidecar.interface.sse import encode_event

_MISSING_QUERY_MESSAGE = "A search needs a q parameter. Add q to the URL, empty when nothing is typed."
_INVALID_LIMIT_MESSAGE = "The limit takes a whole number above zero. Pass one, or leave it out for the default."

# A buffering proxy holds a streamed response until it closes, which would land
# a stage 1 event that took milliseconds only once the whole stream is over.
_STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


def build_search_blueprint(search: Search) -> Blueprint:
    """Build the /search blueprint bound to one Search use case.

    The stream is `candidates` then exactly one `done`, and `done` carries the
    count, so a client that reads only the terminal event still knows what it got.

    A blank or whitespace q streams an empty candidate list: nothing typed is
    neither an error nor a request for the whole index. A missing q and a limit
    that is not a positive integer are both 400 before the stream opens, because
    a caller that built the URL wrong needs a status code rather than a stream
    that ends empty.
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
        return Response(_events(hits, took_ms), mimetype="text/event-stream", headers=_STREAM_HEADERS)

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
    """Stage one candidates, and the milliseconds that one call took."""
    started = time.perf_counter()
    hits = search.stage_one(query, limit)
    return hits, round((time.perf_counter() - started) * 1000)


def _events(hits: list[PageHit], took_ms: int) -> Iterator[str]:
    yield encode_event("candidates", {"hits": [_hit_payload(hit) for hit in hits], "took_ms": took_ms})
    yield encode_event("done", {"count": len(hits)})


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
