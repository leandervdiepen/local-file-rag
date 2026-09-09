"""Embedding the files the user actually opens, before they search for them.

A page without vectors can still be found by its words, but it cannot be
ranked by what it looks like until something has read it, and a search that
has to read thirty pages first is a search that takes half a minute. Doing
that reading while the machine is idle and plugged in is the difference
between the first visual search being slow and it being instant.
"""

from __future__ import annotations

import logging
from typing import Protocol

from sidecar.application.embed_pages import EmbedPages
from sidecar.application.ports import PowerSource
from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.eviction import DEFAULT_CAP_BYTES
from sidecar.domain.idle import BATCH_PAGES, IDLE_AFTER_SECONDS, RECENT_FILE_LIMIT, Conditions, refusal

logger = logging.getLogger(__name__)


class Idleness(Protocol):
    """How long since the user did anything. `Activity` satisfies this."""

    def idle_seconds(self) -> float: ...


class Busyness(Protocol):
    """Whether a crawl is running. `IndexingJobs` satisfies this.

    A protocol rather than the class, because this needs one boolean and
    taking the job runner would make pre-embedding depend on everything a
    crawl can do.
    """

    def is_running(self) -> bool: ...


class PreEmbedRecent:
    """Embeds a few pages at a time, only while the machine can spare it.

    One batch per call rather than one job, so the loop that drives this can
    re-read the conditions between batches. A user who comes back to the
    machine waits for at most one batch to finish, not for the two hundred
    files this would get through if nothing stopped it.

    Stops entirely once the vector store is at its cap. Otherwise this and
    `EnforceStorageCap` take turns adding and removing the same pages for as
    long as the machine is left alone, which costs a night of GPU and leaves
    the index exactly where it started.
    """

    def __init__(
        self,
        store: IndexStore,
        vectors: VectorStore,
        embed_pages: EmbedPages,
        power: PowerSource,
        activity: Idleness,
        jobs: Busyness,
        cap_bytes: int = DEFAULT_CAP_BYTES,
        file_limit: int = RECENT_FILE_LIMIT,
        batch_pages: int = BATCH_PAGES,
        idle_after_seconds: float = IDLE_AFTER_SECONDS,
    ) -> None:
        self._store = store
        self._vectors = vectors
        self._embed_pages = embed_pages
        self._power = power
        self._activity = activity
        self._jobs = jobs
        self._cap_bytes = cap_bytes
        self._file_limit = file_limit
        self._batch_pages = batch_pages
        self._idle_after_seconds = idle_after_seconds

    def tick(self) -> int:
        """Embed up to one batch and return how many pages were read.

        Returns zero when the conditions refuse, and when everything the
        working set holds already has vectors. Never raises: this runs on a
        timer with nobody waiting on it, and a failure here must not take the
        loop down with it.
        """
        why_not = refusal(self._conditions(), self._idle_after_seconds)
        if why_not is not None:
            logger.debug("not pre-embedding: %s", why_not)
            return 0

        batch = self._next_batch()
        if not batch:
            return 0
        try:
            # What landed, not what was asked for. A page whose image will not
            # render is skipped inside `EmbedPages`, and counting it here would
            # report work that did not happen and hide a file that never embeds.
            embedded = self._embed_pages.run(batch)
        except Exception:
            logger.exception("pre-embedding %d pages failed", len(batch))
            return 0
        if embedded:
            logger.info("pre-embedded %d pages while the machine was idle", embedded)
        return embedded

    def _conditions(self) -> Conditions:
        return Conditions(
            on_ac_power=self._power.on_ac_power(),
            idle_seconds=self._activity.idle_seconds(),
            indexing=self._jobs.is_running(),
            # A full store means the cap evicts whatever this embeds, and the
            # two jobs spend the machine's night undoing each other. Measured
            # 2026-09-09 against a cap deliberately set below the corpus.
            storage_full=self._vectors.bytes_on_disk() >= self._cap_bytes,
        )

    def _next_batch(self) -> list[str]:
        """The next few pages of the working set that have no vectors, most recently used file first."""
        wanted: list[str] = []
        for file in self._store.recently_used_files(self._file_limit):
            page_ids = [page.id for page in self._store.get_pages(file.id)]
            embedded = self._vectors.embedded_ids(page_ids)
            wanted.extend(page_id for page_id in page_ids if page_id not in embedded)
            if len(wanted) >= self._batch_pages:
                break
        return wanted[: self._batch_pages]
