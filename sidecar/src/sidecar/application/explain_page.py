"""Explaining why a page matched, as a grid the renderer can draw."""

from __future__ import annotations

import logging
from collections import OrderedDict

from sidecar.application.embedding_ports import PageExplainer
from sidecar.application.render_page import PageImageSize, RenderPage
from sidecar.domain.heatmap import Heatmap, PatchGrid, build_heatmap
from sidecar.domain.vectors import PageVectors

logger = logging.getLogger(__name__)

# Unpooled vectors are about four times the size of the stored ones, and a
# person comparing pages goes back and forth between the same few. Five
# hundred is the cap ARCHITECTURE.md sets; this holds them in memory rather
# than on disk, because they are rebuilt from the page image either way and a
# cache that survives a restart is not worth the file format.
CACHED_PAGES = 500


class ExplainPage:
    """Builds the heatmap for one page and one query.

    Invariant: the grid returned always describes the vectors it was built
    from, so an overlay drawn from it lands on the patches that actually
    matched. A page whose vectors and grid disagree is refused rather than
    explained, because a heatmap in the wrong place is worse than none.

    The unpooled encode is the expensive part and is cached per page, so
    moving the threshold slider or switching tokens costs nothing.
    """

    def __init__(self, render: RenderPage, explainer: PageExplainer, cached_pages: int = CACHED_PAGES) -> None:
        self._render = render
        self._explainer = explainer
        self._cached_pages = cached_pages
        self._cache: OrderedDict[str, tuple[PageVectors, PatchGrid]] = OrderedDict()

    def run(self, page_id: str, query: str) -> Heatmap:
        """The per-token and combined maps for this page under this query.

        Raises `NotFoundError` when the page is not indexed and
        `ValidationError` for a blank query or a malformed page id, both of
        which arrive from a URL.
        """
        vectors, grid = self._vectors_for(page_id)
        query_vectors, tokens = self._explainer.query_tokens(query)
        return build_heatmap(query_vectors, vectors, grid, tokens)

    def _vectors_for(self, page_id: str) -> tuple[PageVectors, PatchGrid]:
        cached = self._cache.get(page_id)
        if cached is not None:
            self._cache.move_to_end(page_id)
            return cached

        page = self._explainer.explain_page(self._render.run(page_id, PageImageSize.FULL))
        self._cache[page_id] = page
        if len(self._cache) > self._cached_pages:
            self._cache.popitem(last=False)
        return page
