"""A real, in-memory HealthProbe. Not a mock."""

from __future__ import annotations

from pathlib import Path

from sidecar.domain.model_readiness import ModelProgress, ModelState


class FakeHealthProbe:
    """Tests set the `_value` attributes directly to change what the probe reports."""

    def __init__(self, model_loaded: bool, db_path: Path, readiness: ModelProgress | None = None) -> None:
        self.model_loaded_value = model_loaded
        self.db_path_value = db_path
        self.readiness_value = readiness or ModelProgress(ModelState.READY if model_loaded else ModelState.ABSENT)

    def model_loaded(self) -> bool:
        return self.model_loaded_value

    def model_readiness(self) -> ModelProgress:
        return self.readiness_value

    def db_path(self) -> Path:
        return self.db_path_value
