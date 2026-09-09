"""Running an index crawl as a background job.

A crawl of a real folder takes minutes, so nothing here is called from a
request thread except `start`, which returns as soon as the thread exists.
Everything a caller can read afterwards is a snapshot, never a wait.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from dataclasses import replace
from queue import Queue
from uuid import uuid4

from sidecar.application.embed_pages import EmbedPages
from sidecar.application.index_folder import IndexFolder
from sidecar.application.store_ports import FolderStore, IndexStore, VectorStore
from sidecar.domain.entities import Folder
from sidecar.domain.errors import FolderUnreadableError, IndexBusyError
from sidecar.domain.progress import EmbedProgress, FolderFailure, IndexProgress

logger = logging.getLogger(__name__)

# macOS decides this, not the app: the folders it guards are the ones people
# index first, and the dialog is never shown twice.
_PERMISSION_DENIED = (
    "macOS is not letting this app read that folder. "
    "Open System Settings, Privacy and Security, Full Disk Access, and turn it on for this app."
)


class IndexingJobs:
    """Crawls the enabled folders on one background thread.

    Invariant: one job runs at a time, and every job that starts publishes a
    snapshot carrying `done`, whatever any folder does to it. A subscriber
    always reaches an end, so the index screen never sits on a spinner for a
    job that is no longer running.

    Counters accumulate across folders, so a snapshot is the running total
    for the whole job rather than for the folder in front of it, and its
    `folder_id` is the folder being crawled at that moment.
    """

    def __init__(
        self,
        index_folder: IndexFolder,
        folders: FolderStore,
        store: IndexStore,
        vectors: VectorStore,
        embed_pages: EmbedPages,
    ) -> None:
        self._index_folder = index_folder
        self._folders = folders
        self._store = store
        self._vectors = vectors
        self._embed_pages = embed_pages
        self._lock = threading.Lock()
        self._running = False
        self._latest: IndexProgress | None = None
        self._subscribers: list[Queue[IndexProgress]] = []

    def start(self) -> str:
        """Start a crawl of every enabled folder, in path order, and return the job id.

        Raises `IndexBusyError` when a job is already running, because two
        crawls writing the index at once is the one thing the store cannot
        take. Returns normally when no folder is enabled: that job finishes
        at once with a done snapshot, which is an answer, not a failure.
        """
        with self._lock:
            if self._running:
                raise IndexBusyError("A rescan is already running. Wait for it to finish before starting another.")
            self._running = True
            self._latest = IndexProgress(folder_id="")
        job_id = uuid4().hex
        threading.Thread(target=self._run_job, name=f"indexing-{job_id}", daemon=True).start()
        return job_id

    def is_running(self) -> bool:
        """True from the moment a job starts until its done snapshot is published."""
        with self._lock:
            return self._running

    def progress(self) -> IndexProgress | None:
        """The latest snapshot, `None` before the first job of this process."""
        with self._lock:
            return self._latest

    def subscribe(self) -> Iterator[IndexProgress]:
        """Yield each new snapshot as it happens, ending on the one that carries `done`.

        Yields nothing and ends at once when no job is running, so a caller
        never waits on work that is not happening. The subscription is taken
        here rather than on the first `next`, so a snapshot published between
        this call and that one is still delivered.

        Every subscriber gets its own queue and sees every snapshot. Nothing
        the job publishes blocks on a subscriber, so a client that stops
        reading costs the crawl nothing.
        """
        with self._lock:
            if not self._running:
                return iter(())
            subscriber: Queue[IndexProgress] = Queue()
            self._subscribers.append(subscriber)
        return self._drain(subscriber)

    def _drain(self, subscriber: Queue[IndexProgress]) -> Iterator[IndexProgress]:
        try:
            while True:
                snapshot = subscriber.get()
                yield snapshot
                if snapshot.done:
                    return
        finally:
            self._forget(subscriber)

    def _forget(self, subscriber: Queue[IndexProgress]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def _run_job(self) -> None:
        totals = IndexProgress(folder_id="")
        try:
            for folder in self._folders.list():
                if folder.enabled:
                    totals = self._crawl(folder, totals)
            totals = self._embed(totals)
        finally:
            self._finish(replace(totals, current_path="", done=True))

    def _embed(self, totals: IndexProgress) -> IndexProgress:
        """Give every indexed page its vectors, after the text is in.

        Text first, because it is seconds for the whole folder and it makes
        search work immediately. Vectors second, because they are the slow
        part and a page that has none can still be found by its words.

        This is what makes visual search possible at all. Stage 2 can only
        rank pages that have vectors, and a page only gets them here or by
        being a text candidate, so without this pass a page whose words never
        match is unreachable no matter how well the model would have scored
        it. Measured 2026-09-09: it is exactly why the day 2 acceptance query
        failed before this existed.
        """
        pending = self._pages_without_vectors()
        if not pending:
            return totals
        current = totals

        def on_progress(step: EmbedProgress) -> None:
            nonlocal current
            current = replace(totals, pages_embedded=step.pages_read, current_path=step.current_page_id)
            self._publish(current)

        try:
            self._embed_pages.run(pending, on_progress)
        except Exception:
            logger.exception("embedding pages failed")
        return current

    def _pages_without_vectors(self) -> list[str]:
        """Every indexed page with no vectors yet, oldest file first so a rescan resumes where it stopped."""
        page_ids: list[str] = []
        for file in self._store.indexed_files():
            page_ids.extend(page.id for page in self._store.get_pages(file.id))
        embedded = self._vectors.embedded_ids(page_ids)
        return [page_id for page_id in page_ids if page_id not in embedded]

    def _crawl(self, folder: Folder, base: IndexProgress) -> IndexProgress:
        """Crawl one folder and return the totals it leaves for the next one.

        A folder that raises is recorded and left behind: one unreadable folder
        must not cost the user the folders queued after it, and the counts it
        did reach stay in the total. The failure travels in the snapshot, so
        the index screen can say which folder and what to do, rather than
        showing a crawl that found nothing for no visible reason.
        """
        totals = replace(base, folder_id=folder.id)

        def on_progress(step: IndexProgress) -> None:
            nonlocal totals
            totals = _accumulate(base, folder.id, step)
            if not step.done:
                self._publish(totals)

        try:
            self._index_folder.run(folder.id, folder.path, on_progress)
        except FolderUnreadableError as denied:
            logger.warning("cannot read %s: %s", folder.path, denied.message)
            totals = _with_failure(totals, FolderFailure(str(folder.path), _PERMISSION_DENIED))
        except Exception as failure:
            logger.exception("indexing %s failed", folder.path)
            totals = _with_failure(totals, FolderFailure(str(folder.path), str(failure)))
        return replace(totals, current_path="")

    def _publish(self, snapshot: IndexProgress) -> None:
        with self._lock:
            self._latest = snapshot
            for subscriber in self._subscribers:
                subscriber.put_nowait(snapshot)

    def _finish(self, final: IndexProgress) -> None:
        with self._lock:
            self._latest = final
            for subscriber in self._subscribers:
                subscriber.put_nowait(final)
            self._subscribers.clear()
            self._running = False


def _accumulate(base: IndexProgress, folder_id: str, step: IndexProgress) -> IndexProgress:
    """Fold one folder's step into the totals of the folders already crawled."""
    return IndexProgress(
        folder_id=folder_id,
        files_seen=base.files_seen + step.files_seen,
        files_indexed=base.files_indexed + step.files_indexed,
        files_skipped=base.files_skipped + step.files_skipped,
        pages_indexed=base.pages_indexed + step.pages_indexed,
        current_path=step.current_path,
        failures=base.failures,
    )


def _with_failure(totals: IndexProgress, failure: FolderFailure) -> IndexProgress:
    return replace(totals, failures=(*totals.failures, failure))
