"""What a page's use history means, run against the real table and against the fake.

The storage cap evicts by these fields and idle pre-embedding picks files by
them, so a fake that drifts from the adapter here makes both features pass
their unit tests while doing the wrong thing to a real index.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sidecar.application.store_ports import IndexStore
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.infrastructure.lancedb_store import LanceDBStore
from tests.fakes.index_store import FakeIndexStore

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=3)


@pytest.fixture(params=["lancedb", "fake"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> IndexStore:
    if request.param == "fake":
        return FakeIndexStore()
    return LanceDBStore(tmp_path / "db")


def a_file(file_id: str, name: str, mtime: datetime = NOW) -> IndexedFile:
    return IndexedFile(
        id=file_id,
        path=Path("/corpus") / name,
        folder_id="d1",
        content_hash=f"hash-{file_id}",
        size_bytes=1024,
        mtime=mtime,
        kind=FileKind.PDF,
        state=FileState.TEXT_INDEXED,
        page_count=1,
    )


def seed(store: IndexStore, file_id: str, name: str, mtime: datetime = NOW) -> str:
    store.upsert_file(a_file(file_id, name, mtime))
    store.upsert_pages([Page(id=f"{file_id}#1", file_id=file_id, page_no=1, text=name)])
    return f"{file_id}#1"


def test_a_page_nobody_opened_reads_as_untouched(store: IndexStore) -> None:
    page_id = seed(store, "f1", "report.pdf")

    heat = {item.page_id: item for item in store.page_heat()}

    assert heat[page_id].last_hit_at is None
    assert heat[page_id].hit_count == 0


def test_recording_a_hit_counts_it_and_stamps_the_time(store: IndexStore) -> None:
    page_id = seed(store, "f1", "report.pdf")

    store.record_hits([page_id], NOW)

    heat = {item.page_id: item for item in store.page_heat()}
    assert heat[page_id].hit_count == 1
    assert heat[page_id].last_hit_at == NOW


def test_two_hits_count_twice_and_keep_the_later_time(store: IndexStore) -> None:
    page_id = seed(store, "f1", "report.pdf")

    store.record_hits([page_id], NOW)
    store.record_hits([page_id], LATER)

    heat = {item.page_id: item for item in store.page_heat()}
    assert heat[page_id].hit_count == 2
    assert heat[page_id].last_hit_at == LATER


def test_a_hit_marks_the_file_used_so_pre_embedding_can_find_it(store: IndexStore) -> None:
    page_id = seed(store, "f1", "report.pdf")

    store.record_hits([page_id], NOW)

    stored = store.get_file("f1")
    assert stored is not None
    assert stored.last_used == NOW


def test_recording_a_hit_on_a_page_that_is_not_there_changes_nothing(store: IndexStore) -> None:
    seed(store, "f1", "report.pdf")

    store.record_hits(["nothing#1"], NOW)

    assert all(item.hit_count == 0 for item in store.page_heat())


def test_recording_no_hits_at_all_is_allowed(store: IndexStore) -> None:
    seed(store, "f1", "report.pdf")

    store.record_hits([], NOW)

    assert all(item.hit_count == 0 for item in store.page_heat())


def test_the_most_recently_used_file_comes_first(store: IndexStore) -> None:
    used_page = seed(store, "f1", "opened.pdf")
    seed(store, "f2", "never-opened.pdf")

    store.record_hits([used_page], LATER)

    assert [file.id for file in store.recently_used_files(limit=10)] == ["f1", "f2"]


def test_files_nobody_used_fall_back_to_newest_first(store: IndexStore) -> None:
    """A fresh index has no use history and pre-embedding still has to start somewhere."""
    seed(store, "old", "old.pdf", mtime=NOW - timedelta(days=30))
    seed(store, "new", "new.pdf", mtime=NOW)

    assert [file.id for file in store.recently_used_files(limit=10)] == ["new", "old"]


def test_recently_used_stops_at_the_limit(store: IndexStore) -> None:
    for index in range(5):
        seed(store, f"f{index}", f"file-{index}.pdf")

    assert len(store.recently_used_files(limit=2)) == 2
