import numpy as np
import pytest

from sidecar.domain.errors import ValidationError
from sidecar.domain.heatmap import PatchGrid, build_heatmap, peak_patch, threshold_at
from sidecar.domain.vectors import VECTOR_DIM, PageVectors, QueryVectors


def unit(slot: int) -> np.ndarray:
    vector = np.zeros(VECTOR_DIM, dtype=np.float32)
    vector[slot] = 1.0
    return vector


def a_page(slots: list[int]) -> PageVectors:
    """A page whose patches carry the given features, in reading order."""
    return PageVectors("p1", np.stack([unit(s) for s in slots]).astype(np.float16), pool_factor=1)


def a_query(*slots: int) -> QueryVectors:
    return QueryVectors(np.stack([unit(s) for s in slots]))


def test_a_token_lights_up_the_patch_that_carries_it() -> None:
    # A 2x2 page whose bottom-right patch is the only one with feature 5.
    page = a_page([1, 2, 3, 5])

    heatmap = build_heatmap(a_query(5), page, PatchGrid(2, 2), ("funnel",))

    assert heatmap.combined.shape == (2, 2)
    assert peak_patch(heatmap.combined) == (1, 1)
    assert heatmap.combined[1][1] == pytest.approx(1.0)


def test_patches_are_laid_out_in_reading_order() -> None:
    page = a_page([9, 9, 4, 9, 9, 9])

    heatmap = build_heatmap(a_query(4), page, PatchGrid(2, 3), ("x",))

    assert peak_patch(heatmap.combined) == (0, 2)


def test_one_map_per_query_token_each_labelled() -> None:
    page = a_page([1, 2, 3, 4])

    heatmap = build_heatmap(a_query(2, 4), page, PatchGrid(2, 2), ("red", "dialog"))

    assert [t.token for t in heatmap.tokens] == ["red", "dialog"]
    assert peak_patch(heatmap.tokens[0].values) == (0, 1)
    assert peak_patch(heatmap.tokens[1].values) == (1, 1)


def test_the_combined_map_is_the_strongest_token_at_each_patch() -> None:
    page = a_page([1, 2, 3, 4])

    heatmap = build_heatmap(a_query(1, 4), page, PatchGrid(2, 2), ("a", "b"))

    expected = np.maximum(heatmap.tokens[0].values, heatmap.tokens[1].values)
    assert np.allclose(heatmap.combined, expected)


def test_tokens_share_one_scale_so_a_weak_token_stays_weak() -> None:
    # "hit" matches a patch exactly. "miss" matches nothing on the page.
    page = a_page([1, 1, 1, 1])

    heatmap = build_heatmap(a_query(1, 7), page, PatchGrid(2, 2), ("hit", "miss"))

    assert heatmap.tokens[0].values.max() == pytest.approx(1.0)
    assert heatmap.tokens[1].values.max() == pytest.approx(0.0)


def test_a_page_that_matches_nothing_anywhere_is_flat_rather_than_a_divide_by_zero() -> None:
    page = a_page([1, 1, 1, 1])

    heatmap = build_heatmap(a_query(7), page, PatchGrid(2, 2), ("miss",))

    assert np.all(heatmap.combined == 0.0)


def test_the_default_threshold_hides_most_of_the_page() -> None:
    values = np.arange(100, dtype=np.float32).reshape(10, 10)

    assert threshold_at(values) == pytest.approx(np.percentile(values, 90))
    assert (values >= threshold_at(values)).sum() == 10


def test_pooled_vectors_are_refused_because_they_have_no_position_left() -> None:
    pooled = PageVectors("p1", np.stack([unit(1), unit(2)]).astype(np.float16), pool_factor=3)

    with pytest.raises(ValidationError, match="Unpooled"):
        build_heatmap(a_query(1), pooled, PatchGrid(2, 2), ("x",))


def test_token_labels_that_do_not_match_the_query_are_refused() -> None:
    with pytest.raises(ValidationError):
        build_heatmap(a_query(1, 2), a_page([1, 2, 3, 4]), PatchGrid(2, 2), ("only-one",))


@pytest.mark.parametrize("bad", [-1.0, 100.5])
def test_a_percentile_outside_the_slider_is_refused(bad: float) -> None:
    with pytest.raises(ValidationError):
        threshold_at(np.zeros((2, 2), dtype=np.float32), bad)


@pytest.mark.parametrize(("rows", "cols"), [(0, 4), (4, 0), (-1, 2)])
def test_a_grid_needs_at_least_one_patch(rows: int, cols: int) -> None:
    with pytest.raises(ValidationError):
        PatchGrid(rows, cols)
