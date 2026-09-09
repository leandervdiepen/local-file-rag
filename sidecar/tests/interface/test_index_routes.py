"""The wire shape of the /index routes. Fake ports, real Flask, real SSE bytes.

This is the contract the renderer is written against, so every assertion is
about what goes over the socket: status, keys, headers, event names.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.forget_file import ForgetFile
from sidecar.application.indexing_jobs import IndexingJobs
from sidecar.application.list_index_files import ListIndexFiles
from sidecar.application.read_index_stats import ReadIndexStats
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.errors import IndexBusyError
from sidecar.domain.progress import IndexProgress
from sidecar.domain.vectors import VECTOR_DIM, PageVectors
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.index_routes import build_index_blueprint
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.vector_store import FakeVectorStore

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
JOB_ID = "0123456789abcdef0123456789abcdef"
BUSY_MESSAGE = "A rescan is already running. Wait for it to finish before starting another."
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class FakeIndexingJobs:
    """A real, working stand-in for `IndexingJobs`, with the thread taken out.

    A job is a list of snapshots that is already complete, so what the SSE
    route writes is decided by what the test seeded rather than by when a
    background thread got scheduled.
    """

    def __init__(self, snapshots: list[IndexProgress] | None = None, running: bool = False) -> None:
        self.snapshots = snapshots or []
        self.running = running
        self.busy = False
        self.starts = 0

    def start(self) -> str:
        if self.busy:
            raise IndexBusyError(BUSY_MESSAGE)
        self.starts += 1
        return JOB_ID

    def is_running(self) -> bool:
        return self.running

    def progress(self) -> IndexProgress | None:
        return self.snapshots[-1] if self.snapshots else None

    def subscribe(self) -> Iterator[IndexProgress]:
        return iter(self.snapshots) if self.running else iter(())


def _client(
    jobs: FakeIndexingJobs, store: FakeIndexStore | None = None, vectors: FakeVectorStore | None = None
) -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    index = store if store is not None else FakeIndexStore()
    page_vectors = vectors or FakeVectorStore()
    read_stats = ReadIndexStats(index, page_vectors)
    app.register_blueprint(
        build_index_blueprint(
            cast(IndexingJobs, jobs), read_stats, ListIndexFiles(index), ForgetFile(index, page_vectors)
        )
    )
    return app.test_client()


def _events(payload: str) -> list[tuple[str, Any]]:
    """The stream as the pairs a client parses out of it: event name, JSON payload."""
    parsed: list[tuple[str, Any]] = []
    for block in [block for block in payload.split("\n\n") if block.strip()]:
        name, data = block.split("\n", 1)
        parsed.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return parsed


def _a_file(
    file_id: str, size_bytes: int, state: FileState, skip_reason: str | None = None, path: Path | None = None
) -> IndexedFile:
    return IndexedFile(
        id=file_id,
        path=path or Path(f"/corpus/{file_id}.pdf"),
        folder_id="folder-1",
        content_hash="abc",
        size_bytes=size_bytes,
        mtime=NOW,
        kind=FileKind.PDF,
        state=state,
        skip_reason=skip_reason,
    )


def _a_stocked_store() -> FakeIndexStore:
    """One indexed file with two pages and one file the gate refused."""
    store = FakeIndexStore()
    store.upsert_file(_a_file("file-1", 1000, FileState.TEXT_INDEXED))
    store.upsert_pages([Page(id="page-1", file_id="file-1", page_no=1), Page(id="page-2", file_id="file-1", page_no=2)])
    store.upsert_file(_a_file("file-2", 200, FileState.SKIPPED, skip_reason="too_large"))
    return store


def _vectors_for(page_ids: list[str]) -> FakeVectorStore:
    """A vector store holding vectors for these pages, which is what `pages_embedded` counts."""
    vectors = FakeVectorStore()
    rows = np.ones((4, VECTOR_DIM), dtype=np.float16)
    vectors.put_vectors([PageVectors(page_id=page_id, vectors=rows, pool_factor=3) for page_id in page_ids])
    return vectors


def test_rescan_returns_202_with_the_job_id() -> None:
    jobs = FakeIndexingJobs()

    response = _client(jobs).post("/index/rescan", headers=AUTH)

    assert response.status_code == 202
    assert response.get_json() == {"job_id": JOB_ID}
    assert jobs.starts == 1


def test_rescan_returns_409_index_busy_while_a_job_runs() -> None:
    jobs = FakeIndexingJobs()
    jobs.busy = True

    response = _client(jobs).post("/index/rescan", headers=AUTH)

    assert response.status_code == 409
    assert response.get_json() == {"error": {"code": "index_busy", "message": BUSY_MESSAGE, "detail": {}}}


def test_stats_returns_the_counts_with_skips_as_an_object_and_is_never_cached() -> None:
    client = _client(FakeIndexingJobs(), _a_stocked_store(), _vectors_for(["page-1"]))

    response = client.get("/index/stats", headers=AUTH)

    assert response.status_code == 200
    assert response.get_json() == {
        "files_scanned": 2,
        "files_text_indexed": 1,
        "files_skipped": 1,
        "pages_total": 2,
        "pages_embedded": 1,
        "bytes_on_disk": 0,
        "skips_by_reason": {"too_large": 1},
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_progress_streams_a_progress_event_per_snapshot_then_one_done() -> None:
    crawling = IndexProgress(folder_id="folder-1", files_seen=1, files_indexed=1, current_path="/corpus/a.pdf")
    finished = replace(crawling, files_seen=2, files_indexed=2, pages_indexed=5, current_path="", done=True)

    response = _client(FakeIndexingJobs([crawling, finished], running=True)).get("/index/progress", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Accel-Buffering"] == "no"
    events = _events(response.get_data(as_text=True))
    assert [name for name, _ in events] == ["progress", "done"]
    assert events[0][1] == {
        "folder_id": "folder-1",
        "files_seen": 1,
        "files_indexed": 1,
        "files_skipped": 0,
        "pages_indexed": 0,
        "pages_embedded": 0,
        "current_path": "/corpus/a.pdf",
        "failures": [],
        "done": False,
    }
    assert (events[1][1]["files_seen"], events[1][1]["pages_indexed"], events[1][1]["done"]) == (2, 5, True)


def test_progress_with_no_job_running_sends_the_last_snapshot_and_closes() -> None:
    finished = IndexProgress(folder_id="folder-1", files_seen=9, pages_indexed=20, done=True)

    response = _client(FakeIndexingJobs([finished])).get("/index/progress", headers=AUTH)

    events = _events(response.get_data(as_text=True))
    assert [name for name, _ in events] == ["done"]
    assert (events[0][1]["files_seen"], events[0][1]["pages_indexed"]) == (9, 20)


def test_progress_before_the_first_job_sends_a_zeroed_done() -> None:
    response = _client(FakeIndexingJobs()).get("/index/progress", headers=AUTH)

    events = _events(response.get_data(as_text=True))
    assert [name for name, _ in events] == ["done"]
    assert events[0][1] == {
        "folder_id": "",
        "files_seen": 0,
        "files_indexed": 0,
        "files_skipped": 0,
        "pages_indexed": 0,
        "pages_embedded": 0,
        "current_path": "",
        "failures": [],
        "done": True,
    }


def test_the_index_lists_what_it_indexed() -> None:
    response = _client(FakeIndexingJobs(), _a_stocked_store()).get("/index/files", headers=AUTH)

    body = response.get_json()
    assert [file["id"] for file in body["files"]] == ["file-1"]
    assert body["files"][0]["state"] == "text_indexed"
    assert body["next_cursor"] is None
    assert response.headers["Cache-Control"] == "no-store"


def test_a_skipped_file_carries_the_reason_instead_of_a_page_count() -> None:
    response = _client(FakeIndexingJobs(), _a_stocked_store()).get(
        "/index/files", query_string={"state": "skipped"}, headers=AUTH
    )

    [skipped] = response.get_json()["files"]
    assert skipped["id"] == "file-2"
    assert skipped["skip_reason"] == "too_large"
    assert skipped["page_count"] == 0


def test_a_state_that_does_not_exist_is_400_rather_than_an_empty_list() -> None:
    response = _client(FakeIndexingJobs(), _a_stocked_store()).get(
        "/index/files", query_string={"state": "pondering"}, headers=AUTH
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_the_cursor_walks_every_file_once() -> None:
    store = FakeIndexStore()
    for n in range(5):
        store.upsert_file(_a_file(f"file-{n}", 10, FileState.TEXT_INDEXED, path=Path(f"/corpus/{n}.pdf")))
    client = _client(FakeIndexingJobs(), store)

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(6):
        query = {} if cursor is None else {"cursor": cursor}
        body = client.get("/index/files", query_string=query, headers=AUTH).get_json()
        seen.extend(file["id"] for file in body["files"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert sorted(seen) == [f"file-{n}" for n in range(5)]
    assert len(seen) == len(set(seen)), "the cursor showed a file twice"


def test_forgetting_a_file_takes_it_out_of_the_index() -> None:
    store = FakeIndexStore()
    store.upsert_file(_a_file("f1", size_bytes=1024, state=FileState.TEXT_INDEXED))
    store.upsert_pages([Page(id="f1:1", file_id="f1", page_no=1)])
    client = _client(FakeIndexingJobs(), store=store)

    response = client.delete("/index/files/f1", headers=AUTH)

    assert response.status_code == 204
    assert store.get_file("f1") is None


def test_forgetting_a_file_that_is_not_there_is_still_204() -> None:
    """Gone is the goal, and the row the user clicked may already have been rescanned away."""
    client = _client(FakeIndexingJobs())

    assert client.delete("/index/files/nothing", headers=AUTH).status_code == 204


def test_forgetting_a_file_needs_the_token() -> None:
    assert _client(FakeIndexingJobs()).delete("/index/files/f1").status_code == 401
