"""The ports that hold state: what is in the index, and which folders feed it.

Each `Protocol` plus its docstrings is the entire contract: an agent
implementing an adapter reads this file and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sidecar.domain.entities import FileState, Folder, IndexedFile, Page
from sidecar.domain.eviction import PageHeat
from sidecar.domain.search import IndexStats, PageHit
from sidecar.domain.vectors import PageVectors, QueryVectors


class IndexStore(Protocol):
    """The one place index state lives. A crash loses nothing that got here."""

    def upsert_file(self, file: IndexedFile) -> None:
        """Insert or replace by `file.id`. Idempotent: the same file twice is one row."""
        ...

    def upsert_pages(self, pages: Sequence[Page]) -> None:
        """Insert or replace by `page.id`, as one batch. Idempotent."""
        ...

    def forget_file(self, file_id: str) -> None:
        """Remove a file and its pages. Silent when the file is already gone."""
        ...

    def forget_pages(self, page_ids: Sequence[str]) -> None:
        """Remove these pages, leaving their file alone. Silent for ids that are not there.

        For a file that shrank. Re-indexing writes the pages that exist now and
        cannot know about the ones that no longer do, so a ten page report cut
        to three would go on returning pages four to ten in search results.
        """
        ...

    def get_file(self, file_id: str) -> IndexedFile | None:
        """The file stored under this id, `None` when nothing was stored under it.

        A missing file is an answer, not an error: an id read from a list
        taken before a rescan is the ordinary case.
        """
        ...

    def get_pages(self, file_id: str) -> list[Page]:
        """Every page of one file, ordered by page number.

        Empty for a file that has none and for a file that is not there: a
        skipped file and an unknown id both have nothing to show.
        """
        ...

    def content_hash_of(self, file_id: str) -> str | None:
        """The hash stored with this file, `None` when it is not in the index.

        Exists so an incremental rescan can compare it against the hash on
        disk and skip an unchanged file without loading it. The day 5 watcher
        depends on that: its cost has to be proportional to what changed
        rather than to the size of the folder.
        """
        ...

    def files_in_state(self, state: FileState, after_path: str | None, limit: int) -> list[IndexedFile]:
        """A page of files in one state, ordered by path, starting after `after_path`.

        Paged by path rather than by offset so a crawl running underneath the
        index screen cannot make a row appear twice or not at all. `after_path`
        of `None` starts at the beginning.
        """
        ...

    def indexed_files(self) -> list[IndexedFile]:
        """Every file that has pages, ordered by path.

        Exists so a job can walk what is in the index without a search. Skipped
        files are not here: they have no pages and nothing to do with them.
        """
        ...

    def record_hits(self, page_ids: Sequence[str], at: datetime) -> None:
        """Count one use of each of these pages, and mark their files used at `at`.

        Silent for ids that are not there, and a no-op for an empty list. This
        is the only thing that writes `last_hit_at`, `hit_count` and a file's
        `last_used`, which are what the storage cap evicts by and what idle
        pre-embedding picks up first.
        """
        ...

    def page_heat(self) -> list[PageHeat]:
        """How much use every page has seen, in no particular order.

        Every page, not only the ones with vectors: which of them cost storage
        is the vector store's question, and joining the two here would make
        this port depend on the answer.
        """
        ...

    def recently_used_files(self, limit: int) -> list[IndexedFile]:
        """The `limit` indexed files used most recently, most recent first.

        A file that has never been used is still returned once the used ones
        run out, oldest modification last, because a fresh index has no use
        history and pre-embedding still has to start somewhere.
        """
        ...

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        """Full-text search over page and file text, best first.

        Returns an empty list for a query that matches nothing, and for an
        empty query. Never raises on punctuation or an unbalanced quote: a
        search box takes whatever the user typed.
        """
        ...

    def stats(self) -> IndexStats:
        """Counts for the index screen, computed from rows rather than kept as counters."""
        ...


class FolderStore(Protocol):
    """The folders the user chose to index. A handful of rows, edited by hand."""

    def add(self, path: Path) -> Folder:
        """Add `path` as an enabled folder and return it.

        Idempotent by path, because the id is derived from it: a second add
        is one row and returns the folder already there, with its `added_at`
        and its enabled flag untouched. Turning one back on is `set_enabled`.

        Does not check that the folder exists. A folder that is gone is an
        empty crawl, which is the crawler's answer to give, not this one's.
        """
        ...

    def list(self) -> list[Folder]:
        """Every folder, enabled or not, ordered by path. Empty before the first add."""
        ...

    def remove(self, folder_id: str) -> None:
        """Forget a folder. Silent when the id is not there, because gone is the goal.

        Leaves the files indexed from it alone. Removing those is a separate
        decision, and the user who is only moving a folder wants them kept.
        """
        ...

    def set_enabled(self, folder_id: str, enabled: bool) -> None:
        """Turn a folder on or off. Idempotent.

        Raises `NotFoundError` for an id that is not there, unlike `remove`:
        the caller is asking for a state no row can hold, and a toggle that
        silently does nothing is the bug the user reports.
        """
        ...


class VectorStore(Protocol):
    """Where page vectors live. Separate from the index because it is the expensive part.

    A page's vectors are written once and read many times, are rebuilt from
    the page image when lost, and cost about 60 KB each, so this store can be
    evicted, capped or dropped without touching what the index knows about
    a file.
    """

    def put_vectors(self, vectors: Sequence[PageVectors]) -> None:
        """Insert or replace by `page_id`, as one batch. Idempotent. Empty input is a no-op."""
        ...

    def forget_pages(self, page_ids: Sequence[str]) -> None:
        """Drop the vectors for these pages. Silent for ids that have none, and a no-op for an empty list.

        Needed because a deleted file must leave nothing behind. Its vectors
        are the largest thing it owned, and a page that is gone must not go on
        being reachable through the vector search.
        """
        ...

    def get_vectors(self, page_ids: Sequence[str]) -> dict[str, PageVectors]:
        """The stored vectors for each id that has them. Ids without vectors are simply absent."""
        ...

    def embedded_ids(self, page_ids: Sequence[str]) -> set[str]:
        """Which of these ids have vectors, without reading the vectors.

        Exists because deciding what still needs embedding is asked of every
        candidate on every search, and the vectors themselves are only wanted
        for the ones that have them.
        """
        ...

    def nearest(self, query: QueryVectors, limit: int) -> list[tuple[str, float]]:
        """The `limit` pages most similar to the query across the whole store, best first.

        This is the fallback for a query stage 1 cannot serve, so it searches
        everything rather than a candidate set. Returns fewer than `limit`
        when the store holds fewer pages, and an empty list from an empty
        store. The score is the adapter's similarity and is only comparable
        with other scores from this method, never with MaxSim.
        """
        ...

    def compact(self) -> None:
        """Rewrite the store so deleted rows stop costing disk. Safe to call on an empty one.

        Deleting rows marks them gone and leaves their bytes in place, so
        `bytes_on_disk` does not move until this runs. Anything that deletes
        in order to free space has to call this or it will read the same size
        back and delete again.
        """
        ...

    def bytes_on_disk(self) -> int:
        """What the stored vectors cost, in bytes. Zero for a store with none.

        The number the storage cap is measured against. It is the store's own
        footprint rather than an estimate from row counts, because the cap is
        a promise about the user's disk and an estimate is not one.
        """
        ...

    def count(self) -> int:
        """How many pages have vectors. Cheap enough to call per write."""
        ...
