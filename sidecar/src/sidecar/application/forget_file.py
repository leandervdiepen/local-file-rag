"""Taking one file out of the index without touching the file itself."""

from __future__ import annotations

import logging

from sidecar.application.store_ports import IndexStore, VectorStore

logger = logging.getLogger(__name__)


class ForgetFile:
    """Removes a file's rows and vectors, leaving the file on disk alone.

    For the row on the index screen a user does not want indexed: a scan of
    their passport, a folder of client work, anything they would rather this
    app had never read. Deleting their file would be the wrong answer to that,
    so nothing here touches the filesystem.

    The next crawl of the folder puts it back, which is honest rather than a
    bug: an index that quietly refuses to see a file the user still keeps in
    an indexed folder is an index that cannot be trusted to be complete.
    Excluding it for good is the folder toggle, or a narrower folder.
    """

    def __init__(self, store: IndexStore, vectors: VectorStore) -> None:
        self._store = store
        self._vectors = vectors

    def run(self, file_id: str) -> None:
        """Forget this file. Silent for an id that is not there, because gone is the goal."""
        pages = [page.id for page in self._store.get_pages(file_id)]
        self._store.forget_file(file_id)
        self._vectors.forget_pages(pages)
        logger.info("forgot %s and its %d pages at the user's request", file_id, len(pages))
