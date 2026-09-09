"""Listing what is in the index, and why anything is not."""

from __future__ import annotations

from dataclasses import dataclass

from sidecar.application.store_ports import IndexStore
from sidecar.domain.entities import FileState, IndexedFile

PAGE_SIZE = 200
MAX_PAGE_SIZE = 500


@dataclass(frozen=True)
class FilePage:
    """One page of files, and where to carry on from."""

    files: tuple[IndexedFile, ...]
    next_cursor: str | None


class ListIndexFiles:
    """The rows behind the index screen.

    Invariant: walking the cursor to its end lists every file in that state
    exactly once, even while a crawl is writing. The cursor is a path rather
    than an offset, so a row inserted before the current position cannot shift
    the page under the reader.
    """

    def __init__(self, store: IndexStore) -> None:
        self._store = store

    def run(self, state: FileState, cursor: str | None = None, limit: int = PAGE_SIZE) -> FilePage:
        """A page of files in `state`. The cursor is `None` once the list is exhausted."""
        wanted = max(1, min(limit, MAX_PAGE_SIZE))
        # One more than asked for, so the answer to "is there another page"
        # comes from the same query rather than a second one that could
        # disagree with it.
        found = self._store.files_in_state(state, cursor, wanted + 1)
        page = found[:wanted]
        has_more = len(found) > wanted
        return FilePage(files=tuple(page), next_cursor=str(page[-1].path) if has_more and page else None)
