"""Holding one expensive object: loaded on first use, dropped when idle.

The retrieval model is about 4 GB resident and takes seconds to load, so it
cannot be loaded at startup and cannot be kept forever. Everything about that
lifecycle lives here, in stdlib only, so it can be tested without the model.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class LazyModel[T]:
    """One instance of `T`, loaded on demand and released after an idle spell.

    Loading happens at most once at a time. Two threads arriving together
    share one load rather than each starting their own, because loading a
    multi-gigabyte model twice is a bug that only shows up under demo
    conditions, when two things happen at once for the first time.

    Use is serialized with loading, so the object is never released or
    replaced while someone is inside it.
    """

    def __init__(
        self,
        load: Callable[[], T],
        unload: Callable[[T], None],
        idle_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._load = load
        self._unload = unload
        self._idle_seconds = idle_seconds
        self._clock = clock
        self._lock = threading.RLock()
        self._held: T | None = None
        self._timer: threading.Timer | None = None
        self._last_used = 0.0

    def use[R](self, fn: Callable[[T], R]) -> R:
        """Run `fn` against the loaded object, loading it first if it is not held.

        Blocks for the whole load on the first call. An exception from `load`
        leaves nothing held, so the next call tries again rather than
        returning a half-built object forever.
        """
        with self._lock:
            if self._held is None:
                self._held = self._load()
            try:
                return fn(self._held)
            finally:
                self._last_used = self._clock()
                self._arm_idle_timer()

    def is_loaded(self) -> bool:
        """Whether the object is held right now, answered without waiting for anything.

        Deliberately outside the lock. `use` holds it for the whole of a load,
        which on first run is a four gigabyte download, and this is what
        `/health` asks. Taking the lock made the endpoint that reports the
        download's progress block until the download finished, so the progress
        bar it feeds could never draw. Measured 2026-09-10.

        Reading one attribute is atomic under the GIL, and the answer is a
        snapshot either way: it can be stale the instant it is returned, and
        every caller already treats it that way.
        """
        return self._held is not None

    def unload(self) -> None:
        """Release now. Idempotent, and safe to call from the idle timer or a caller."""
        with self._lock:
            self._cancel_timer()
            held, self._held = self._held, None
            if held is not None:
                self._unload(held)

    def _arm_idle_timer(self) -> None:
        self._cancel_timer()
        # Daemon, so an idle model never keeps the process alive at quit.
        self._timer = threading.Timer(self._idle_seconds, self._unload_if_idle)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _unload_if_idle(self) -> None:
        """Release only if nothing has used it since the timer was set.

        The lock means this waits for any use in progress rather than pulling
        the object out from under it, and the timestamp check means a use that
        started meanwhile keeps the model.
        """
        with self._lock:
            if self._held is None or self._clock() - self._last_used < self._idle_seconds:
                return
            logger.info("releasing the model after %.0f idle seconds", self._idle_seconds)
            self.unload()
