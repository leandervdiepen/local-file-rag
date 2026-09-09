import numpy as np
import pytest

from sidecar.domain.errors import ValidationError
from sidecar.domain.rerank import maxsim, rank_by_maxsim
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
