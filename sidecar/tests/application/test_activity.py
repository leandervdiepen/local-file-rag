"""How long since the user did anything."""

from __future__ import annotations

from sidecar.application.activity import Activity


class Ticking:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.seconds = 100.0

    def __call__(self) -> float:
        return self.seconds


def test_a_fresh_activity_starts_idle_from_now() -> None:
    assert Activity(Ticking()).idle_seconds() == 0.0


def test_idle_time_grows_while_nothing_happens() -> None:
    clock = Ticking()
    activity = Activity(clock)

    clock.seconds += 90.0

    assert activity.idle_seconds() == 90.0


def test_a_request_resets_the_clock() -> None:
    clock = Ticking()
    activity = Activity(clock)
    clock.seconds += 90.0

    activity.touch()

    assert activity.idle_seconds() == 0.0
