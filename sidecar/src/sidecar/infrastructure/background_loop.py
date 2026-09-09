"""A daemon thread that runs the same short jobs on a timer.

One loop for every background job rather than one thread each, because they
all want the same thing: run when the machine is quiet, stop when the process
does, and never take the app down.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)

DEFAULT_EVERY_SECONDS = 30.0

Job = Callable[[], object]


class BackgroundLoop:
    """Runs each job in turn, waits, repeats, until stopped.

    Jobs run one after another on one thread. They are all touching the same
    index, and two of them writing it at once is the one thing the store
    cannot take.

    A job that raises is logged and the loop carries on. These have nobody
    waiting on them, so an exception has nothing to reach and killing the
    thread would silently stop every other job with it.
    """

    def __init__(self, jobs: Sequence[Job], every_seconds: float = DEFAULT_EVERY_SECONDS) -> None:
        self._jobs = list(jobs)
        self._every_seconds = every_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="background-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Ask the loop to finish the job it is on and end. Waits for it briefly.

        Bounded, because this runs at exit: a job that hangs must not stop the
        process from quitting, and a daemon thread dies with it anyway.
        """
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._every_seconds)

    def _run(self) -> None:
        # Waits first. Starting a job in the same second the process does
        # would compete with the model load the first search is waiting on.
        while not self._stop.wait(self._every_seconds):
            for job in self._jobs:
                if self._stop.is_set():
                    return
                self._run_once(job)

    @staticmethod
    def _run_once(job: Job) -> None:
        try:
            job()
        except Exception:
            logger.exception("a background job failed")
