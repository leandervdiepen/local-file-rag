"""Bringing the index back in line with what changed on disk."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from sidecar.application.index_folder import IndexFolder
from sidecar.application.store_ports import FolderStore, IndexStore, VectorStore
from sidecar.domain.changes import ChangeKind, FileChange, collapse, worth_reacting_to
from sidecar.domain.entities import Folder
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

    def __init__(
        self,
        index_folder: IndexFolder,
        folders: FolderStore,
        store: IndexStore,
        vectors: VectorStore,
    ) -> None:
        self._index_folder = index_folder
        self._folders = folders
        self._store = store
        self._vectors = vectors

    def run(self, changes: Sequence[FileChange], sizes: dict[Path, int]) -> int:
        """Apply a batch of changes and return how many paths were acted on.

        `sizes` carries the size the watcher saw for each touched path, so the
        gate rule stays a pure function of what was observed rather than of
        what the disk says by the time this runs.

        Each path is attributed to the enabled folder that holds it, because
        one batch can span two watched folders and the file's row has to name
        the right one. A path under no enabled folder is left alone: the user
        turned that folder off, and reacting to it would put back what the
        toggle was for.
        """
        enabled = [folder for folder in self._folders.list() if folder.enabled]
        acted = 0
        for change in collapse(list(changes)):
            owner = _folder_holding(change.path, enabled)
            if owner is None or not worth_reacting_to(change, sizes.get(change.path, 0)):
                continue
            acted += 1
            if change.kind is ChangeKind.GONE:
                self._forget(change.path)
            else:
                self._reindex(owner.id, change.path)
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
        try:
            self._index_folder.run(folder_id, path)
        except Exception:
            logger.exception("re-indexing %s failed", path)
            return
        self._drop_pages_past_the_end(owner)

    def _drop_pages_past_the_end(self, owner: str) -> None:
        """Forget the pages a file used to have and no longer does.

        Re-indexing writes the pages that exist now and cannot know about the
        rest, so a ten page report cut to three would go on returning pages
        four to ten in search results. The file's own page count is the line,
        because the rows still sitting in the store are exactly what is being
        checked. This is the second half of D43.
        """
        file = self._store.get_file(owner)
        if file is None:
            return
        past_the_end = [page.id for page in self._store.get_pages(owner) if page.page_no > file.page_count]
        if not past_the_end:
            return
        self._store.forget_pages(past_the_end)
        self._vectors.forget_pages(past_the_end)
        logger.info("dropped %d pages %s no longer has", len(past_the_end), file.path)


def _folder_holding(path: Path, folders: Sequence[Folder]) -> Folder | None:
    """The innermost enabled folder this path is under, `None` when no folder is.

    Innermost rather than first, because a user who indexed both a folder and
    a folder inside it means the file to belong to the one they named last.
    """
    holding = [folder for folder in folders if path.is_relative_to(folder.path)]
    return max(holding, key=lambda folder: len(folder.path.parts), default=None)
