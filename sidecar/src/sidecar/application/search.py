"""Finding pages."""

from __future__ import annotations

from sidecar.application.store_ports import IndexStore
from sidecar.domain.search import PageHit

STAGE_ONE_CANDIDATE_LIMIT = 300


class Search:
    """Finds the pages that answer a query.

    Invariant: results are ordered best first, and the order is stable for
    an unchanged index and an unchanged query. A user who searches the same
    thing twice sees the same list in the same order, because a result list
    that reshuffles under an unchanged query cannot be trusted to have
    ranked anything.

    An empty or whitespace query returns nothing rather than everything.
    Nothing typed is not a request for the whole index.
    """

    def __init__(self, store: IndexStore) -> None:
        self._store = store

    def stage_one(self, query: str, limit: int = STAGE_ONE_CANDIDATE_LIMIT) -> list[PageHit]:
        """Full-text candidates, in milliseconds.

        This is what the user sees while stage two is still reading pages, so
        it never waits on anything expensive.
        """
        if not query.strip():
            return []
        return self._store.search_pages(query, limit)
