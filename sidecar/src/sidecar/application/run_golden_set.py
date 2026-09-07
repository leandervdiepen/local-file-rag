"""Running the golden set through both retrieval stages and scoring each query."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from sidecar.application.search import COLD_PAGE_CAP, FALLBACK_BELOW, STAGE_ONE_CANDIDATE_LIMIT
from sidecar.application.store_ports import VectorStore
from sidecar.domain.evaluation import (
    Aggregates,
    GoldenQuery,
    QueryOutcome,
    aggregate,
    cap_missed,
    rank_of,
    top_pages,
)
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.search import PageHit

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]
OutcomeCallback = Callable[[QueryOutcome], None]


class TwoStageSearch(Protocol):
    """What the runner needs from search: the two stages separately, so each can be timed and scored on its own."""

    def stage_one(self, query: str, limit: int = STAGE_ONE_CANDIDATE_LIMIT) -> list[PageHit]:
        """Full-text candidates, best first."""
        ...

    def stage_two(
        self,
        query: str,
        candidates: list[PageHit],
        on_progress: Callable[[EmbedProgress], None] | None = None,
    ) -> list[PageHit]:
        """The final ranking, best first. Calls `on_progress` once per page it had to embed."""
        ...


class RunGoldenSet:
    """Scores every golden query against the live index.

    Invariant: every query in the set produces exactly one outcome, in the
    order given, even when its search raises. A query whose search raises
    produces an outcome with no rank and no candidates and the error is
    logged, so one bad query never hides the other twenty-nine. The clock is
    injected so a test never sleeps or depends on timing.

    The callbacks belong to the caller, and one that raises stops the run.
    That is how a client that hung up stops thirty queries' worth of
    embedding that nobody will read.
    """

    def __init__(
        self, search: TwoStageSearch, vectors: VectorStore, monotonic: Callable[[], float] = time.monotonic
    ) -> None:
        self._search = search
        self._vectors = vectors
        self._monotonic = monotonic

    def run(
        self,
        corpus_root: Path,
        queries: Sequence[GoldenQuery],
        on_progress: ProgressCallback,
        on_outcome: OutcomeCallback,
    ) -> Aggregates:
        """Run every query, reporting `(done, total)` before each and its outcome after, and return the rates."""
        outcomes: list[QueryOutcome] = []
        for done, golden in enumerate(queries):
            on_progress(done, len(queries))
            outcome = self._score(corpus_root, golden)
            outcomes.append(outcome)
            on_outcome(outcome)
        return aggregate(outcomes)

    def _score(self, corpus_root: Path, golden: GoldenQuery) -> QueryOutcome:
        try:
            return self._search_and_score(corpus_root, golden)
        except Exception:
            logger.exception("golden query %s failed", golden.id)
            return _nothing_ran(golden)

    def _search_and_score(self, corpus_root: Path, golden: GoldenQuery) -> QueryOutcome:
        started = self._monotonic()
        candidates = self._search.stage_one(golden.query)
        stage1_ms = self._elapsed_ms(started)
        stage1_rank = rank_of(golden, candidates, corpus_root)
        embedded = self._vectors.embedded_ids([hit.page_id for hit in candidates])

        cold = _ColdPageCounter()
        started = self._monotonic()
        results = self._search.stage_two(golden.query, candidates, on_progress=cold.count)
        stage2_ms = self._elapsed_ms(started)

        return QueryOutcome(
            golden=golden,
            candidates=len(candidates),
            stage1_rank=stage1_rank,
            embedded_before_run=len(embedded),
            cap_miss=cap_missed(stage1_rank, candidates, embedded, COLD_PAGE_CAP),
            fallback_fired=len(candidates) < FALLBACK_BELOW,
            top10=top_pages(results, corpus_root),
            rank=rank_of(golden, results, corpus_root),
            stage1_ms=stage1_ms,
            stage2_ms=stage2_ms,
            cold_pages=cold.pages,
        )

    def _elapsed_ms(self, started: float) -> int:
        return round((self._monotonic() - started) * 1000)


class _ColdPageCounter:
    """Counts the pages stage 2 embedded, one progress call each."""

    def __init__(self) -> None:
        self.pages = 0

    def count(self, _: EmbedProgress) -> None:
        self.pages += 1


def _nothing_ran(golden: GoldenQuery) -> QueryOutcome:
    """The outcome of a query whose search raised: no candidates, no rank, and no fallback because nothing ran."""
    return QueryOutcome(
        golden=golden,
        candidates=0,
        stage1_rank=None,
        embedded_before_run=0,
        cap_miss=False,
        fallback_fired=False,
        top10=(),
        rank=None,
        stage1_ms=0,
        stage2_ms=0,
        cold_pages=0,
    )
