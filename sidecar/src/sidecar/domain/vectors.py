"""What a page and a query look like to the retrieval model.

ColQwen2 turns a page image into a few hundred vectors, one per image patch,
and a query into one vector per token. Retrieval compares the two sets
directly, which is what lets a heatmap point at the patch that matched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sidecar.domain.errors import ValidationError

VECTOR_DIM = 128
STORED_DTYPE = np.float16


def _check_matrix(name: str, matrix: np.ndarray) -> None:
    if matrix.ndim != 2 or matrix.shape[1] != VECTOR_DIM:
        raise ValidationError(f"{name} is a matrix of {VECTOR_DIM}-wide rows, got shape {matrix.shape}.")
    if matrix.shape[0] == 0:
        raise ValidationError(f"{name} has no rows.")


@dataclass(frozen=True, eq=False)
class PageVectors:
    """One page's pooled patch vectors, as stored.

    `eq=False` because two arrays are not compared by `==` without ambiguity,
    and nothing compares pages this way: the id is the identity.
    """

    page_id: str
    vectors: np.ndarray
    pool_factor: int

    def __post_init__(self) -> None:
        _check_matrix("PageVectors.vectors", self.vectors)
        if self.pool_factor < 1:
            raise ValidationError(f"pool_factor is at least 1, got {self.pool_factor}.")

    @property
    def row_count(self) -> int:
        return int(self.vectors.shape[0])


@dataclass(frozen=True, eq=False)
class QueryVectors:
    """One query's token vectors. Instruction and padding tokens are already dropped."""

    vectors: np.ndarray

    def __post_init__(self) -> None:
        _check_matrix("QueryVectors.vectors", self.vectors)

    @property
    def token_count(self) -> int:
        return int(self.vectors.shape[0])
