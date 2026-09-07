"""`RunGoldenSet` over a working two-stage search and the in-memory vector store. No model, no disk."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from sidecar.application.run_golden_set import RunGoldenSet
from sidecar.application.search import COLD_PAGE_CAP, STAGE_ONE_CANDIDATE_LIMIT
from sidecar.domain.entities import FileKind
from sidecar.domain.evaluation import Aggregates, GoldenQuery, QueryOutcome
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.search import PageHit
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors
from tests.fakes.vector_store import FakeVectorStore

CORPUS = Path("/corpus")


class FakeTwoStageSearch:
    """A working two-stage search with the model taken out.

    Stage 1 answers from a script keyed by query text. Stage 2 embeds the
    uncached candidates up to the cold page cap, writing their vectors into
    the store and reporting one `EmbedProgress` per page, then returns the
    scripted ranking, or the candidates unchanged when none was scripted.
    A query in `failing` raises from stage 1, the way a store fault would.
    """

    def __init__(self, vectors: FakeVectorStore) -> None:
        self.vectors = vectors
        self.stage_one_by_query: dict[str, list[PageHit]] = {}
        self.stage_two_by_query: dict[str, list[PageHit]] = {}
        self.failing: set[str] = set()

    def stage_one(self, query: str, limit: int = STAGE_ONE_CANDIDATE_LIMIT) -> list[PageHit]:
        if query in self.failing:
            raise RuntimeError(f"stage one broke on {query!r}")
        return self.stage_one_by_query.get(query, [])[:limit]

    def stage_two(
        self,
        query: str,
        candidates: list[PageHit],
        on_progress: Callable[[EmbedProgress], None] | None = None,
    ) -> list[PageHit]:
        cached = self.vectors.embedded_ids([hit.page_id for hit in candidates])
        cold = [hit for hit in candidates if hit.page_id not in cached][:COLD_PAGE_CAP]
        for read, hit in enumerate(cold, start=1):
            self.vectors.put_vectors([vectors_for(hit.page_id)])
            if on_progress is not None:
                on_progress(EmbedProgress(pages_read=read, pages_total=len(cold), current_page_id=hit.page_id))
        return self.stage_two_by_query.get(query, list(candidates))


class Recorder:
    """What the runner reported, in the order it reported it."""

    def __init__(self) -> None:
        self.progress: list[tuple[int, int]] = []
        self.outcomes: list[QueryOutcome] = []

    def on_progress(self, done: int, total: int) -> None:
        self.progress.append((done, total))

    def on_outcome(self, outcome: QueryOutcome) -> None:
        self.outcomes.append(outcome)


def vectors_for(page_id: str) -> PageVectors:
    return PageVectors(page_id=page_id, vectors=np.ones((1, VECTOR_DIM), dtype=STORED_DTYPE), pool_factor=1)


def golden(
    id: str = "g02",  # noqa: A002
    query: str = "funnel chart",
    file: str = "decks/growth.pdf",
    page: int = 4,
    text_free: bool = True,
    channel: str = "visual",
) -> GoldenQuery:
    return GoldenQuery(
        id=id, query=query, expected_file=Path(file), expected_page=page, text_free=text_free, match_channel=channel
    )


def hit(page_id: str, file: str = "decks/growth.pdf", page_no: int = 1, score: float = 1.0) -> PageHit:
    return PageHit(
        page_id=page_id,
        file_id="f1",
        path=CORPUS / file,
        page_no=page_no,
        kind=FileKind.PDF,
        score=score,
        stage="content",
    )


def run(
    search: FakeTwoStageSearch,
    queries: Sequence[GoldenQuery],
    monotonic: Callable[[], float] = lambda: 0.0,
) -> tuple[Aggregates, Recorder]:
    recorder = Recorder()
    aggregates = RunGoldenSet(search, search.vectors, monotonic).run(
        CORPUS, queries, recorder.on_progress, recorder.on_outcome
    )
    return aggregates, recorder


def test_ranks_are_measured_in_each_stage_and_the_top_ten_reads_like_the_golden_file() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    expected = hit("p4", page_no=4, score=0.5)
    others = [hit("p1", page_no=1, score=3.0), hit("p2", page_no=2, score=2.0)]
    search.stage_one_by_query["funnel chart"] = [*others, expected]
    search.stage_two_by_query["funnel chart"] = [expected, *others]

    aggregates, recorder = run(search, [golden()])

    [outcome] = recorder.outcomes
    assert outcome.candidates == 3
    assert outcome.stage1_rank == 3
    assert outcome.rank == 1
    assert (outcome.hit1, outcome.hit5, outcome.hit10) == (True, True, True)
    assert outcome.top10[0].page_id == "p4"
    assert outcome.top10[0].file == Path("decks/growth.pdf")
    assert outcome.top10[0].page == 4
    assert aggregates.overall.hit1 == 1.0
    assert aggregates.overall.stage1_hit == 1.0


def test_cap_miss_when_the_expected_page_ranks_past_the_cap_among_uncached_candidates() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    candidates = [hit(f"p{n}", page_no=n) for n in range(1, 36)]
    search.stage_one_by_query["funnel chart"] = candidates

    _, recorder = run(search, [golden(page=33)])

    [outcome] = recorder.outcomes
    assert outcome.stage1_rank == 33
    assert outcome.embedded_before_run == 0
    assert outcome.cap_miss is True
    assert outcome.cold_pages == COLD_PAGE_CAP


def test_no_cap_miss_when_the_expected_page_already_had_a_vector() -> None:
    vectors = FakeVectorStore()
    vectors.put_vectors([vectors_for("p33")])
    search = FakeTwoStageSearch(vectors)
    search.stage_one_by_query["funnel chart"] = [hit(f"p{n}", page_no=n) for n in range(1, 36)]

    _, recorder = run(search, [golden(page=33)])

    [outcome] = recorder.outcomes
    assert outcome.embedded_before_run == 1
    assert outcome.cap_miss is False


def test_no_cap_miss_when_the_expected_page_is_uncached_but_within_the_cap() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    search.stage_one_by_query["funnel chart"] = [hit(f"p{n}", page_no=n) for n in range(1, 36)]

    _, recorder = run(search, [golden(page=5)])

    assert recorder.outcomes[0].cap_miss is False


def test_fallback_fired_when_stage_one_found_fewer_than_five_candidates() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    search.stage_one_by_query["funnel chart"] = [hit(f"p{n}", page_no=n) for n in range(1, 5)]
    search.stage_one_by_query["hosting invoice"] = [hit(f"p{n}", page_no=n) for n in range(1, 6)]

    _, recorder = run(search, [golden(), golden(id="g11", query="hosting invoice")])

    assert [o.fallback_fired for o in recorder.outcomes] == [True, False]


def test_cold_pages_counts_only_the_candidates_stage_two_had_to_embed() -> None:
    vectors = FakeVectorStore()
    vectors.put_vectors([vectors_for("p1")])
    search = FakeTwoStageSearch(vectors)
    search.stage_one_by_query["funnel chart"] = [hit(f"p{n}", page_no=n) for n in range(1, 5)]

    _, recorder = run(search, [golden()])

    assert recorder.outcomes[0].cold_pages == 3
    assert recorder.outcomes[0].embedded_before_run == 1


def test_stage_timings_come_from_the_injected_clock() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    search.stage_one_by_query["funnel chart"] = [hit("p4", page_no=4)]
    readings = iter([10.0, 10.12, 20.0, 21.5])

    _, recorder = run(search, [golden()], monotonic=lambda: next(readings))

    assert recorder.outcomes[0].stage1_ms == 120
    assert recorder.outcomes[0].stage2_ms == 1500


def test_a_query_whose_search_raises_still_produces_its_outcome_and_the_run_goes_on() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    search.stage_one_by_query["funnel chart"] = [hit("p4", page_no=4)]
    search.stage_one_by_query["hosting invoice"] = [hit("p1", "invoices/q2.pdf", page_no=1)]
    search.failing.add("broken query")
    queries = [
        golden(),
        golden(id="g99", query="broken query"),
        golden(id="g11", query="hosting invoice", file="invoices/q2.pdf", page=1),
    ]

    aggregates, recorder = run(search, queries)

    assert [o.golden.id for o in recorder.outcomes] == ["g02", "g99", "g11"]
    broken = recorder.outcomes[1]
    assert (broken.candidates, broken.stage1_rank, broken.rank, broken.cold_pages) == (0, None, None, 0)
    assert broken.fallback_fired is False
    assert recorder.outcomes[2].rank == 1
    assert recorder.progress == [(0, 3), (1, 3), (2, 3)]
    assert aggregates.overall.count == 3


def test_progress_is_reported_before_each_query_and_outcomes_after_in_the_same_order() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    order: list[str] = []
    runner = RunGoldenSet(search, search.vectors, lambda: 0.0)

    runner.run(
        CORPUS,
        [golden(id="g01"), golden(id="g02")],
        lambda done, total: order.append(f"progress {done}/{total}"),
        lambda outcome: order.append(f"outcome {outcome.golden.id}"),
    )

    assert order == ["progress 0/2", "outcome g01", "progress 1/2", "outcome g02"]
