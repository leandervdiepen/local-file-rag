"""How long since the user asked this process for anything.

Kept here rather than read from a request context, because the thing that
wants to know is a background job with no request of its own.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class Activity:
    """The moment of the last request, and how long ago that was.

    Monotonic rather than wall clock: this measures an interval, and a clock
    that moves when the machine sleeps or the timezone changes would report
    an idle machine as busy or the reverse.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._last = clock()

    def touch(self) -> None:
        """Note that the user just did something. Called on every request."""
        with self._lock:
            self._last = self._clock()

    def idle_seconds(self) -> float:
        with self._lock:
            return self._clock() - self._last
