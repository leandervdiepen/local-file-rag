"""A working `ColdPageEmbedder`: embeds through the fake embedder into the fake store and reports progress."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sidecar.domain.progress import EmbedProgress
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.vector_store import FakeVectorStore


class FakeColdPages:
    def __init__(self, embedder: FakePageEmbedder, vectors: FakeVectorStore) -> None:
        self._embedder = embedder
        self._vectors = vectors
        self.runs: list[list[str]] = []

    def run(self, page_ids: Sequence[str], on_progress: Callable[[EmbedProgress], None] | None = None) -> int:
        wanted = [page_id for page_id in page_ids if page_id not in self._vectors.embedded_ids(page_ids)]
        self.runs.append(list(wanted))
        if not wanted:
            return 0
        self._vectors.put_vectors(self._embedder.embed_pages(wanted, [b"png"] * len(wanted)))
        for read, page_id in enumerate(wanted, start=1):
            if on_progress is not None:
                on_progress(EmbedProgress(pages_read=read, pages_total=len(wanted), current_page_id=page_id))
        return len(wanted)
