"""A real, in-memory HealthProbe. Not a mock."""

from __future__ import annotations

from pathlib import Path


class FakeHealthProbe:
    """Tests set `model_loaded_value` and `db_path_value` directly to change what the probe reports."""

    def __init__(self, model_loaded: bool, db_path: Path) -> None:
        self.model_loaded_value = model_loaded
        self.db_path_value = db_path

    def model_loaded(self) -> bool:
        return self.model_loaded_value

    def db_path(self) -> Path:
        return self.db_path_value
