import numpy as np
import pytest

from sidecar.domain.errors import ValidationError
from sidecar.domain.rerank import TEXT_MATCH_DISCOUNT, discount_text_matches, maxsim, rank_by_maxsim
from sidecar.domain.vectors import VECTOR_DIM, PageVectors, QueryVectors


def unit(slot: int) -> np.ndarray:
    vector = np.zeros(VECTOR_DIM, dtype=np.float32)
    vector[slot] = 1.0
    return vector


def page(page_id: str, *slots: int) -> PageVectors:
    return PageVectors(page_id, np.stack([unit(s) for s in slots]).astype(np.float16), pool_factor=3)


def query(*slots: int) -> QueryVectors:
    return QueryVectors(np.stack([unit(s) for s in slots]))


def test_each_query_token_takes_its_best_patch_and_the_page_sums_them() -> None:
    assert maxsim(query(1, 2), page("p", 1, 2, 7)) == pytest.approx(2.0)
    assert maxsim(query(1, 2), page("p", 1, 7)) == pytest.approx(1.0)
    assert maxsim(query(1, 2), page("p", 7)) == pytest.approx(0.0)


def test_a_patch_matched_by_two_tokens_counts_for_both() -> None:
    assert maxsim(query(1, 1), page("p", 1)) == pytest.approx(2.0)


def test_ranking_puts_the_page_that_answers_more_of_the_query_first() -> None:
    ranked = rank_by_maxsim(query(1, 2, 3), [page("one", 1), page("three", 1, 2, 3), page("two", 2, 3)])

    assert [page_id for page_id, _ in ranked] == ["three", "two", "one"]


def test_ties_keep_their_incoming_order() -> None:
    ranked = rank_by_maxsim(query(1), [page("a", 1), page("b", 1), page("c", 1)])

    assert [page_id for page_id, _ in ranked] == ["a", "b", "c"]


def test_maxsim_agrees_with_a_nested_loop_reference_on_random_matrices() -> None:
    rng = np.random.default_rng(7)
    tokens = QueryVectors(rng.standard_normal((9, VECTOR_DIM)).astype(np.float32))
    patches = PageVectors("p", rng.standard_normal((40, VECTOR_DIM)).astype(np.float16), pool_factor=3)

    reference = sum(
        max(float(np.dot(patch.astype(np.float32), token)) for patch in patches.vectors) for token in tokens.vectors
    )

    assert maxsim(tokens, patches) == pytest.approx(reference, rel=1e-5)


def test_a_page_the_words_already_found_keeps_only_the_discount_and_a_close_picture_overtakes_it() -> None:
    ranked = discount_text_matches([("text", 10.0), ("picture", 9.0)], text_matched={"text"}, discount=0.85)

    assert [page_id for page_id, _ in ranked] == ["picture", "text"]
    assert [score for _, score in ranked] == pytest.approx([9.0, 8.5])


def test_a_text_match_that_is_clearly_the_better_page_stays_first() -> None:
    ranked = discount_text_matches([("text", 14.0), ("picture", 9.0)], text_matched={"text"})

    assert [page_id for page_id, _ in ranked] == ["text", "picture"]
    assert ranked[0][1] == pytest.approx(14.0 * TEXT_MATCH_DISCOUNT)


def test_pages_the_words_did_not_find_are_untouched_and_ties_keep_their_order() -> None:
    scored = [("a", 9.0), ("b", 9.0), ("c", 9.0)]

    assert discount_text_matches(scored, text_matched=set()) == scored
    assert discount_text_matches(scored, text_matched={"a", "b", "c"}) == [
        (p, pytest.approx(s * TEXT_MATCH_DISCOUNT)) for p, s in scored
    ]


def test_scores_are_computed_in_float32_from_float16_storage() -> None:
    stored = page("p", 1)
    assert stored.vectors.dtype == np.float16

    assert isinstance(maxsim(query(1), stored), float)


def test_vectors_must_be_wide_enough_and_non_empty() -> None:
    with pytest.raises(ValidationError):
        PageVectors("p", np.zeros((3, 64), dtype=np.float16), pool_factor=3)
    with pytest.raises(ValidationError):
        QueryVectors(np.zeros((0, VECTOR_DIM), dtype=np.float32))
    with pytest.raises(ValidationError):
        PageVectors("p", np.zeros((3, VECTOR_DIM), dtype=np.float16), pool_factor=0)
