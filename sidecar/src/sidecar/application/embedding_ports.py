"""The port that turns pages and queries into vectors.

Each `Protocol` plus its docstrings is the entire contract: an agent
implementing an adapter reads this file and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sidecar.domain.heatmap import PatchGrid
from sidecar.domain.vectors import PageVectors, QueryVectors


class PageEmbedder(Protocol):
    """The retrieval model, loaded when first asked and dropped when idle.

    Every method may block for as long as the model takes, including the load
    itself on the first call. Loading happens at most once at a time: two
    callers arriving together share one load rather than each starting their
    own, because loading a 2B parameter model twice is the bug that only
    appears under demo conditions.
    """

    def embed_pages(self, page_ids: Sequence[str], images_png: Sequence[bytes]) -> list[PageVectors]:
        """Pooled patch vectors for each page image, in the order given.

        `page_ids` and `images_png` are parallel and equally long; the result
        carries each id so the caller never re-zips them. Each result is
        float16 with the pool factor the adapter was built with. An empty
        input returns an empty list without loading the model.

        Raises `ValidationError` when the two sequences differ in length, and
        `UnreadableFileError` when an image will not decode.
        """
        ...

    def embed_query(self, text: str) -> QueryVectors:
        """Token vectors for a query, float32, exactly the rows the model scores with.

        Which tokens those are is the model's business: ColQwen2 appends
        augmentation tokens to a query and scores with them, so dropping them
        here would change the ranking. The adapter documents what it returns.

        Raises `ValidationError` for a blank query: there is nothing to encode
        and the caller should not have asked.
        """
        ...

    def is_loaded(self) -> bool:
        """True while the model holds memory. Never loads it to find out."""
        ...

    def unload(self) -> None:
        """Drop the model and its memory now. Idempotent, and the next embed reloads it."""
        ...


class PageExplainer(Protocol):
    """Re-reads one page at full detail, so the heatmap has a position to point at.

    Separate from `PageEmbedder` because it is a different configuration of
    the same model rather than a different model: Sentence Transformers
    applies pooling as a pipeline module, so one encoder cannot serve both
    storage and explanation (D35). Pooled vectors have no position left, which
    is why the heatmap cannot be drawn from what the index already holds.
    """

    def explain_page(self, image_png: bytes) -> tuple[PageVectors, PatchGrid]:
        """Unpooled patch vectors for one page image, with the grid that lays them back onto it.

        The returned `PageVectors` has `pool_factor` 1 and exactly
        `grid.rows * grid.cols` rows, because a heatmap built from a page
        whose vectors and grid disagree points confidently at the wrong place.

        Raises `UnreadableFileError` when the image will not decode.
        """
        ...

    def query_tokens(self, text: str) -> tuple[QueryVectors, tuple[str, ...]]:
        """Query vectors and the readable label for each row, for the per-token maps.

        The labels are what the token picker shows, so they are the words the
        user recognizes from what they typed. Rows the model adds for its own
        purposes are dropped here rather than shown as tokens nobody typed.

        Raises `ValidationError` for a blank query.
        """
        ...
