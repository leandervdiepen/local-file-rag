"""Reading the counts behind the index screen."""

from __future__ import annotations

from dataclasses import replace

from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.search import IndexStats


class ReadIndexStats:
    """Reports what is in the index right now.

    Invariant: every number is counted from the rows that are there at the
    moment of the call, so a count never disagrees with the index it
    describes.

    `pages_embedded` comes from the vector store rather than the index,
    because that is where the vectors are. Counting it anywhere else means
    keeping a copy in step across the crawl that writes pages and the search
    that embeds them, and a count that can drift is worse on an index screen
    than one that costs a second lookup.
    """

    def __init__(self, store: IndexStore, vectors: VectorStore) -> None:
        self._store = store
        self._vectors = vectors

    def run(self) -> IndexStats:
        return replace(self._store.stats(), pages_embedded=self._vectors.count())
