from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sidecar.application.health import ReportHealth
from sidecar.domain.version import VERSION
from tests.fakes.clock import FakeClock
from tests.fakes.health_probe import FakeHealthProbe


def test_report_reflects_the_probe_and_clock_state() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=UTC)
    db_path = Path("/tmp/example-db")
    use_case = ReportHealth(
        clock=FakeClock(fixed_time),
        probe=FakeHealthProbe(model_loaded=False, db_path=db_path),
    )

    report = use_case.run()

    assert report.status == "ok"
    assert report.version == VERSION
    assert report.model_loaded is False
    assert report.db_path == str(db_path)
    assert report.checked_at == fixed_time.isoformat()


def test_report_picks_up_a_loaded_model_from_the_probe() -> None:
    use_case = ReportHealth(
        clock=FakeClock(datetime(2026, 1, 1, tzinfo=UTC)),
        probe=FakeHealthProbe(model_loaded=True, db_path=Path("/tmp/db")),
    )

    report = use_case.run()

    assert report.model_loaded is True


def test_each_run_asks_the_probe_again_instead_of_caching() -> None:
    probe = FakeHealthProbe(model_loaded=False, db_path=Path("/tmp/db"))
    use_case = ReportHealth(clock=FakeClock(datetime(2026, 1, 1, tzinfo=UTC)), probe=probe)

    assert use_case.run().model_loaded is False

    probe.model_loaded_value = True

    assert use_case.run().model_loaded is True
