"""Adapter for the `HealthProbe` port, backed by the filesystem and the embedder."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from sidecar.domain.model_readiness import ModelProgress


class Readable(Protocol):
    """What this needs of the embedder: two questions that never load anything."""

    def is_loaded(self) -> bool: ...

    def readiness(self) -> ModelProgress: ...


class FilesystemHealthProbe:
    """Reports health from the configured db directory and the embedder holding the model.

    The embedder is asked rather than guessed at. Until 2026-09-09 this
    returned a hardcoded False, which had been true on day 0 and wrong from
    the moment the model existed, so `/health` said no model was loaded while
    one was answering searches.
    """

    def __init__(self, db_path: Path, embedder: Readable) -> None:
        self._db_path = db_path
        self._embedder = embedder

    def model_loaded(self) -> bool:
        return self._embedder.is_loaded()

    def model_readiness(self) -> ModelProgress:
        return self._embedder.readiness()

    def db_path(self) -> Path:
        return self._db_path
