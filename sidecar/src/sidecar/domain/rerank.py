"""MaxSim: how a set of query vectors scores against a set of page vectors."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from sidecar.domain.vectors import PageVectors, QueryVectors


def maxsim(query: QueryVectors, page: PageVectors) -> float:
    """The ColBERT late-interaction score.

    For every query token, the best matching patch on the page; then the sum
    over tokens. A page scores well when each part of the question finds
    something on it, which is why it survives a query with no shared words.

    Computed in float32 whatever the stored precision. float16 accumulation
    over a few hundred dot products drifts enough to reorder close pages.
    """
    similarities = page.vectors.astype(np.float32) @ query.vectors.astype(np.float32).T
    return float(similarities.max(axis=0).sum())


def rank_by_maxsim(query: QueryVectors, pages: Sequence[PageVectors]) -> list[tuple[str, float]]:
    """Every page scored, best first. Ties keep their incoming order, so a stable caller stays stable."""
    scored = [(page.page_id, maxsim(query, page)) for page in pages]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
