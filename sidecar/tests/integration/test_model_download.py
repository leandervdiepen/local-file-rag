"""The aggregating progress bar, against real tqdm instances."""

from __future__ import annotations

import io
import threading

import pytest

from sidecar.infrastructure.model_download import _Aggregating

pytestmark = pytest.mark.integration


def test_several_files_downloading_at_once_report_one_pair_of_numbers() -> None:
    """The hub opens a bar per file, so one bar's numbers are a fraction of a fraction."""
    seen: list[tuple[int, int]] = []
    _Aggregating.reporting_to(lambda done, total: seen.append((done, total)))
    try:
        first = _Aggregating(total=100, file=io.StringIO())
        second = _Aggregating(total=300, file=io.StringIO())
        first.update(40)
        second.update(60)
    finally:
        first.close()
        second.close()
        _Aggregating.done()

    assert seen[-1] == (100, 400)


def test_a_run_with_nothing_left_to_download_reports_nothing() -> None:
    """Every file is already on disk on a second run, so no bar is ever opened."""
    seen: list[tuple[int, int]] = []
    _Aggregating.reporting_to(lambda done, total: seen.append((done, total)))
    _Aggregating.done()

    assert seen == []


def test_bars_from_an_earlier_download_do_not_count_towards_the_next_one() -> None:
    _Aggregating.reporting_to(lambda done, total: None)
    stale = _Aggregating(total=999, file=io.StringIO())
    stale.update(999)
    _Aggregating.done()

    seen: list[tuple[int, int]] = []
    _Aggregating.reporting_to(lambda done, total: seen.append((done, total)))
    try:
        fresh = _Aggregating(total=10, file=io.StringIO())
        fresh.update(5)
    finally:
        fresh.close()
        _Aggregating.done()

    assert seen[0] == (5, 10)


def test_a_disabled_bar_would_count_nothing_which_is_why_none_of_these_disable_one() -> None:
    """tqdm's update returns early when disabled, so `n` never moves. Pinned so the trap is not re-set."""
    seen: list[tuple[int, int]] = []
    _Aggregating.reporting_to(lambda done, total: seen.append((done, total)))
    try:
        bar = _Aggregating(total=10, disable=True)
        bar.update(5)
    finally:
        bar.close()
        _Aggregating.done()

    assert seen[-1] == (0, 10)


def test_finishing_a_download_does_not_deadlock_on_releasing_its_bars() -> None:
    """Dropping the last reference to a bar runs `tqdm.__del__` on this thread.

    That calls `close`, which reports, which wants the lock the caller is
    already holding. With a plain lock the first model download on a fresh
    machine hangs forever and the app never starts. Measured 2026-09-09.
    """
    _Aggregating.reporting_to(lambda done, total: None)
    _Aggregating(total=10, file=io.StringIO()).update(10)

    finished = threading.Event()
    threading.Thread(target=lambda: (_Aggregating.done(), finished.set()), daemon=True).start()

    assert finished.wait(10), "releasing the bars deadlocked"
