"""Noticing that a page was actually used.

The index knows what it holds. This is the only thing that knows what any of
it was worth, and two features spend that: the storage cap evicts the pages
nobody opened, and idle pre-embedding starts with the files somebody did.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sidecar.application.ports import Clock
from sidecar.application.store_ports import IndexStore

logger = logging.getLogger(__name__)


class RecordPageHit:
    """Counts a page as used.

    A hit is the user opening a page, never a search returning it. Search
    returns twenty four pages for one query, so counting those would say every
    page is equally wanted and leave the cap evicting at random.

    Never raises. A hit that fails to record costs a slightly worse eviction
    decision later, and losing the page preview the user asked for to save a
    counter would be the wrong trade.
    """

    def __init__(self, store: IndexStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def run(self, page_ids: Sequence[str]) -> None:
        if not page_ids:
            return
        try:
            self._store.record_hits(page_ids, self._clock.now())
        except Exception:
            logger.exception("recording a hit on %d pages failed", len(page_ids))
