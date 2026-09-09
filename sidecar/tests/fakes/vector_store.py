"""A working in-memory `VectorStore`."""

from __future__ import annotations

from collections.abc import Sequence

from sidecar.domain.rerank import rank_by_maxsim
from sidecar.domain.vectors import PageVectors, QueryVectors


class FakeVectorStore:
    def __init__(self) -> None:
        self._vectors: dict[str, PageVectors] = {}

    def put_vectors(self, vectors: Sequence[PageVectors]) -> None:
        for item in vectors:
            self._vectors[item.page_id] = item

    def forget_pages(self, page_ids: Sequence[str]) -> None:
        for page_id in page_ids:
            self._vectors.pop(page_id, None)

    def get_vectors(self, page_ids: Sequence[str]) -> dict[str, PageVectors]:
        return {page_id: self._vectors[page_id] for page_id in page_ids if page_id in self._vectors}

    def embedded_ids(self, page_ids: Sequence[str]) -> set[str]:
        return {page_id for page_id in page_ids if page_id in self._vectors}

    def nearest(self, query: QueryVectors, limit: int) -> list[tuple[str, float]]:
        return rank_by_maxsim(query, list(self._vectors.values()))[:limit]

    def count(self) -> int:
        return len(self._vectors)
