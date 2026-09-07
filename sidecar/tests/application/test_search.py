"""`Search` against the in-memory `FakeIndexStore`. No adapter, no disk, no network."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.application.search import STAGE_ONE_CANDIDATE_LIMIT, Search
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.search import PageHit
from tests.fakes.index_store import FakeIndexStore

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class RecordingStore(FakeIndexStore):
    """The same store, keeping the limits it was asked for. Still a real store, not a mock."""

    def __init__(self) -> None:
        super().__init__()
        self.limits: list[int] = []

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        self.limits.append(limit)
        return super().search_pages(query, limit)


def a_store_holding(texts: list[str]) -> RecordingStore:
    """One indexed file whose pages carry `texts`, page 1 first."""
    store = RecordingStore()
    store.upsert_file(
        IndexedFile(
            id="f1",
            path=Path("/corpus/notes.md"),
            folder_id="d1",
            content_hash="hash1",
            size_bytes=64,
            mtime=NOW,
            kind=FileKind.TEXT,
            state=FileState.TEXT_INDEXED,
            page_count=len(texts),
        )
    )
    store.upsert_pages([Page(id=f"p{n}", file_id="f1", page_no=n, text=t) for n, t in enumerate(texts, start=1)])
    return store


@pytest.mark.parametrize("query", ["", "   ", "\t\n"])
def test_a_query_with_nothing_in_it_returns_nothing_and_never_asks_the_store(query: str) -> None:
    store = a_store_holding(["quarterly forecast"])

    assert Search(store).stage_one(query) == []
    assert store.limits == []


def test_the_stage_one_candidate_limit_is_what_reaches_the_store() -> None:
    store = a_store_holding(["quarterly forecast"])

    Search(store).stage_one("forecast")

    assert store.limits == [STAGE_ONE_CANDIDATE_LIMIT]


def test_a_caller_limit_reaches_the_store_and_bounds_the_results() -> None:
    store = a_store_holding(["forecast"] * 5)

    hits = Search(store).stage_one("forecast", limit=2)

    assert store.limits == [2]
    assert len(hits) == 2


def test_results_keep_the_order_the_store_put_them_in() -> None:
    store = a_store_holding(["forecast", "forecast forecast", "forecast forecast forecast"])

    hits = Search(store).stage_one("forecast")

    from_the_store = store.search_pages("forecast", STAGE_ONE_CANDIDATE_LIMIT)
    assert [hit.page_id for hit in hits] == [hit.page_id for hit in from_the_store]
    assert hits[0].page_id == "p3"
