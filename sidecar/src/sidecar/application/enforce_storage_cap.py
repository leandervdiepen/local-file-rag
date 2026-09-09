"""Keeping the index inside the disk budget the user agreed to."""

from __future__ import annotations

import logging

from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.eviction import DEFAULT_CAP_BYTES, pages_to_evict

logger = logging.getLogger(__name__)


class EnforceStorageCap:
    """Drops the vectors of the least recently hit pages until the store fits.

    Only vectors go. They are most of what the index costs and the only part
    that can be rebuilt from the file itself, so an evicted page is still
    indexed, still found by its words, and earns its vectors back the next
    time it is a search candidate. Nothing the user would notice is lost
    except one slower search.

    Invariant: after a run that evicted anything, the vector store is under
    the cap. A run that evicted nothing means it already was.
    """

    def __init__(self, store: IndexStore, vectors: VectorStore, cap_bytes: int = DEFAULT_CAP_BYTES) -> None:
        self._store = store
        self._vectors = vectors
        self._cap_bytes = cap_bytes

    def run(self) -> int:
        """Evict what has to go and return how many pages lost their vectors.

        Reads the heat of every page and keeps only the ones that actually
        hold vectors, because a page with none costs nothing and evicting it
        would free nothing while counting as work done.

        Compacts before deciding and again after evicting. A store that has
        been written to carries the bytes of everything it replaced, so the
        first reading is over the cap for work already done, and without the
        second the next run reads the same size and evicts again. Measured
        2026-09-09: without either, the cap emptied the whole index in two
        passes rather than trimming it.
        """
        if self._vectors.bytes_on_disk() <= self._cap_bytes:
            return 0

        self._vectors.compact()
        bytes_on_disk = self._vectors.bytes_on_disk()
        if bytes_on_disk <= self._cap_bytes:
            logger.info("reclaimed enough by compacting, nothing evicted")
            return 0

        heat = self._store.page_heat()
        embedded = self._vectors.embedded_ids([item.page_id for item in heat])
        stored = [item for item in heat if item.page_id in embedded]

        evicting = pages_to_evict(stored, bytes_on_disk, self._cap_bytes)
        if not evicting:
            return 0
        self._vectors.forget_pages(evicting)
        self._vectors.compact()
        logger.info(
            "evicted %d of %d pages to get %.1f MB under the %.1f MB cap",
            len(evicting),
            len(stored),
            bytes_on_disk / 1024**2,
            self._cap_bytes / 1024**2,
        )
        return len(evicting)
