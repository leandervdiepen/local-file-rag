"""The thread that runs the background jobs, against real threading."""

from __future__ import annotations

import threading

import pytest

from sidecar.infrastructure.background_loop import BackgroundLoop

pytestmark = pytest.mark.integration

QUICK = 0.02
PATIENCE = 5.0


class Counter:
    def __init__(self, raises: bool = False) -> None:
        self.calls = 0
        self.raises = raises
        self.ran = threading.Event()

    def __call__(self) -> None:
        self.calls += 1
        self.ran.set()
        if self.raises:
            raise RuntimeError("this job is broken")


def test_a_job_runs_on_the_timer() -> None:
    job = Counter()
    loop = BackgroundLoop([job], every_seconds=QUICK)

    loop.start()
    try:
        assert job.ran.wait(PATIENCE)
    finally:
        loop.stop()


def test_every_job_runs_each_time_around() -> None:
    first, second = Counter(), Counter()
    loop = BackgroundLoop([first, second], every_seconds=QUICK)

    loop.start()
    try:
        assert first.ran.wait(PATIENCE)
        assert second.ran.wait(PATIENCE)
    finally:
        loop.stop()


def test_a_job_that_raises_does_not_stop_the_one_after_it() -> None:
    """These have nobody waiting on them, so an exception has nothing to reach."""
    broken, working = Counter(raises=True), Counter()
    loop = BackgroundLoop([broken, working], every_seconds=QUICK)

    loop.start()
    try:
        assert working.ran.wait(PATIENCE)
    finally:
        loop.stop()


def test_the_loop_waits_before_its_first_run() -> None:
    """Starting a job in the same second the process does competes with the model load."""
    job = Counter()
    loop = BackgroundLoop([job], every_seconds=PATIENCE)

    loop.start()
    try:
        assert not job.ran.wait(0.2)
    finally:
        loop.stop()


def test_stopping_ends_the_thread() -> None:
    loop = BackgroundLoop([Counter()], every_seconds=QUICK)
    loop.start()

    loop.stop()

    assert not any(thread.name == "background-loop" and thread.is_alive() for thread in threading.enumerate())


def test_starting_twice_is_one_thread() -> None:
    loop = BackgroundLoop([Counter()], every_seconds=QUICK)

    loop.start()
    loop.start()
    try:
        running = [thread for thread in threading.enumerate() if thread.name == "background-loop"]
        assert len(running) == 1
    finally:
        loop.stop()


def test_stopping_a_loop_that_never_started_is_allowed() -> None:
    BackgroundLoop([Counter()], every_seconds=QUICK).stop()
