"""`Search` against the in-memory `FakeIndexStore`. No adapter, no disk, no network."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.application.search import COLD_PAGE_CAP, STAGE_ONE_CANDIDATE_LIMIT, Search
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.rerank import TEXT_MATCH_DISCOUNT
from sidecar.domain.search import PageHit
from tests.fakes.clock import FakeClock
from tests.fakes.cold_pages import FakeColdPages
from tests.fakes.folder_store import FakeFolderStore
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.vector_store import FakeVectorStore

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class RecordingStore(FakeIndexStore):
    """The same store, keeping the limits it was asked for. Still a real store, not a mock."""

    def __init__(self) -> None:
        super().__init__()
        self.limits: list[int] = []

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        self.limits.append(limit)
        return super().search_pages(query, limit)


def a_store_holding(texts: list[str], file_id: str = "f1", name: str = "notes.md") -> RecordingStore:
    """One indexed file whose pages carry `texts`, page 1 first. Page ids follow the domain's `owner:page_no` shape."""
    store = RecordingStore()
    add_file(store, texts, file_id, name)
    return store


def add_file(store: FakeIndexStore, texts: list[str], file_id: str, name: str) -> None:
    store.upsert_file(
        IndexedFile(
            id=file_id,
            path=Path("/corpus") / name,
            folder_id="d1",
            content_hash=f"hash-{file_id}",
            size_bytes=64,
            mtime=NOW,
            kind=FileKind.PDF if name.endswith(".pdf") else FileKind.TEXT,
            state=FileState.TEXT_INDEXED,
            page_count=len(texts),
        )
    )
    store.upsert_pages(
        [Page(id=f"{file_id}:{n}", file_id=file_id, page_no=n, text=t) for n, t in enumerate(texts, start=1)]
    )


def a_search(
    store: FakeIndexStore, looks: dict[str, list[str]] | None = None
) -> tuple[Search, FakePageEmbedder, FakeVectorStore, FakeColdPages]:
    """A Search over fakes. `looks` says which visual features each page id carries, for the fake embedder."""
    embedder = FakePageEmbedder(looks)
    vectors = FakeVectorStore()
    cold = FakeColdPages(embedder, vectors)
    return Search(store, vectors, embedder, cold), embedder, vectors, cold


@pytest.mark.parametrize("query", ["", "   ", "\t\n"])
def test_a_query_with_nothing_in_it_returns_nothing_and_never_asks_the_store(query: str) -> None:
    store = a_store_holding(["quarterly forecast"])

    search, _, _, _ = a_search(store)

    assert search.stage_one(query) == []
    assert store.limits == []


def test_the_stage_one_candidate_limit_is_what_reaches_the_store() -> None:
    store = a_store_holding(["quarterly forecast"])

    a_search(store)[0].stage_one("forecast")

    assert store.limits == [STAGE_ONE_CANDIDATE_LIMIT]


def test_a_caller_limit_reaches_the_store_and_bounds_the_results() -> None:
    store = a_store_holding(["forecast"] * 5)

    hits = a_search(store)[0].stage_one("forecast", limit=2)

    assert store.limits == [2]
    assert len(hits) == 2


def test_results_keep_the_order_the_store_put_them_in() -> None:
    store = a_store_holding(["forecast", "forecast forecast", "forecast forecast forecast"])

    hits = a_search(store)[0].stage_one("forecast")

    from_the_store = store.search_pages("forecast", STAGE_ONE_CANDIDATE_LIMIT)
    assert [hit.page_id for hit in hits] == [hit.page_id for hit in from_the_store]
    assert hits[0].page_id == "f1:3"


def test_stage_two_ranks_by_what_the_page_looks_like_not_by_its_words() -> None:
    store = a_store_holding(["chart chart chart", "chart", "chart"], name="deck.pdf")
    looks = {"f1:1": ["table"], "f1:2": ["funnel", "chart"], "f1:3": ["funnel"]}
    search, _, _, _ = a_search(store, looks)
    candidates = search.stage_one("chart")
    assert candidates[0].page_id == "f1:1", "stage 1 ranks by word count, so the wrong page leads"

    results = search.stage_two("funnel chart", candidates)

    assert [hit.page_id for hit in results] == ["f1:2", "f1:3", "f1:1"]
    assert all(hit.stage == "visual" for hit in results)
    assert results[0].score > results[1].score > results[2].score


