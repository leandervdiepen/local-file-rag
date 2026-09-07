"""Choosing which folders feed the index."""

from __future__ import annotations

from pathlib import Path

from sidecar.application.store_ports import FolderStore
from sidecar.domain.entities import Folder
from sidecar.domain.errors import ValidationError


def _reject_unusable(path: Path) -> None:
    if not path.is_absolute():
        raise ValidationError(f"{path} is not a full path. Pick the folder from the file picker.")
    if not path.exists():
        raise ValidationError(f"{path} is not on this Mac. Pick another folder.")
    if not path.is_dir():
        raise ValidationError(f"{path} is a file. Pick the folder that holds it.")


class ManageFolders:
    """Owns which folders the index is allowed to read.

    Invariant: every stored folder is an absolute path that was a readable
    directory when it was added, and one path is one folder however many
    times it is added.

    Adding a folder does not read a single file. Indexing is a job the user
    starts, so picking three folders in onboarding costs three rows and one
    crawl rather than three crawls racing each other.
    """

    def __init__(self, folders: FolderStore) -> None:
        self._folders = folders

    def add(self, path: Path) -> Folder:
        """Add `path` as an enabled folder and return it.

        Raises `ValidationError`, and stores nothing, when the path is not
        absolute, is not there, or is not a directory. The store takes a path
        on trust, so a path the product will not accept is turned away here,
        with a message naming the path and what to do instead.

        Idempotent by path: a second add returns the folder already stored,
        with the time it was added and its enabled flag untouched.
        """
        _reject_unusable(path)
        return self._folders.add(path)

    def list(self) -> list[Folder]:
        """Every folder, enabled or not, ordered by path. Empty before the first add."""
        return self._folders.list()

    def remove(self, folder_id: str) -> None:
        """Forget a folder. Silent for an id that is not there, because gone is the goal.

        The files indexed from it stay in the index. A user who is moving a
        folder wants them, and forgetting files is its own action.
        """
        self._folders.remove(folder_id)

    def set_enabled(self, folder_id: str, enabled: bool) -> None:
        """Turn a folder on or off. Idempotent.

        Raises `NotFoundError` for an id that is not there, unlike `remove`:
        a toggle that silently does nothing is the bug the user reports.
        """
        self._folders.set_enabled(folder_id, enabled)
