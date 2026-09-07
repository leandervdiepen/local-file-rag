"""Reading the counts behind the index screen."""

from __future__ import annotations

from sidecar.application.store_ports import IndexStore
from sidecar.domain.search import IndexStats


class ReadIndexStats:
    """Reports what is in the index right now.

    Invariant: every number is counted from the rows that are there at the
    moment of the call, so a count never disagrees with the index it
    describes.
    """

    def __init__(self, store: IndexStore) -> None:
        self._store = store

    def run(self) -> IndexStats:
        return self._store.stats()
