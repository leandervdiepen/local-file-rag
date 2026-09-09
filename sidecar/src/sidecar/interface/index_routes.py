"""The /index routes: start a rescan, read the counts, watch a job run."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict
from typing import Any

from flask import Blueprint, Response, jsonify, request

from sidecar.application.forget_file import ForgetFile
from sidecar.application.indexing_jobs import IndexingJobs
from sidecar.application.list_index_files import ListIndexFiles
from sidecar.application.read_index_stats import ReadIndexStats
from sidecar.domain.entities import FileState, IndexedFile
from sidecar.domain.progress import IndexProgress
from sidecar.domain.search import IndexStats
from sidecar.interface.errors import error_response
from sidecar.interface.sse import encode_event

_NO_JOB_YET = IndexProgress(folder_id="", done=True)

# The index changes under the reader, so a count served from a cache is a
# wrong count, and a proxy that buffers turns a live stream into one report
# delivered after the crawl it was describing has finished.
_LIVE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


_INVALID_STATE_MESSAGE = "That is not a file state. Ask for text_indexed or skipped."


def build_index_blueprint(
    jobs: IndexingJobs,
    read_stats: ReadIndexStats,
    list_files: ListIndexFiles,
    forget_file: ForgetFile,
) -> Blueprint:
    """Build the /index blueprint bound to one job runner and one stats use case."""
    bp = Blueprint("index", __name__)

    @bp.post("/index/rescan")
    def rescan() -> Response:
        accepted = jsonify({"job_id": jobs.start()})
        accepted.status_code = 202
        return accepted

    @bp.get("/index/stats")
    def stats() -> Response:
        response = jsonify(_stats_body(read_stats.run()))
        response.headers["Cache-Control"] = "no-store"
        return response

    @bp.get("/index/files")
    def files() -> Response:
        wanted = request.args.get("state", FileState.TEXT_INDEXED.value)
        try:
            state = FileState(wanted)
        except ValueError:
            return error_response("invalid_state", _INVALID_STATE_MESSAGE, status=400, detail={"state": wanted})

        page = list_files.run(state, request.args.get("cursor"))
        response = jsonify(
            {
                "files": [_file_body(file) for file in page.files],
                "next_cursor": page.next_cursor,
            }
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @bp.delete("/index/files/<file_id>")
    def forget(file_id: str) -> Response:
        forget_file.run(file_id)
        return Response(status=204)

    @bp.get("/index/progress")
    def progress() -> Response:
        return Response(_progress_events(jobs), mimetype="text/event-stream", headers=_LIVE_HEADERS)

    return bp


def _file_body(file: IndexedFile) -> dict[str, Any]:
    """One row of the index screen. `skip_reason` is what the screen shows instead of a page count."""
    return {
        "id": file.id,
        "path": str(file.path),
        "kind": file.kind.value,
        "state": file.state.value,
        "skip_reason": file.skip_reason,
        "size_bytes": file.size_bytes,
        "page_count": file.page_count,
        "truncated_pages": file.truncated_pages,
    }


def _stats_body(stats: IndexStats) -> dict[str, Any]:
    """The wire shape of the index counts.

    `skips_by_reason` is a tuple of pairs in the domain because a frozen
    dataclass needs hashable fields, and an object here because a client
    reads it by reason.
    """
    body = asdict(stats)
    body["skips_by_reason"] = dict(stats.skips_by_reason)
    return body


def _progress_events(jobs: IndexingJobs) -> Iterator[str]:
    """Every snapshot as a `progress` event, then exactly one terminal `done`.

    With no job running there is nothing to wait for, so the stream is the
    last known snapshot as `done` and a close. A client that connects between
    two jobs gets an answer rather than an open socket.
    """
    final: IndexProgress | None = None
    for snapshot in jobs.subscribe():
        if snapshot.done:
            final = snapshot
            break
        yield encode_event("progress", asdict(snapshot))

    if final is None:
        final = jobs.progress() or _NO_JOB_YET
    yield encode_event("done", asdict(final))
