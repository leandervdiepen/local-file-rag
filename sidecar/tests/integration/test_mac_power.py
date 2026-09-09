"""`MacPowerSource` against the real `pmset` on this machine."""

from __future__ import annotations

import pytest

from sidecar.infrastructure.mac_power import MacPowerSource

pytestmark = pytest.mark.integration


def test_reading_the_power_source_answers_without_raising() -> None:
    """Whatever this machine is running on, the answer is a bool and it arrives."""
    assert isinstance(MacPowerSource().on_ac_power(), bool)


def test_a_machine_that_cannot_be_asked_reads_as_plugged_in() -> None:
    """A desktop that read as being on battery would never pre-embed anything."""

    class NoPmset(MacPowerSource):
        def on_ac_power(self) -> bool:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr("sidecar.infrastructure.mac_power.subprocess.run", _raise)
                return super().on_ac_power()

    assert NoPmset().on_ac_power()


def _raise(*args: object, **kwargs: object) -> None:
    raise OSError("no such file")
