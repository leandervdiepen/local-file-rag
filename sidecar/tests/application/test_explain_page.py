"""`ExplainPage` over fakes. No model, no disk."""

from __future__ import annotations

import numpy as np
import pytest

from sidecar.application.explain_page import ExplainPage
from sidecar.domain.errors import NotFoundError, ValidationError
from sidecar.domain.heatmap import PatchGrid, peak_patch
from sidecar.domain.vectors import PageVectors, QueryVectors
from tests.fakes.page_embedder import feature_vector


class FakeRenderPage:
    """Returns distinguishable bytes per page and counts what it was asked to render."""

    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages = pages
        self.rendered: list[str] = []

    def run(self, page_id: str, size: object) -> bytes:
        if page_id not in self.pages:
            raise NotFoundError(f"No page {page_id}.")
        self.rendered.append(page_id)
        return self.pages[page_id]


class FakeExplainer:
    """A page whose patches carry one feature word each, laid out on a grid the test picks."""

    def __init__(self, layout: dict[bytes, tuple[list[str], PatchGrid]]) -> None:
        self.layout = layout
        self.explained = 0

    def explain_page(self, image_png: bytes) -> tuple[PageVectors, PatchGrid]:
        self.explained += 1
        words, grid = self.layout[image_png]
        rows = np.stack([feature_vector(word) for word in words]).astype(np.float16)
        return PageVectors(page_id="", vectors=rows, pool_factor=1), grid

    def query_tokens(self, text: str) -> tuple[QueryVectors, tuple[str, ...]]:
        words = text.split()
        return QueryVectors(np.stack([feature_vector(word) for word in words])), tuple(words)


def a_use_case(words: list[str], grid: PatchGrid) -> tuple[ExplainPage, FakeRenderPage, FakeExplainer]:
    render = FakeRenderPage({"a:1": b"png-a"})
    explainer = FakeExplainer({b"png-a": (words, grid)})
    return ExplainPage(render, explainer), render, explainer  # type: ignore[arg-type]


def test_the_map_points_at_the_patch_carrying_the_query_word() -> None:
    explain, _, _ = a_use_case(["table", "chart", "notes", "funnel"], PatchGrid(2, 2))

    heatmap = explain.run("a:1", "funnel")

    assert heatmap.grid == PatchGrid(2, 2)
    assert peak_patch(heatmap.combined) == (1, 1)
    assert [token.token for token in heatmap.tokens] == ["funnel"]


def test_one_map_comes_back_per_word_the_user_typed() -> None:
    explain, _, _ = a_use_case(["table", "chart", "notes", "funnel"], PatchGrid(2, 2))

    heatmap = explain.run("a:1", "chart funnel")

    assert [token.token for token in heatmap.tokens] == ["chart", "funnel"]
    assert peak_patch(heatmap.tokens[0].values) == (0, 1)
    assert peak_patch(heatmap.tokens[1].values) == (1, 1)


def test_the_page_is_encoded_once_however_many_times_it_is_asked_about() -> None:
    explain, render, explainer = a_use_case(["a", "b", "c", "d"], PatchGrid(2, 2))

    explain.run("a:1", "a")
    explain.run("a:1", "b")
    explain.run("a:1", "c d")

    assert explainer.explained == 1, "moving the slider must not re-encode the page"
    assert render.rendered == ["a:1"]


def test_the_cache_lets_go_of_the_page_used_longest_ago() -> None:
    render = FakeRenderPage({"a:1": b"png-a", "b:1": b"png-b", "c:1": b"png-c"})
    layout = {name: (["x", "y", "z", "w"], PatchGrid(2, 2)) for name in (b"png-a", b"png-b", b"png-c")}
    explainer = FakeExplainer(layout)
    explain = ExplainPage(render, explainer, cached_pages=2)  # type: ignore[arg-type]

    explain.run("a:1", "x")
    explain.run("b:1", "x")
    explain.run("a:1", "x")
    explain.run("c:1", "x")
    explain.run("a:1", "x")

    assert render.rendered == ["a:1", "b:1", "c:1"], "a:1 stayed cached because it kept being used"


def test_a_page_that_is_not_indexed_is_not_explained() -> None:
    explain, _, _ = a_use_case(["a", "b", "c", "d"], PatchGrid(2, 2))

    with pytest.raises(NotFoundError):
        explain.run("gone:1", "anything")


def test_vectors_that_do_not_fill_the_grid_are_refused_rather_than_drawn_wrong() -> None:
    explain, _, _ = a_use_case(["a", "b", "c"], PatchGrid(2, 2))

    with pytest.raises(ValidationError, match="Unpooled"):
        explain.run("a:1", "a")