def test_stage_two_pins_filename_matches_above_everything_and_leaves_them_unscored() -> None:
    store = RecordingStore()
    add_file(store, ["funnel"], "f1", "notes.md")
    add_file(store, ["report"], "f2", "budget.pdf")
    search, _, _, _ = a_search(store, {"f1:1": ["funnel"], "f2:1": ["funnel", "chart"]})
    candidates = search.stage_one("budget")
    assert [hit.stage for hit in candidates] == ["filename"]

    results = search.stage_two("funnel", candidates + search.stage_one("funnel"))

    assert [(hit.page_id, hit.stage) for hit in results] == [("f2:1", "filename"), ("f1:1", "visual")]


def test_stage_two_reads_cold_pages_best_first_up_to_the_cap_and_keeps_the_rest_in_stage_one_order() -> None:
    texts = ["forecast " * (50 - n) for n in range(COLD_PAGE_CAP + 5)]
    store = a_store_holding(texts, name="long.pdf")
    search, embedder, _, _ = a_search(store)
    candidates = search.stage_one("forecast")

    results = search.stage_two("forecast", candidates)

    assert len(embedder.embedded_page_ids) == COLD_PAGE_CAP
    assert embedder.embedded_page_ids == [hit.page_id for hit in candidates[:COLD_PAGE_CAP]]
    unread = results[COLD_PAGE_CAP:]
    assert [hit.page_id for hit in unread] == [hit.page_id for hit in candidates[COLD_PAGE_CAP:]]
    assert all(hit.stage == "content" for hit in unread)


def test_stage_two_does_not_re_read_a_page_that_already_has_vectors() -> None:
    store = a_store_holding(["forecast", "forecast"])
    search, embedder, _, _ = a_search(store)
    candidates = search.stage_one("forecast")
    search.stage_two("forecast", candidates)
    after_first = list(embedder.embedded_page_ids)
    assert len(after_first) == 2

    search.stage_two("forecast", candidates)

    assert embedder.embedded_page_ids == after_first, "the second search embedded a page it had already read"


def test_stage_two_reports_progress_against_the_total_cold_pages_not_the_chunk() -> None:
    store = a_store_holding(["forecast"] * 6)
    search, _, _, _ = a_search(store)
    seen: list[EmbedProgress] = []

    search.stage_two("forecast", search.stage_one("forecast"), on_progress=seen.append)

    assert [p.pages_total for p in seen] == [6] * 6
    assert [p.pages_read for p in seen] == [1, 2, 3, 4, 5, 6]


def test_stage_two_widens_a_thin_candidate_list_from_the_whole_vector_store() -> None:
    store = RecordingStore()
    add_file(store, ["quarterly numbers"], "f1", "numbers.md")
    add_file(store, ["slide"], "f2", "deck.pdf")
    search, _, vectors, _ = a_search(store, {"f2:1": ["funnel", "chart"]})
    search.stage_two("funnel chart", search.stage_one("slide"))
    assert vectors.count() == 1, "the deck page has vectors from an earlier search"

    results = search.stage_two("funnel chart", search.stage_one("funnel"))

    assert [hit.page_id for hit in results] == ["f2:1"]
    assert results[0].stage == "visual"


def test_a_page_the_words_already_found_does_not_also_win_on_the_words() -> None:
    """Stage 1 credited the note for saying 'funnel chart'. MaxSim reads the same two words off its image and
    ties the slide that only looks like one, and without the discount the tie went to the text."""
    store = RecordingStore()
    add_file(store, ["funnel chart"], "note", "notes.md")
    add_file(store, ["nothing alike"], "deck", "deck.pdf")
    search, _, _, cold = a_search(store, {"note:1": ["funnel", "chart"], "deck:1": ["funnel", "chart"]})
    cold.run(["deck:1"])

    results = search.stage_two("funnel chart", search.stage_one("funnel chart"))

    assert [hit.page_id for hit in results] == ["deck:1", "note:1"]
    assert results[0].score == pytest.approx(2.0)
    assert results[1].score == pytest.approx(2.0 * TEXT_MATCH_DISCOUNT)


