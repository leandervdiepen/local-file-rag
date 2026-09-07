"""The retrieval metrics on hand-built outcomes. Pure arithmetic, no fakes."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.domain.entities import FileKind
from sidecar.domain.errors import ValidationError
from sidecar.domain.evaluation import (
    GoldenQuery,
    QueryOutcome,
    aggregate,
    cap_missed,
    hit_at,
    rank_of,
    reciprocal_rank,
    relative_file,
    top_pages,
)
from sidecar.domain.search import PageHit

CORPUS = Path("/corpus")


def golden(
    id: str = "g01",  # noqa: A002
    file: str = "decks/growth.pdf",
    page: int = 4,
    text_free: bool = True,
    channel: str = "visual",
) -> GoldenQuery:
    return GoldenQuery(
        id=id,
        query="funnel chart",
        expected_file=Path(file),
        expected_page=page,
        text_free=text_free,
        match_channel=channel,
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


def outcome(rank: int | None, stage1_rank: int | None = 1, query: GoldenQuery | None = None) -> QueryOutcome:
    return QueryOutcome(
        golden=query or golden(),
        candidates=10,
        stage1_rank=stage1_rank,
        embedded_before_run=0,
        cap_miss=False,
        fallback_fired=False,
        top10=(),
        rank=rank,
        stage1_ms=1,
        stage2_ms=2,
        cold_pages=0,
    )


def test_rank_one_hits_every_cutoff_and_scores_mrr_one() -> None:
    first = outcome(rank=1)

    assert (first.hit1, first.hit5, first.hit10) == (True, True, True)
    assert reciprocal_rank(1) == 1.0


def test_rank_seven_hits_only_at_ten_and_scores_one_seventh() -> None:
    seventh = outcome(rank=7)

    assert (seventh.hit1, seventh.hit5, seventh.hit10) == (False, False, True)
    assert reciprocal_rank(7) == pytest.approx(1 / 7)


def test_no_rank_hits_nothing_and_scores_zero() -> None:
    missed = outcome(rank=None)

    assert (missed.hit1, missed.hit5, missed.hit10) == (False, False, False)
    assert reciprocal_rank(None) == 0.0


def test_a_rank_past_the_cutoff_scores_zero_not_a_small_fraction() -> None:
    assert reciprocal_rank(11) == 0.0
    assert hit_at(11, 10) is False


def test_rank_of_matches_the_expected_file_relative_to_the_corpus_root_and_the_page_number() -> None:
    hits = [hit("p1", page_no=1), hit("p2", "other.pdf", page_no=4), hit("p3", page_no=4)]

    assert rank_of(golden(page=4), hits, CORPUS) == 3


def test_rank_of_is_none_when_the_file_matches_but_no_page_does() -> None:
    assert rank_of(golden(page=4), [hit("p1", page_no=1), hit("p2", page_no=2)], CORPUS) is None


def test_rank_of_is_none_over_an_empty_list() -> None:
    assert rank_of(golden(), [], CORPUS) is None


def test_relative_file_strips_the_corpus_root_and_keeps_a_path_outside_it_absolute() -> None:
    inside = hit("p1", "decks/growth.pdf")
    outside = PageHit(
        page_id="p2",
        file_id="f2",
        path=Path("/elsewhere/x.pdf"),
        page_no=1,
        kind=FileKind.PDF,
        score=1,
        stage="content",
    )

    assert relative_file(inside, CORPUS) == Path("decks/growth.pdf")
    assert relative_file(outside, CORPUS) == Path("/elsewhere/x.pdf")


def test_top_pages_keeps_the_first_ten_with_relative_files() -> None:
    hits = [hit(f"p{n}", page_no=n, score=float(20 - n)) for n in range(1, 13)]

    top = top_pages(hits, CORPUS)

    assert len(top) == 10
    assert top[0].page_id == "p1"
    assert top[0].file == Path("decks/growth.pdf")
    assert top[0].page == 1
    assert top[0].score == 19.0
    assert top[0].stage == "content"


def test_cap_missed_when_the_expected_page_sits_past_the_cap_among_uncached_candidates() -> None:
    candidates = [hit(f"p{n}", page_no=n) for n in range(1, 36)]

    assert cap_missed(stage1_rank=33, candidates=candidates, embedded=set(), cap=30) is True
    assert cap_missed(stage1_rank=30, candidates=candidates, embedded=set(), cap=30) is False


def test_cached_candidates_ahead_of_the_expected_page_do_not_count_against_the_cap() -> None:
    candidates = [hit(f"p{n}", page_no=n) for n in range(1, 36)]
    cached_ahead = {f"p{n}" for n in range(1, 6)}

    assert cap_missed(stage1_rank=33, candidates=candidates, embedded=cached_ahead, cap=30) is False


def test_an_already_embedded_expected_page_is_never_a_cap_miss() -> None:
    candidates = [hit(f"p{n}", page_no=n) for n in range(1, 36)]

    assert cap_missed(stage1_rank=35, candidates=candidates, embedded={"p35"}, cap=30) is False


def test_no_stage_one_hit_is_no_cap_miss() -> None:
    assert cap_missed(stage1_rank=None, candidates=[hit("p1")], embedded=set(), cap=30) is False


def test_aggregate_overall_rates_over_a_mixed_set() -> None:
    rates = aggregate([outcome(rank=1), outcome(rank=7), outcome(rank=None, stage1_rank=None)]).overall

    assert rates.count == 3
    assert rates.hit1 == pytest.approx(1 / 3)
    assert rates.hit5 == pytest.approx(1 / 3)
    assert rates.hit10 == pytest.approx(2 / 3)
    assert rates.mrr10 == pytest.approx((1 + 1 / 7) / 3)
    assert rates.stage1_hit == pytest.approx(2 / 3)


def test_stage2_hit5_is_computed_only_over_stage_one_hits() -> None:
    found_and_ranked = outcome(rank=2, stage1_rank=5)
    found_and_buried = outcome(rank=9, stage1_rank=5)
    never_found = outcome(rank=None, stage1_rank=None)

    rates = aggregate([found_and_ranked, found_and_buried, never_found]).overall

    assert rates.hit5 == pytest.approx(1 / 3)
    assert rates.stage2_hit5 == pytest.approx(1 / 2)


def test_an_empty_split_is_count_zero_with_none_rates_never_zero_point_zero() -> None:
    rates = aggregate([outcome(rank=1, query=golden(text_free=True, channel="visual"))])

    empty = rates.by_text_free["false"]
    assert empty.count == 0
    assert (empty.hit1, empty.hit5, empty.hit10, empty.mrr10, empty.stage1_hit, empty.stage2_hit5) == (None,) * 6
    assert rates.by_match_channel["filename"].count == 0
    assert rates.by_match_channel["content"].hit5 is None


def test_stage2_hit5_is_none_when_stage_one_found_nothing_even_with_queries_present() -> None:
    rates = aggregate([outcome(rank=None, stage1_rank=None)]).overall

    assert rates.count == 1
    assert rates.hit5 == 0.0
    assert rates.stage2_hit5 is None


def test_aggregate_splits_by_text_free_and_match_channel() -> None:
    visual = outcome(rank=None, stage1_rank=None, query=golden(id="g02", text_free=True, channel="visual"))
    filename = outcome(rank=1, query=golden(id="g23", text_free=False, channel="filename"))
    content = outcome(rank=3, query=golden(id="g11", text_free=False, channel="content"))

    rates = aggregate([visual, filename, content])

    assert rates.by_text_free["true"].count == 1
    assert rates.by_text_free["true"].hit5 == 0.0
    assert rates.by_text_free["false"].count == 2
    assert rates.by_text_free["false"].hit5 == 1.0
    assert rates.by_match_channel["visual"].hit1 == 0.0
    assert rates.by_match_channel["filename"].hit1 == 1.0
    assert rates.by_match_channel["content"].hit1 == 0.0
    assert rates.by_match_channel["content"].hit5 == 1.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"match_channel": "ocr"},
        {"expected_page": 0},
        {"expected_file": Path("/corpus/decks/growth.pdf")},
        {"id": ""},
    ],
)
def test_a_golden_query_cannot_be_built_in_an_invalid_state(kwargs: dict[str, object]) -> None:
    fields: dict[str, object] = {
        "id": "g01",
        "query": "funnel chart",
        "expected_file": Path("decks/growth.pdf"),
        "expected_page": 4,
        "text_free": True,
        "match_channel": "visual",
    }
    fields.update(kwargs)

    with pytest.raises(ValidationError):
        GoldenQuery(**fields)  # type: ignore[arg-type]
