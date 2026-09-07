"""Adapter for the `HealthProbe` port, backed by the filesystem and process state."""

from __future__ import annotations

from pathlib import Path


class FilesystemHealthProbe:
    """Reports health from the configured db directory.

    No retrieval model is loaded anywhere in this build, so `model_loaded`
    always answers False. It starts reporting True once model loading exists.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def model_loaded(self) -> bool:
        return False

    def db_path(self) -> Path:
        return self._db_path
