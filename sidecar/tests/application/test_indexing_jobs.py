"""What `IndexingJobs` does on a real thread. No mocks, no sleeping.

The folder store holds the job shut at its first move, so every assertion
about a job in flight lands at a point the test chose rather than at the
point a sleep happened to fall.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from sidecar.application.embed_pages import EmbedPages
from sidecar.application.index_folder import IndexFolder, ProgressSink
from sidecar.application.indexing_jobs import IndexingJobs
from sidecar.application.ports import Clock
from sidecar.domain.entities import Folder
from sidecar.domain.errors import FolderUnreadableError, IndexBusyError
from sidecar.domain.identity import file_id
from sidecar.domain.progress import IndexProgress
from tests.fakes.clock import FakeClock
from tests.fakes.folder_store import FakeFolderStore
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.vector_store import FakeVectorStore

# A guard, not a wait. The green path never reaches it, and a job that hangs
# fails the suite in seconds instead of freezing it.
TIMEOUT_SECONDS = 5.0

FIRST = Path("/corpus/a")
SECOND = Path("/corpus/b")
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class FakeIndexer:
    """A real, working stand-in for `IndexFolder`: two files per folder, then done.

    Add a folder id to `unreadable` and its crawl raises the way a real one
    does when the user has not granted access to the folder.
    """

    def __init__(self) -> None:
        self.unreadable: set[str] = set()
        self.crawled: list[str] = []

    def run(self, folder_id: str, root: Path, on_progress: ProgressSink | None = None) -> IndexProgress:
        self.crawled.append(folder_id)
        if folder_id in self.unreadable:
            raise FolderUnreadableError(f"{root} is not readable. Grant access in System Settings.")

        progress = IndexProgress(folder_id=folder_id)
        for number in (1, 2):
            progress = IndexProgress(
                folder_id=folder_id,
                files_seen=number,
                files_indexed=number,
                pages_indexed=number * 2,
                current_path=f"{root}/file-{number}",
            )
            _report(on_progress, progress)
        finished = replace(progress, current_path="", done=True)
        _report(on_progress, finished)
        return finished


def _report(on_progress: ProgressSink | None, progress: IndexProgress) -> None:
    if on_progress is not None:
        on_progress(progress)


class GatedFolderStore(FakeFolderStore):
    """A folder store that can hold a job at its first move, reading the list.

    A job blocked there has started and published nothing, which is the one
    moment a test can subscribe and be certain of seeing every snapshot.
    """

    def __init__(self, clock: Clock) -> None:
        super().__init__(clock)
        self.reading = threading.Event()
        self._open = threading.Event()
        self._open.set()

    def hold(self) -> None:
        self._open.clear()

    def release(self) -> None:
        self._open.set()

    def list(self) -> list[Folder]:
        self.reading.set()
        assert self._open.wait(TIMEOUT_SECONDS), "the job never read the folder list"
        return super().list()


class World:
    """One `IndexingJobs` over a fake indexer and a folder store the test drives."""

    def __init__(self, *paths: Path) -> None:
        self.indexer = FakeIndexer()
        self.store = GatedFolderStore(FakeClock(NOW))
        for path in paths:
            self.store.add(path)
        # An empty index, so the embedding pass finds no page to read and the
        # crawl is the whole job. Embedding has its own tests.
        self.index = FakeIndexStore()
        self.vectors = FakeVectorStore()
        self.embedder = FakePageEmbedder()
        self.jobs = IndexingJobs(
            cast(IndexFolder, self.indexer),
            self.store,
            self.index,
            self.vectors,
            EmbedPages(self.index, {}, self.embedder, self.vectors),
        )

    def start_held(self) -> None:
        """Start a job and return once it is running but has crawled nothing."""
        self.store.hold()
        self.jobs.start()
        assert self.store.reading.wait(TIMEOUT_SECONDS), "the job never started"

    def run_to_done(self) -> list[IndexProgress]:
        """Every snapshot one subscriber sees, from the first file to the terminal one."""
        self.start_held()
        snapshots = self.jobs.subscribe()
        self.store.release()
        return list(snapshots)


def test_counters_accumulate_across_folders_crawled_in_path_order() -> None:
    world = World(SECOND, FIRST)

    final = world.run_to_done()[-1]

    assert world.indexer.crawled == [file_id(FIRST), file_id(SECOND)]
    assert (final.files_seen, final.files_indexed, final.pages_indexed) == (4, 4, 8)
    assert (final.folder_id, final.current_path, final.done) == (file_id(SECOND), "", True)


def test_every_snapshot_reaches_every_subscriber_and_only_the_last_carries_done() -> None:
    world = World(FIRST, SECOND)
    world.start_held()
    watching, also_watching = world.jobs.subscribe(), world.jobs.subscribe()

    world.store.release()
    seen, also_seen = list(watching), list(also_watching)

    assert seen == also_seen
    assert [snapshot.current_path for snapshot in seen] == [
        f"{FIRST}/file-1",
        f"{FIRST}/file-2",
        f"{SECOND}/file-1",
        f"{SECOND}/file-2",
        "",
    ]
    assert [snapshot.done for snapshot in seen] == [False, False, False, False, True]


def test_a_second_start_while_a_job_runs_raises_index_busy() -> None:
    world = World(FIRST, SECOND)
    world.start_held()

    assert world.jobs.is_running() is True
    with pytest.raises(IndexBusyError) as raised:
        world.jobs.start()
    assert raised.value.code == "index_busy"

    snapshots = world.jobs.subscribe()
    world.store.release()
    assert list(snapshots)[-1].done is True
    assert world.jobs.is_running() is False


def test_a_folder_that_raises_leaves_its_counts_and_the_folder_after_it_alone() -> None:
    world = World(FIRST, SECOND)
    world.indexer.unreadable = {file_id(FIRST)}

    final = world.run_to_done()[-1]

    assert world.indexer.crawled == [file_id(FIRST), file_id(SECOND)]
    assert (final.files_seen, final.folder_id, final.done) == (2, file_id(SECOND), True)


def test_a_disabled_folder_is_not_crawled_and_an_empty_job_still_finishes() -> None:
    world = World(FIRST)
    world.store.set_enabled(file_id(FIRST), False)

    snapshots = world.run_to_done()

    assert world.indexer.crawled == []
    assert snapshots == [IndexProgress(folder_id="", done=True)]
    assert world.jobs.is_running() is False


def test_subscribing_with_no_job_running_ends_at_once_with_nothing() -> None:
    world = World(FIRST)

    assert list(world.jobs.subscribe()) == []
    assert world.jobs.progress() is None

    world.run_to_done()

    assert list(world.jobs.subscribe()) == []
    assert world.jobs.progress() == IndexProgress(
        folder_id=file_id(FIRST), done=True, files_seen=2, files_indexed=2, pages_indexed=4
    )
