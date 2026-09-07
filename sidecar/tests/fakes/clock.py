"""A real, in-memory Clock. Not a mock."""

from __future__ import annotations

from datetime import datetime


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now
