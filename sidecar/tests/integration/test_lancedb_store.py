"""`LanceDBStore` against a real LanceDB directory, per the `IndexStore` contract.

Everything here goes through the port. A test that reached past it to check
what the port promises would be proving something about lancedb rather than
about the contract every other layer codes against.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.infrastructure.lancedb_store import LanceDBStore

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def a_file(**overrides: object) -> IndexedFile:
    defaults: dict[str, object] = {
        "id": "f1",
        "path": Path("/corpus/report.pdf"),
        "folder_id": "d1",
        "content_hash": "hash1",
        "size_bytes": 1024,
        "mtime": NOW,
        "kind": FileKind.PDF,
        "state": FileState.TEXT_INDEXED,
        "page_count": 1,
    }
    return IndexedFile(**{**defaults, **overrides})  # type: ignore[arg-type]


def a_page(**overrides: object) -> Page:
    defaults: dict[str, object] = {"id": "p1", "file_id": "f1", "page_no": 1, "text": ""}
    return Page(**{**defaults, **overrides})  # type: ignore[arg-type]


def test_fresh_directory_is_usable(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")

    stats = store.stats()

    assert stats.files_scanned == stats.files_text_indexed == stats.files_skipped == 0
    assert stats.pages_total == stats.pages_embedded == stats.bytes_on_disk == 0
    assert stats.skips_by_reason == ()
    assert store.search_pages("anything", 10) == []
    assert (store.get_file("f1"), store.get_pages("f1"), store.content_hash_of("f1")) == (None, [], None)
    store.forget_file("nothing-was-ever-written")  # must not raise on tables that do not exist yet


def test_upsert_round_trips_every_field(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    file = a_file(state=FileState.SKIPPED, skip_reason="too_large", truncated_pages=True, last_used=NOW)
    page = a_page(text="hello", embedded_at=NOW, last_hit_at=NOW, hit_count=3)

    store.upsert_file(file)
    store.upsert_pages([page])

    assert store.get_file(file.id) == file
    assert store.get_pages(file.id) == [page]
    assert store.content_hash_of(file.id) == file.content_hash


def test_reads_of_an_id_that_was_never_written_are_empty(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file())
    store.upsert_pages([a_page()])

    assert store.get_file("never-indexed") is None
    assert store.get_pages("never-indexed") == []
    assert store.content_hash_of("never-indexed") is None


def test_pages_come_back_in_page_order_whatever_order_they_went_in(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file(page_count=3))
    store.upsert_pages([a_page(id="p3", page_no=3), a_page(id="p1", page_no=1), a_page(id="p2", page_no=2)])

    assert [page.page_no for page in store.get_pages("f1")] == [1, 2, 3]


def test_upsert_twice_is_one_row_for_files_and_pages(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    pages = [a_page(id="p1", page_no=1), a_page(id="p2", page_no=2)]

    store.upsert_file(a_file())
    store.upsert_file(a_file(content_hash="changed"))
    store.upsert_pages(pages)
    store.upsert_pages(pages)

    stats = store.stats()
    assert (stats.files_text_indexed, stats.pages_total) == (1, 2)
    assert store.content_hash_of("f1") == "changed"
    assert store.get_pages("f1") == pages


def test_forget_file_removes_the_file_and_its_pages(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file(id="f1"))
    store.upsert_file(a_file(id="f2"))
    store.upsert_pages([a_page(id="p1", file_id="f1"), a_page(id="p2", file_id="f2")])

    store.forget_file("f1")

    assert (store.get_file("f1"), store.get_pages("f1")) == (None, [])
    assert store.get_file("f2") == a_file(id="f2")
    assert [page.id for page in store.get_pages("f2")] == ["p2"]


def test_forget_file_is_silent_for_an_id_that_is_not_there(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file(id="f1"))

    store.forget_file("never-indexed")  # must not raise

    assert store.get_file("f1") is not None


def test_fts_finds_a_page_by_a_word_in_its_text(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    file = a_file(id="f1", path=Path("/corpus/notes.txt"), kind=FileKind.TEXT)
    store.upsert_file(file)
    store.upsert_pages([a_page(id="p1", file_id="f1", text="the invoice mentions a quarterly forecast")])

    hits = store.search_pages("forecast", 10)

    assert [h.page_id for h in hits] == ["p1"]
    assert hits[0].stage == "content"
    assert (hits[0].path, hits[0].kind) == (file.path, file.kind)


def test_filename_query_ranks_that_files_pages_first(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    target = a_file(id="target", path=Path("/corpus/quarterly_forecast.txt"), kind=FileKind.TEXT)
    other = a_file(id="other", path=Path("/corpus/unrelated.txt"), kind=FileKind.TEXT)
    store.upsert_file(target)
    store.upsert_file(other)
    store.upsert_pages(
        [
            a_page(id="target-p1", file_id="target", page_no=1, text="nothing to do with the query"),
            a_page(id="other-p1", file_id="other", page_no=1, text="quarterly forecast numbers are strong"),
        ]
    )

    hits = store.search_pages("quarterly_forecast", 10)

    assert hits[0].page_id == "target-p1"
    assert hits[0].stage == "filename"


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query_returns_nothing(tmp_path: Path, query: str) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file())
    store.upsert_pages([a_page(text="some text")])

    assert store.search_pages(query, 10) == []


@pytest.mark.parametrize(
    "query",
    ['"unterminated quote', "a lone AND", "!!!@@@***???"],
    ids=["unbalanced-quote", "lone-and", "punctuation"],
)
def test_hostile_query_strings_never_raise(tmp_path: Path, query: str) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file())
    store.upsert_pages([a_page(text="ordinary page text")])

    assert store.search_pages(query, 10) == []


def test_stats_counts_match_what_was_inserted(tmp_path: Path) -> None:
    store = LanceDBStore(tmp_path / "db")
    store.upsert_file(a_file(id="f1", state=FileState.TEXT_INDEXED, size_bytes=100))
    store.upsert_file(a_file(id="f2", state=FileState.SKIPPED, skip_reason="too_large", size_bytes=200))
    store.upsert_file(a_file(id="f3", state=FileState.SKIPPED, skip_reason="too_large", size_bytes=50))
    store.upsert_file(a_file(id="f4", state=FileState.SKIPPED, skip_reason="encrypted", size_bytes=10))
    store.upsert_file(a_file(id="f5", state=FileState.SCANNED, size_bytes=5))
    store.upsert_pages(
        [a_page(id="p1", file_id="f1", page_no=1, embedded_at=NOW), a_page(id="p2", file_id="f1", page_no=2)]
    )

    stats = store.stats()

    assert (stats.files_scanned, stats.files_text_indexed, stats.files_skipped) == (1, 1, 3)
    assert (stats.pages_total, stats.pages_embedded) == (2, 1)
    assert stats.bytes_on_disk == 100 + 200 + 50 + 10 + 5
    assert stats.skips_by_reason == (("encrypted", 1), ("too_large", 2))
