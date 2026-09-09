"""Adapter that turns FSEvents into `FileChange`s, debounced.

The one job here is translation and timing. What a change means is
`domain/changes.py`, and what to do about it is `ApplyChanges`, so this file
holds no rule about which files matter.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import (
    DirDeletedEvent,
    DirMovedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from sidecar.domain.changes import ChangeKind, FileChange

logger = logging.getLogger(__name__)

# Long enough to swallow the write, rename, write that one save produces, and
# short enough to stay inside the five seconds the plan promises between
# dropping a file in and finding it.
DEBOUNCE_SECONDS = 1.5

Batch = Callable[[list[FileChange], dict[Path, int]], None]


class FolderWatcher:
    """Watches folders and hands over batches of changes once they settle.

    Nothing is delivered while events are still arriving. An editor saving a
    large file emits a burst, and re-indexing on the first of them reads a
    half written file; waiting for quiet reads it once, whole.

    The size of each touched path is taken here, at the moment the batch is
    cut, because the gate rule needs one and the domain must not read a disk.
    """

    def __init__(self, on_batch: Batch, debounce_seconds: float = DEBOUNCE_SECONDS) -> None:
        self._on_batch = on_batch
        self._debounce_seconds = debounce_seconds
        self._observer = Observer()
        self._lock = threading.Lock()
        self._pending: list[FileChange] = []
        self._timer: threading.Timer | None = None

    def watch(self, root: Path) -> None:
        self._observer.schedule(_Handler(self._record), str(root), recursive=True)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        """Stop watching and deliver whatever was pending, so a quit loses no change."""
        self._observer.stop()
        self._observer.join(timeout=5)
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._deliver()

    def _record(self, change: FileChange) -> None:
        with self._lock:
            self._pending.append(change)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._deliver)
            self._timer.daemon = True
            self._timer.start()

    def _deliver(self) -> None:
        with self._lock:
            batch, self._pending = self._pending, []
            self._timer = None
        if not batch:
            return
        try:
            self._on_batch(batch, _sizes_of(batch))
        except Exception:
            logger.exception("applying %d filesystem changes failed", len(batch))


def _sizes_of(batch: list[FileChange]) -> dict[Path, int]:
    """One stat per touched path. A path that has already gone reads as zero, which the gate refuses."""
    sizes: dict[Path, int] = {}
    for change in batch:
        if change.kind is ChangeKind.TOUCHED:
            try:
                sizes[change.path] = change.path.stat().st_size
            except OSError:
                sizes[change.path] = 0
    return sizes


class _Handler(FileSystemEventHandler):
    """Translates watchdog's events into the two the domain knows about."""

    def __init__(self, record: Callable[[FileChange], None]) -> None:
        self._record = record

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory and not isinstance(event, DirDeletedEvent | DirMovedEvent):
            return
        for path, kind in _changes_in(event):
            self._record(FileChange(path, kind))


def _changes_in(event: FileSystemEvent) -> list[tuple[Path, ChangeKind]]:
    """A move is two changes because the index keys on path, and that is what a move does to it."""
    source = Path(_as_str(event.src_path))
    if isinstance(event, FileMovedEvent | DirMovedEvent):
        return [(source, ChangeKind.GONE), (Path(_as_str(event.dest_path)), ChangeKind.TOUCHED)]
    if isinstance(event, FileDeletedEvent | DirDeletedEvent):
        return [(source, ChangeKind.GONE)]
    return [(source, ChangeKind.TOUCHED)]


def _as_str(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value
