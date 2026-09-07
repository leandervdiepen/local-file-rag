"""Adapter for the `Clock` port, backed by the real system clock."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Reads the real wall clock, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
