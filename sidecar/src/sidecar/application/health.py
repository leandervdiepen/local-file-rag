"""The health reporting use case."""

from __future__ import annotations

from dataclasses import dataclass

from sidecar.application.ports import Clock, HealthProbe
from sidecar.domain.model_readiness import ModelProgress
from sidecar.domain.version import VERSION


@dataclass(frozen=True)
class HealthReport:
    status: str
    version: str
    model_loaded: bool
    model: ModelProgress
    db_path: str
    checked_at: str


class ReportHealth:
    """Reports sidecar health.

    Invariant: a report always reflects the probe's state at the moment it is
    produced. It never returns a cached or stale value from an earlier check.
    """

    def __init__(self, clock: Clock, probe: HealthProbe) -> None:
        self._clock = clock
        self._probe = probe

    def run(self) -> HealthReport:
        return HealthReport(
            status="ok",
            version=VERSION,
            model_loaded=self._probe.model_loaded(),
            model=self._probe.model_readiness(),
            db_path=str(self._probe.db_path()),
            checked_at=self._clock.now().isoformat(),
        )