def test_a_text_match_that_looks_clearly_better_still_comes_first() -> None:
    store = RecordingStore()
    add_file(store, ["funnel chart slide"], "note", "notes.md")
    add_file(store, ["nothing alike"], "deck", "deck.pdf")
    search, _, _, cold = a_search(store, {"note:1": ["funnel", "chart", "slide"], "deck:1": ["funnel", "chart"]})
    cold.run(["deck:1"])

    results = search.stage_two("funnel chart slide", search.stage_one("funnel chart slide"))

    assert [hit.page_id for hit in results] == ["note:1", "deck:1"]


def test_a_search_abandoned_before_it_starts_never_touches_the_model() -> None:
    store = a_store_holding(["forecast"] * 3)
    search, embedder, _, _ = a_search(store)

    results = search.stage_two("forecast", search.stage_one("forecast"), is_cancelled=lambda: True)

    assert results == []
    assert embedder.query_texts == [], "the query was encoded for a stream nobody is reading"
    assert embedder.embedded_page_ids == []


def test_stage_two_stops_when_the_caller_has_hung_up() -> None:
    store = a_store_holding(["forecast"] * 12)
    search, embedder, _, _ = a_search(store)
    # Live for the encode and the first chunk of pages, gone by the second.
    answers = iter([False, False, True])

    results = search.stage_two("forecast", search.stage_one("forecast"), is_cancelled=lambda: next(answers, True))

    assert results == []
    assert 0 < len(embedder.embedded_page_ids) < 12, "it stopped part way, not before starting and not at the end"


def a_search_over_folders(
    store: FakeIndexStore, folders: FakeFolderStore, looks: dict[str, list[str]] | None = None
) -> tuple[Search, FakeVectorStore, FakeColdPages]:
    embedder = FakePageEmbedder(looks)
    vectors = FakeVectorStore()
    cold = FakeColdPages(embedder, vectors)
    return Search(store, vectors, embedder, cold, folders), vectors, cold


def test_a_folder_the_user_turned_off_stops_returning_results() -> None:
    """The whole point of the toggle. A switch that changes nothing visible did nothing."""
    store = FakeIndexStore()
    add_file(store, ["quarterly egress"], "keep", "keep/report.pdf")
    add_file(store, ["quarterly egress"], "hidden", "hidden/report.pdf")
    folders = FakeFolderStore(FakeClock(NOW))
    folders.add(Path("/corpus/keep"))
    excluded = folders.add(Path("/corpus/hidden"))
    folders.set_enabled(excluded.id, False)
    search, _, _ = a_search_over_folders(store, folders)

    assert [hit.file_id for hit in search.stage_one("egress")] == ["keep"]


def test_turning_a_folder_back_on_returns_its_results_with_no_rescan() -> None:
    store = FakeIndexStore()
    add_file(store, ["quarterly egress"], "f1", "hidden/report.pdf")
    folders = FakeFolderStore(FakeClock(NOW))
    folder = folders.add(Path("/corpus/hidden"))
    search, _, _ = a_search_over_folders(store, folders)

    folders.set_enabled(folder.id, False)
    assert search.stage_one("egress") == []

    folders.set_enabled(folder.id, True)
    assert [hit.file_id for hit in search.stage_one("egress")] == ["f1"]


def test_the_vector_search_does_not_bring_back_a_page_the_toggle_excluded() -> None:
    """Stage 2 widens from the whole store, which knows nothing about folders."""
    store = FakeIndexStore()
    add_file(store, ["nothing alike"], "hidden", "hidden/deck.pdf")
    folders = FakeFolderStore(FakeClock(NOW))
    excluded = folders.add(Path("/corpus/hidden"))
    search, vectors, cold = a_search_over_folders(store, folders, looks={"hidden:1": ["funnel", "chart"]})
    cold.run(["hidden:1"])
    assert vectors.count() == 1

    folders.set_enabled(excluded.id, False)

    assert search.stage_two("funnel chart", []) == []
