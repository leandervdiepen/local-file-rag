"""A real, in-memory FolderStore. Not a mock.

Implements the same `FolderStore` contract as `LanceDBFolders`: an id derived
from the path, so adding the same folder twice returns the one already there,
a silent `remove` for an id that is not there, and a `NotFoundError` from
`set_enabled` for one. `tests/integration/test_lancedb_folders.py` runs both
against the same tests, which is what keeps this claim true.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from sidecar.application.ports import Clock
from sidecar.domain.entities import Folder
from sidecar.domain.errors import NotFoundError
from sidecar.domain.identity import file_id


class FakeFolderStore:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._folders: dict[str, Folder] = {}

    def add(self, path: Path) -> Folder:
        existing = self._folders.get(file_id(path))
        if existing is not None:
            return existing
        folder = Folder.at(path=path, added_at=self._clock.now())
        self._folders[folder.id] = folder
        return folder

    def list(self) -> list[Folder]:
        return sorted(self._folders.values(), key=lambda folder: str(folder.path))

    def remove(self, folder_id: str) -> None:
        self._folders.pop(folder_id, None)

    def set_enabled(self, folder_id: str, enabled: bool) -> None:
        current = self._folders.get(folder_id)
        if current is None:
            raise NotFoundError(f"No indexed folder has the id {folder_id}.")
        self._folders[folder_id] = replace(current, enabled=enabled)
