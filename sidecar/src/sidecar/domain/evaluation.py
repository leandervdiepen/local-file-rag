"""Scoring one retrieval against a golden query, and rolling the scores up.

The golden set has one relevant page per query, so hit@k and recall@k are
the same number and MRR is the only ranking metric that adds information.
Every rate is `None` for a split with no queries: a 0.0 there would read as
a set that missed everything.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sidecar.domain.errors import ValidationError
from sidecar.domain.search import PageHit

MATCH_CHANNELS = ("visual", "filename", "content")
MRR_CUTOFF = 10
TOP_PAGES_REPORTED = 10


@dataclass(frozen=True)
class GoldenQuery:
    """One labelled query: what a person typed and the single page that answers it.

    `expected_file` is relative to the corpus root so the set survives the
    corpus moving between machines. `match_channel` names the mechanism the
    query should win on, because a drop confined to `visual` is a model or
    cap problem and a drop confined to `content` is a BM25 problem.
    """

    id: str
    query: str
    expected_file: Path
    expected_page: int
    text_free: bool
    match_channel: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("A golden query has an id.")
        if self.expected_file.is_absolute():
            raise ValidationError(f"expected_file is relative to the corpus root, got {self.expected_file}.")
        if self.expected_page < 1:
            raise ValidationError(f"expected_page is 1-based, got {self.expected_page}.")
        if self.match_channel not in MATCH_CHANNELS:
            raise ValidationError(f"match_channel is one of {', '.join(MATCH_CHANNELS)}, got {self.match_channel!r}.")


@dataclass(frozen=True)
class RankedPage:
    """One row of a result list as the report shows it, the file relative to the corpus root."""

    page_id: str
    file: Path
    page: int
    score: float
    stage: str


@dataclass(frozen=True)
class QueryOutcome:
    """Everything one golden query produced: what stage 1 found, what stage 2 ranked, and what each cost."""

    golden: GoldenQuery
    candidates: int
    stage1_rank: int | None
    embedded_before_run: int
    cap_miss: bool
    fallback_fired: bool
    top10: tuple[RankedPage, ...]
    rank: int | None
    stage1_ms: int
    stage2_ms: int
    cold_pages: int

    @property
    def stage1_hit(self) -> bool:
        return self.stage1_rank is not None

    @property
    def hit1(self) -> bool:
        return hit_at(self.rank, 1)

    @property
    def hit5(self) -> bool:
        return hit_at(self.rank, 5)

    @property
    def hit10(self) -> bool:
        return hit_at(self.rank, 10)


@dataclass(frozen=True)
class SplitMetrics:
    """The rates over one group of queries. `count` 0 means every rate is `None`."""

    count: int
    hit1: float | None
    hit5: float | None
    hit10: float | None
    mrr10: float | None
    stage1_hit: float | None
    stage2_hit5: float | None


@dataclass(frozen=True)
class Aggregates:
    """The rates overall and per split, keyed the way the report prints them."""

    overall: SplitMetrics
    by_text_free: dict[str, SplitMetrics]
    by_match_channel: dict[str, SplitMetrics]


def relative_file(hit: PageHit, corpus_root: Path) -> Path:
    """The hit's file as the golden set names it. A page outside the corpus keeps its absolute path so it shows."""
    return hit.path.relative_to(corpus_root) if hit.path.is_relative_to(corpus_root) else hit.path


def rank_of(expected: GoldenQuery, hits: Sequence[PageHit], corpus_root: Path) -> int | None:
    """The 1-based position of the expected page in `hits`, `None` when it is not there."""
    target = corpus_root / expected.expected_file
    for position, hit in enumerate(hits, start=1):
        if hit.path == target and hit.page_no == expected.expected_page:
            return position
    return None


def hit_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def reciprocal_rank(rank: int | None, cutoff: int = MRR_CUTOFF) -> float:
    if rank is None or rank > cutoff:
        return 0.0
    return 1 / rank


def cap_missed(stage1_rank: int | None, candidates: Sequence[PageHit], embedded: Collection[str], cap: int) -> bool:
    """True when stage 1 found the page but the cold page cap kept stage 2 from ever reading it.

    Only uncached candidates count against the cap, so a page that already
    had a vector is never a cap miss however low BM25 ranked it.
    """
    if stage1_rank is None:
        return False
    expected_id = candidates[stage1_rank - 1].page_id
    if expected_id in embedded:
        return False
    uncached = [hit.page_id for hit in candidates if hit.page_id not in embedded]
    return uncached.index(expected_id) + 1 > cap


def top_pages(hits: Sequence[PageHit], corpus_root: Path, limit: int = TOP_PAGES_REPORTED) -> tuple[RankedPage, ...]:
    return tuple(
        RankedPage(hit.page_id, relative_file(hit, corpus_root), hit.page_no, hit.score, hit.stage)
        for hit in hits[:limit]
    )


def aggregate(outcomes: Sequence[QueryOutcome]) -> Aggregates:
    return Aggregates(
        overall=_split_metrics(outcomes),
        by_text_free={
            "true": _split_metrics([o for o in outcomes if o.golden.text_free]),
            "false": _split_metrics([o for o in outcomes if not o.golden.text_free]),
        },
        by_match_channel={
            channel: _split_metrics([o for o in outcomes if o.golden.match_channel == channel])
            for channel in MATCH_CHANNELS
        },
    )


def _split_metrics(outcomes: Sequence[QueryOutcome]) -> SplitMetrics:
    found_by_stage1 = [o for o in outcomes if o.stage1_hit]
    return SplitMetrics(
        count=len(outcomes),
        hit1=_mean(float(o.hit1) for o in outcomes),
        hit5=_mean(float(o.hit5) for o in outcomes),
        hit10=_mean(float(o.hit10) for o in outcomes),
        mrr10=_mean(reciprocal_rank(o.rank) for o in outcomes),
        stage1_hit=_mean(float(o.stage1_hit) for o in outcomes),
        stage2_hit5=_mean(float(o.hit5) for o in found_by_stage1),
    )


def _mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return sum(items) / len(items) if items else None
