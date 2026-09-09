"""Choosing which folders feed the index."""

from __future__ import annotations

from pathlib import Path

from sidecar.application.ports import FolderWatch
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


class _WatchesNothing:
    """The watch for a build that has none, so the use case never tests for one."""

    def watch(self, root: Path) -> None:
        return None

    def unwatch(self, root: Path) -> None:
        return None


class ManageFolders:
    """Owns which folders the index is allowed to read, and which are watched.

    Invariant: every stored folder is an absolute path that was a readable
    directory when it was added, one path is one folder however many times it
    is added, and the watch is pointed at exactly the enabled ones. That last
    part is here rather than in the composition root because every way a
    folder changes goes through this class, and a watch that drifts out of
    step shows up as a file that quietly never updates.

    Adding a folder does not read a single file. Indexing is a job the user
    starts, so picking three folders in onboarding costs three rows and one
    crawl rather than three crawls racing each other.
    """

    def __init__(self, folders: FolderStore, watch: FolderWatch | None = None) -> None:
        self._folders = folders
        self._watch = watch or _WatchesNothing()

    def resume_watching(self) -> None:
        """Point the watch at every enabled folder. Called once, at startup.

        Folders outlive the process and the watch does not, so without this a
        restart leaves every folder unwatched until the user touches one.
        """
        for folder in self._folders.list():
            if folder.enabled:
                self._watch.watch(folder.path)

    def add(self, path: Path) -> Folder:
        """Add `path` as an enabled folder, start watching it, and return it.

        Raises `ValidationError`, and stores nothing, when the path is not
        absolute, is not there, or is not a directory. The store takes a path
        on trust, so a path the product will not accept is turned away here,
        with a message naming the path and what to do instead.

        Idempotent by path: a second add returns the folder already stored,
        with the time it was added and its enabled flag untouched.
        """
        _reject_unusable(path)
        folder = self._folders.add(path)
        if folder.enabled:
            self._watch.watch(folder.path)
        return folder

    def list(self) -> list[Folder]:
        """Every folder, enabled or not, ordered by path. Empty before the first add."""
        return self._folders.list()

    def remove(self, folder_id: str) -> None:
        """Forget a folder and stop watching it. Silent for an id that is not there.

        The files indexed from it stay in the index. A user who is moving a
        folder wants them, and forgetting files is its own action.
        """
        gone = next((folder for folder in self._folders.list() if folder.id == folder_id), None)
        self._folders.remove(folder_id)
        if gone is not None:
            self._watch.unwatch(gone.path)

    def set_enabled(self, folder_id: str, enabled: bool) -> None:
        """Turn a folder on or off, and its watch with it. Idempotent.

        Raises `NotFoundError` for an id that is not there, unlike `remove`:
        a toggle that silently does nothing is the bug the user reports.
        """
        self._folders.set_enabled(folder_id, enabled)
        folder = next((candidate for candidate in self._folders.list() if candidate.id == folder_id), None)
        if folder is None:
            return
        if enabled:
            self._watch.watch(folder.path)
        else:
            self._watch.unwatch(folder.path)
