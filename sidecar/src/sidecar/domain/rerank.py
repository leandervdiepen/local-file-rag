"""MaxSim: how a set of query vectors scores against a set of page vectors, and what the text channel takes back."""

from __future__ import annotations

from collections.abc import Collection, Sequence

import numpy as np

from sidecar.domain.vectors import PageVectors, QueryVectors

# What a page keeps of its MaxSim when stage 1 already proposed it. BM25 found
# it by the query's words and MaxSim reads those same words off the page image,
# so it is credited twice for one signal; a page that matched on meaning alone
# is credited once. Measured 2026-09-10, demo corpus, 52 golden queries, M1 Max,
# colqwen2-v1.0-merged float16: 0.80 to 0.85 lift four text-free ranks and move
# no text-bearing one, and the tightest text-bearing margin is 2.34 of 11.21.
TEXT_MATCH_DISCOUNT = 0.85


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


def discount_text_matches(
    scored: Sequence[tuple[str, float]], text_matched: Collection[str], discount: float = TEXT_MATCH_DISCOUNT
) -> list[tuple[str, float]]:
    """The same pages re-ranked, the ones in `text_matched` keeping `discount` of their score.

    A page the text channel proposed already earned its place by its words, so
    part of what MaxSim adds for reading those words again is taken back, and
    a page only the picture matched overtakes it when the two were close. A
    text match that is clearly the better page stays first. Ties keep their
    incoming order.
    """
    matched = set(text_matched)
    discounted = [(page_id, score * discount if page_id in matched else score) for page_id, score in scored]
    discounted.sort(key=lambda item: item[1], reverse=True)
    return discounted
