"""`FolderWatcher` against real files on disk and real FSEvents."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from sidecar.domain.changes import ChangeKind, FileChange
from sidecar.infrastructure.fs_watcher import FolderWatcher

pytestmark = pytest.mark.integration

# A guard, not a wait. The green path is woken by the batch arriving.
TIMEOUT_SECONDS = 15.0
DEBOUNCE = 0.2


class Batches:
    """Collects delivered batches and lets a test wait for one rather than sleep."""

    def __init__(self) -> None:
        self.delivered: list[list[FileChange]] = []
        self.sizes: dict[Path, int] = {}
        self.arrived = threading.Event()

    def __call__(self, changes: list[FileChange], sizes: dict[Path, int]) -> None:
        self.delivered.append(changes)
        self.sizes.update(sizes)
        self.arrived.set()

    def wait(self) -> list[FileChange]:
        assert self.arrived.wait(TIMEOUT_SECONDS), "no batch was delivered"
        self.arrived.clear()
        return self.delivered[-1]

    @property
    def paths(self) -> list[Path]:
        return [change.path for batch in self.delivered for change in batch]


@pytest.fixture
def watching(tmp_path: Path):
    batches = Batches()
    watcher = FolderWatcher(batches, debounce_seconds=DEBOUNCE)
    watcher.watch(tmp_path)
    watcher.start()
    try:
        yield batches, watcher
    finally:
        watcher.stop()


def test_a_file_dropped_in_the_folder_is_reported_as_touched(watching, tmp_path: Path) -> None:
    batches, _ = watching

    (tmp_path / "dropped.pdf").write_bytes(b"%PDF-1.4 content")

    batch = batches.wait()
    assert FileChange(tmp_path / "dropped.pdf", ChangeKind.TOUCHED) in batch


def test_the_size_of_a_touched_file_comes_with_the_batch(watching, tmp_path: Path) -> None:
    """The gate rule needs a size and the domain must not read a disk, so the watcher takes it."""
    batches, _ = watching
    payload = b"%PDF-1.4 " + b"x" * 500

    (tmp_path / "sized.pdf").write_bytes(payload)

    batches.wait()
    assert batches.sizes[tmp_path / "sized.pdf"] == len(payload)


def test_a_deleted_file_is_reported_as_gone(watching, tmp_path: Path) -> None:
    batches, _ = watching
    target = tmp_path / "doomed.pdf"
    target.write_bytes(b"%PDF-1.4")
    batches.wait()

    target.unlink()

    batch = batches.wait()
    assert FileChange(target, ChangeKind.GONE) in batch


def test_a_rename_is_the_old_path_gone_and_the_new_one_touched(watching, tmp_path: Path) -> None:
    batches, _ = watching
    before = tmp_path / "before.pdf"
    before.write_bytes(b"%PDF-1.4")
    batches.wait()

    after = tmp_path / "after.pdf"
    before.rename(after)

    batch = batches.wait()
    assert FileChange(before, ChangeKind.GONE) in batch
    assert FileChange(after, ChangeKind.TOUCHED) in batch


def test_a_burst_of_writes_arrives_as_one_batch(watching, tmp_path: Path) -> None:
    """Re-indexing on the first event of a save reads a half written file."""
    batches, _ = watching
    target = tmp_path / "saved.md"

    for n in range(5):
        target.write_text(f"revision {n}\n")

    batches.wait()
    assert len(batches.delivered) == 1, f"the burst arrived as {len(batches.delivered)} batches"


def test_stopping_delivers_a_change_still_inside_the_debounce_window(tmp_path: Path) -> None:
    """A quit must not lose a change the watcher has already seen but not yet delivered.

    The debounce is set long enough that nothing can arrive on its own, so the
    only thing that can deliver this batch is the flush in `stop`. What the
    operating system has not reported yet is genuinely lost, and that is fine:
    the index is rebuilt from disk by the next rescan.
    """
    batches = Batches()
    watcher = FolderWatcher(batches, debounce_seconds=60.0)
    watcher.watch(tmp_path)
    watcher.start()
    (tmp_path / "late.md").write_text("written just before quitting")

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while not watcher._pending and time.monotonic() < deadline:
        time.sleep(0.05)
    assert watcher._pending, "the watcher never saw the write, so there is nothing to flush"

    watcher.stop()

    assert (tmp_path / "late.md") in batches.paths
    assert batches.delivered, "stopping delivered nothing although a change was pending"
