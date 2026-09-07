"""Ports the application layer depends on.

Each `Protocol` plus its docstrings is the entire contract: an agent
implementing an adapter reads this file and nothing else.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol


class Clock(Protocol):
    """Provides the current time. Use cases take time from here, never from the system clock directly."""

    def now(self) -> datetime:
        """Return the current time. Never blocks."""
        ...


class HealthProbe(Protocol):
    """Reports the facts `/health` exposes about the running sidecar."""

    def model_loaded(self) -> bool:
        """True once the retrieval model is loaded in memory. Never triggers loading it."""
        ...

    def db_path(self) -> Path:
        """The directory the index database lives in. Does not imply the directory exists yet."""
        ...
