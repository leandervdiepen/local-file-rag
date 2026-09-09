"""`EnforceStorageCap` over the in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from sidecar.application.enforce_storage_cap import EnforceStorageCap
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.vector_store import FakeVectorStore

NOW = datetime(2026, 9, 9, tzinfo=UTC)
ROWS = 4
PAGE_BYTES = ROWS * VECTOR_DIM * np.dtype(STORED_DTYPE).itemsize


class World:
    def __init__(self, cap_bytes: int) -> None:
        self.store = FakeIndexStore()
        self.vectors = FakeVectorStore()
        self.use_case = EnforceStorageCap(self.store, self.vectors, cap_bytes)

    def a_page(self, page_id: str, embedded: bool = True) -> str:
        file_id = page_id.split("#")[0]
        if self.store.get_file(file_id) is None:
            self.store.upsert_file(
                IndexedFile(
                    id=file_id,
                    path=Path("/corpus") / f"{file_id}.pdf",
                    folder_id="d1",
                    content_hash=f"hash-{file_id}",
                    size_bytes=1024,
                    mtime=NOW,
                    kind=FileKind.PDF,
                    state=FileState.TEXT_INDEXED,
                    page_count=1,
                )
            )
        self.store.upsert_pages([Page(id=page_id, file_id=file_id, page_no=1)])
        if embedded:
            self.vectors.put_vectors([_vectors_for(page_id)])
        return page_id

    def hit(self, page_id: str, at: datetime) -> None:
        self.store.record_hits([page_id], at)


def _vectors_for(page_id: str) -> PageVectors:
    return PageVectors(page_id=page_id, vectors=np.ones((ROWS, VECTOR_DIM), dtype=STORED_DTYPE), pool_factor=3)


def test_a_store_inside_its_cap_loses_nothing() -> None:
    world = World(cap_bytes=PAGE_BYTES * 10)
    world.a_page("f1#1")

    assert world.use_case.run() == 0
    assert world.vectors.count() == 1


def test_an_empty_store_is_not_a_failure() -> None:
    assert World(cap_bytes=0).use_case.run() == 0


def test_the_page_nobody_opened_loses_its_vectors_first() -> None:
    world = World(cap_bytes=PAGE_BYTES * 2)
    world.a_page("opened#1")
    world.a_page("untouched#1")
    world.a_page("untouched#2")
    world.hit("opened#1", NOW)

    world.use_case.run()

    assert world.vectors.embedded_ids(["opened#1", "untouched#1", "untouched#2"]) == {"opened#1"}


def test_the_least_recently_opened_goes_before_the_one_opened_today() -> None:
    world = World(cap_bytes=PAGE_BYTES * 2)
    world.a_page("stale#1")
    world.a_page("older#1")
    world.a_page("fresh#1")
    world.hit("stale#1", NOW - timedelta(days=90))
    world.hit("older#1", NOW - timedelta(days=30))
    world.hit("fresh#1", NOW)

    world.use_case.run()

    assert world.vectors.embedded_ids(["stale#1", "older#1", "fresh#1"]) == {"fresh#1"}


def test_an_evicted_page_is_still_indexed_and_still_findable_by_its_words() -> None:
    """Eviction costs one slower search, never a file that vanishes from the index."""
    world = World(cap_bytes=0)
    world.a_page("f1#1")
    world.store.upsert_pages([Page(id="f1#1", file_id="f1", page_no=1, text="quarterly egress")])

    world.use_case.run()

    assert world.vectors.count() == 0
    assert world.store.get_pages("f1")[0].text == "quarterly egress"
    assert [hit.page_id for hit in world.store.search_pages("egress", limit=5)] == ["f1#1"]


def test_a_page_with_no_vectors_is_not_counted_as_work_done() -> None:
    """Evicting it would free nothing while reporting that something was freed."""
    world = World(cap_bytes=PAGE_BYTES)
    world.a_page("embedded#1")
    world.a_page("bare#1", embedded=False)
    world.a_page("bare#2", embedded=False)

    assert world.use_case.run() == 0


def test_the_store_is_under_the_cap_after_a_run_that_evicted() -> None:
    world = World(cap_bytes=PAGE_BYTES * 3)
    for index in range(10):
        world.a_page(f"f{index}#1")

    assert world.use_case.run() > 0
    assert world.vectors.bytes_on_disk() <= PAGE_BYTES * 3
