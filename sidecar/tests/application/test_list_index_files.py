"""`ListIndexFiles` against the in-memory store."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sidecar.application.list_index_files import MAX_PAGE_SIZE, ListIndexFiles
from sidecar.domain.entities import FileKind, FileState, IndexedFile
from tests.fakes.index_store import FakeIndexStore

NOW = datetime(2026, 9, 9, tzinfo=UTC)


def a_file(name: str, state: FileState) -> IndexedFile:
    return IndexedFile(
        id=name,
        path=Path(f"/corpus/{name}.pdf"),
        folder_id="d1",
        content_hash=f"h-{name}",
        size_bytes=10,
        mtime=NOW,
        kind=FileKind.PDF,
        state=state,
        skip_reason="too_large" if state is FileState.SKIPPED else None,
    )


def a_store(count: int, state: FileState = FileState.TEXT_INDEXED) -> FakeIndexStore:
    store = FakeIndexStore()
    for n in range(count):
        store.upsert_file(a_file(f"{n:03}", state))
    return store


def walk(use_case: ListIndexFiles, state: FileState, limit: int) -> list[str]:
    """Every path the cursor yields, following it to the end."""
    seen: list[str] = []
    cursor: str | None = None
    while True:
        page = use_case.run(state, cursor, limit)
        seen.extend(str(file.path) for file in page.files)
        if page.next_cursor is None:
            return seen
        cursor = page.next_cursor


def test_a_short_list_comes_back_in_one_page_with_no_cursor() -> None:
    page = ListIndexFiles(a_store(3)).run(FileState.TEXT_INDEXED, limit=10)

    assert len(page.files) == 3
    assert page.next_cursor is None


def test_the_cursor_walks_every_file_exactly_once_and_in_path_order() -> None:
    use_case = ListIndexFiles(a_store(25))

    seen = walk(use_case, FileState.TEXT_INDEXED, limit=4)

    assert seen == sorted(seen)
    assert len(seen) == 25
    assert len(set(seen)) == 25


def test_a_file_added_behind_the_reader_does_not_shift_the_page() -> None:
    """The cursor is a path, not an offset, so an insert before it changes nothing ahead of it."""
    store = a_store(6)
    use_case = ListIndexFiles(store)
    first = use_case.run(FileState.TEXT_INDEXED, limit=3)

    store.upsert_file(a_file("000a", FileState.TEXT_INDEXED))
    second = use_case.run(FileState.TEXT_INDEXED, first.next_cursor, limit=3)

    assert [str(f.path) for f in second.files] == ["/corpus/003.pdf", "/corpus/004.pdf", "/corpus/005.pdf"]


def test_only_files_in_the_state_asked_for_come_back() -> None:
    store = a_store(2)
    for name in ("skip-a", "skip-b", "skip-c"):
        store.upsert_file(a_file(name, FileState.SKIPPED))

    indexed = ListIndexFiles(store).run(FileState.TEXT_INDEXED, limit=50)
    skipped = ListIndexFiles(store).run(FileState.SKIPPED, limit=50)

    assert all(f.state is FileState.TEXT_INDEXED for f in indexed.files)
    assert all(f.skip_reason == "too_large" for f in skipped.files)


def test_an_absurd_limit_is_capped_rather_than_obeyed() -> None:
    page = ListIndexFiles(a_store(3)).run(FileState.TEXT_INDEXED, limit=10_000)

    assert len(page.files) == 3
    assert MAX_PAGE_SIZE < 10_000


def test_an_empty_index_is_an_empty_page_not_an_error() -> None:
    page = ListIndexFiles(FakeIndexStore()).run(FileState.SKIPPED)

    assert page.files == ()
    assert page.next_cursor is None
