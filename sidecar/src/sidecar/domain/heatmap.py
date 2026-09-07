"""Turning a query and a page's patch vectors into the picture of why they matched.

The heatmap is the product's reason to exist: it is the one answer a ranked
list cannot give. Everything here is pure, so the explanation can be tested
without a model, and so the same grid arithmetic serves the API and any
future renderer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sidecar.domain.errors import ValidationError
from sidecar.domain.vectors import PageVectors, QueryVectors

# The overlay hides everything below this percentile by default, because a
# similarity map is never zero anywhere and drawing all of it would tint the
# whole page instead of pointing at something.
DEFAULT_THRESHOLD_PERCENTILE = 90.0


@dataclass(frozen=True)
class PatchGrid:
    """How a page's patch vectors lay back onto the page.

    The model flattens a 2D grid of patches into a sequence, so the only way
    back to page coordinates is the row and column count the processor used
    after its spatial merge. Getting this wrong draws a plausible heatmap in
    the wrong place, which is worse than drawing none.
    """

    rows: int
    cols: int

    def __post_init__(self) -> None:
        if self.rows < 1 or self.cols < 1:
            raise ValidationError(f"A patch grid has at least one row and column, got {self.rows}x{self.cols}.")

    @property
    def patch_count(self) -> int:
        return self.rows * self.cols


@dataclass(frozen=True)
class TokenMap:
    """One query token's similarity to every patch, shaped like the page."""

    token: str
    values: np.ndarray


@dataclass(frozen=True)
class Heatmap:
    """Every token's map plus the combined one, all on the same scale.

    Normalized together rather than per token, so a token that matched nothing
    stays dim next to one that matched strongly. Normalizing each map to its
    own maximum would make the weakest token look as confident as the best.
    """

    grid: PatchGrid
    tokens: tuple[TokenMap, ...]
    combined: np.ndarray


def build_heatmap(query: QueryVectors, page: PageVectors, grid: PatchGrid, tokens: tuple[str, ...]) -> Heatmap:
    """Similarity of every query token to every patch, laid back onto the page.

    `page` must be the unpooled vectors: pooling merges neighbouring patches,
    so a pooled page has no position to point at any more.

    Raises `ValidationError` when the vectors and the grid disagree about how
    many patches the page has, or when the token labels do not match the query
    rows, because either mismatch produces a map that looks right and is not.
    """
    if page.row_count != grid.patch_count:
        raise ValidationError(
            f"The page has {page.row_count} patch vectors and the grid describes "
            f"{grid.patch_count}. Unpooled vectors are required for a heatmap."
        )
    if len(tokens) != query.token_count:
        raise ValidationError(f"{len(tokens)} token labels for {query.token_count} query vectors.")

    similarities = page.vectors.astype(np.float32) @ query.vectors.astype(np.float32).T
    per_token = similarities.T.reshape(query.token_count, grid.rows, grid.cols)
    scaled = _to_unit_scale(per_token)
    return Heatmap(
        grid=grid,
        tokens=tuple(TokenMap(token, scaled[index]) for index, token in enumerate(tokens)),
        combined=scaled.max(axis=0),
    )


def _to_unit_scale(maps: np.ndarray) -> np.ndarray:
    """Every map onto 0 to 1 against one shared range. A flat map becomes zeros, not a divide by zero."""
    low, high = float(maps.min()), float(maps.max())
    if high <= low:
        return np.zeros_like(maps, dtype=np.float32)
    return ((maps - low) / (high - low)).astype(np.float32)


def threshold_at(values: np.ndarray, percentile: float = DEFAULT_THRESHOLD_PERCENTILE) -> float:
    """The cutoff below which the overlay draws nothing.

    Raises `ValidationError` outside 0 to 100: the slider is a percentile and
    a value outside it is a caller bug, not a user one.
    """
    if not 0.0 <= percentile <= 100.0:
        raise ValidationError(f"A percentile is between 0 and 100, got {percentile}.")
    return float(np.percentile(values, percentile))


def peak_patch(values: np.ndarray) -> tuple[int, int]:
    """The row and column of the strongest patch, which is where the eye should land."""
    row, col = np.unravel_index(int(np.argmax(values)), values.shape)
    return int(row), int(col)
