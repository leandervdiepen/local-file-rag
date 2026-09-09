"""Bringing the index back in line with what changed on disk."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from sidecar.application.index_folder import IndexFolder
from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.changes import ChangeKind, FileChange, collapse, worth_reacting_to
from sidecar.domain.identity import file_id

logger = logging.getLogger(__name__)


class ApplyChanges:
    """Re-indexes what changed, and forgets what is gone.

    Invariant: after this returns, no path it was told about is described
    wrongly by the index. A file that was edited reads as its new content, and
    a file that was deleted is not in the index at all, including its vectors.

    Forgetting is the part worth being strict about. A deleted file that stays
    indexed is the failure a user notices and cannot explain: they deleted it,
    and the app keeps offering it.
    """

    def __init__(self, index_folder: IndexFolder, store: IndexStore, vectors: VectorStore) -> None:
        self._index_folder = index_folder
        self._store = store
        self._vectors = vectors

    def run(self, folder_id: str, changes: Sequence[FileChange], sizes: dict[Path, int]) -> int:
        """Apply a batch of changes and return how many paths were acted on.

        `sizes` carries the size the watcher saw for each touched path, so the
        gate rule stays a pure function of what was observed rather than of
        what the disk says by the time this runs.
        """
        acted = 0
        for change in collapse(list(changes)):
            if not worth_reacting_to(change, sizes.get(change.path, 0)):
                continue
            acted += 1
            if change.kind is ChangeKind.GONE:
                self._forget(change.path)
            else:
                self._reindex(folder_id, change.path)
        return acted

    def _forget(self, path: Path) -> None:
        owner = file_id(path)
        pages = [page.id for page in self._store.get_pages(owner)]
        self._store.forget_file(owner)
        self._vectors.forget_pages(pages)
        logger.info("forgot %s and its %d pages", path, len(pages))

    def _reindex(self, folder_id: str, path: Path) -> None:
        """Re-index one file by crawling the path itself.

        `IndexFolder` takes a root and walks it, and a single file is a root
        that yields one candidate, so this reuses the whole pipeline rather
        than growing a second one that could disagree with it about the gate,
        about OCR or about page ids.
        """
        owner = file_id(path)
        stale = [page.id for page in self._store.get_pages(owner)]
        try:
            self._index_folder.run(folder_id, path)
        except Exception:
            logger.exception("re-indexing %s failed", path)
            return
        # Pages that no longer exist after the re-index, which is what a file
        # that lost pages leaves behind. Their vectors go with them.
        current = {page.id for page in self._store.get_pages(owner)}
        self._vectors.forget_pages([page_id for page_id in stale if page_id not in current])
