"""A working in-memory `PageEmbedder` whose scores can be reasoned about.

Every feature word maps to one fixed unit vector, so MaxSim between a query
and a page is the number of query words the page carries. A test that wants
page A to beat page B for "funnel chart" gives A those two words and B one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np

from sidecar.domain.errors import UnreadableFileError, ValidationError
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors, QueryVectors

POOL_FACTOR = 3


def feature_vector(word: str) -> np.ndarray:
    """A unit vector for a word, the same every time, distinct for distinct words."""
    slot = int.from_bytes(hashlib.blake2b(word.lower().encode(), digest_size=2).digest(), "big") % VECTOR_DIM
    vector = np.zeros(VECTOR_DIM, dtype=np.float32)
    vector[slot] = 1.0
    return vector


class FakePageEmbedder:
    def __init__(self, features_by_page_id: dict[str, Sequence[str]] | None = None) -> None:
        self.features_by_page_id = dict(features_by_page_id or {})
        self.embedded_page_ids: list[str] = []
        self.query_texts: list[str] = []
        self.unload_calls = 0
        self._loaded = False

    def embed_pages(self, page_ids: Sequence[str], images_png: Sequence[bytes]) -> list[PageVectors]:
        if len(page_ids) != len(images_png):
            raise ValidationError("page_ids and images_png differ in length.")
        if not page_ids:
            return []
        self._loaded = True
        out: list[PageVectors] = []
        for page_id, png in zip(page_ids, images_png, strict=True):
            if not png:
                raise UnreadableFileError(f"Empty image for {page_id}.")
            words = self.features_by_page_id.get(page_id) or [f"page:{page_id}"]
            rows = np.stack([feature_vector(word) for word in words]).astype(STORED_DTYPE)
            out.append(PageVectors(page_id=page_id, vectors=rows, pool_factor=POOL_FACTOR))
            self.embedded_page_ids.append(page_id)
        return out

    def embed_query(self, text: str) -> QueryVectors:
        if not text.strip():
            raise ValidationError("A query has words in it.")
        self._loaded = True
        self.query_texts.append(text)
        return QueryVectors(np.stack([feature_vector(word) for word in text.split()]))

    def is_loaded(self) -> bool:
        return self._loaded

    def unload(self) -> None:
        self.unload_calls += 1
        self._loaded = False
