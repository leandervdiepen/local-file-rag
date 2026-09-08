"""Finding pages."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Protocol

from sidecar.application.embedding_ports import PageEmbedder
from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.identity import split_page_id
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.rerank import rank_by_maxsim
from sidecar.domain.search import PageHit
from sidecar.domain.vectors import QueryVectors

STAGE_ONE_CANDIDATE_LIMIT = 300
FILENAME_STAGE = "filename"
VISUAL_STAGE = "visual"

# D13: a search reads at most this many pages the model has never seen. Each
# costs about a second, so the cap is the difference between a search that
# finishes and one the user gives up on.
COLD_PAGE_CAP = 30

# Cold pages go to the model this many at a time so an abandoned search stops
# within a few seconds rather than after the whole cap.
COLD_PAGE_CHUNK = 4

# FR-7: fewer stage 1 hits than this and the query is asked of the whole
# vector store, because a query with no matching words is exactly the query
# this product exists for.
FALLBACK_BELOW = 5
FALLBACK_LIMIT = 20

ProgressSink = Callable[[EmbedProgress], None]


class ColdPageEmbedder(Protocol):
    """Gives pages their vectors. `EmbedPages` is the implementation; this is what `Search` needs of it."""

    def run(self, page_ids: Sequence[str], on_progress: ProgressSink | None = None) -> int: ...


class Search:
    """Finds the pages that answer a query.

    Invariant: results are ordered best first, and the order is stable for
    an unchanged index and an unchanged query. A user who searches the same
    thing twice sees the same list in the same order, because a result list
    that reshuffles under an unchanged query cannot be trusted to have
    ranked anything.

    An empty or whitespace query returns nothing rather than everything.
    Nothing typed is not a request for the whole index.
    """

    def __init__(
        self, store: IndexStore, vectors: VectorStore, embedder: PageEmbedder, cold_pages: ColdPageEmbedder
    ) -> None:
        self._store = store
        self._vectors = vectors
        self._embedder = embedder
        self._cold_pages = cold_pages

    def stage_one(self, query: str, limit: int = STAGE_ONE_CANDIDATE_LIMIT) -> list[PageHit]:
        """Full-text candidates, in milliseconds.

        This is what the user sees while stage two is still reading pages, so
        it never waits on anything expensive.
        """
        if not query.strip():
            return []
        return self._store.search_pages(query, limit)

    def stage_two(
        self,
        query: str,
        candidates: Sequence[PageHit],
        on_progress: ProgressSink | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> list[PageHit]:
        """The candidates re-ranked by what the pages look like.

        Filename matches stay pinned at the top in their stage 1 order: a user
        who typed a file's name meant that file. Below them every page with
        vectors is ordered by MaxSim, and pages the cap left unread keep their
        stage 1 order at the bottom, still present, because a page stage 1
        found is never dropped for not having been looked at yet.

        A thin candidate list is widened from the whole vector store first.
        Returns an empty list the moment `is_cancelled` says so: the caller
        has hung up and nothing it would get is worth another second of model.
        """
        if not query.strip():
            return []
        cancelled = is_cancelled or (lambda: False)
        # Checked before the encode, not only around the pages: a query costs a
        # quarter of a second of model time, and the caller typing another
        # letter has already made this result unwanted.
        if cancelled():
            return []
        query_vectors = self._embedder.embed_query(query)

        ordered = list(candidates)
        if len(ordered) < FALLBACK_BELOW:
            ordered = self._widen(query_vectors, ordered)
        if not ordered:
            return []

        if not self._embed_cold(ordered, on_progress, cancelled):
            return []

        stored = self._vectors.get_vectors([hit.page_id for hit in ordered])
        scores = dict(rank_by_maxsim(query_vectors, [stored[hit.page_id] for hit in ordered if hit.page_id in stored]))

        pinned = [hit for hit in ordered if hit.stage == FILENAME_STAGE]
        scored = [
            replace(hit, score=scores[hit.page_id], stage=VISUAL_STAGE)
            for hit in ordered
            if hit.stage != FILENAME_STAGE and hit.page_id in scores
        ]
        scored.sort(key=lambda hit: hit.score, reverse=True)
        unread = [hit for hit in ordered if hit.stage != FILENAME_STAGE and hit.page_id not in scores]
        return pinned + scored + unread

    def _widen(self, query_vectors: QueryVectors, candidates: list[PageHit]) -> list[PageHit]:
        seen = {hit.page_id for hit in candidates}
        widened = list(candidates)
        for page_id, _ in self._vectors.nearest(query_vectors, FALLBACK_LIMIT):
            if page_id in seen:
                continue
            hit = self._hit_for(page_id)
            if hit is not None:
                widened.append(hit)
                seen.add(page_id)
        return widened

    def _hit_for(self, page_id: str) -> PageHit | None:
        """A hit for a page the vector store knows but stage 1 did not surface. `None` if its file is gone."""
        file_id, page_no = split_page_id(page_id)
        file = self._store.get_file(file_id)
        if file is None:
            return None
        return PageHit(page_id, file_id, file.path, page_no, file.kind, score=0.0, stage=VISUAL_STAGE)

    def _embed_cold(
        self, ordered: list[PageHit], on_progress: ProgressSink | None, cancelled: Callable[[], bool]
    ) -> bool:
        """Read the unread candidates, best stage 1 first, up to the cap. False when cancelled part way."""
        page_ids = [hit.page_id for hit in ordered]
        embedded = self._vectors.embedded_ids(page_ids)
        cold = [page_id for page_id in page_ids if page_id not in embedded][:COLD_PAGE_CAP]
        done = 0
        for start in range(0, len(cold), COLD_PAGE_CHUNK):
            if cancelled():
                return False
            chunk = cold[start : start + COLD_PAGE_CHUNK]

            def relay(progress: EmbedProgress, done_before: int = done) -> None:
                if on_progress is not None:
                    on_progress(EmbedProgress(done_before + progress.pages_read, len(cold), progress.current_page_id))

            self._cold_pages.run(chunk, relay)
            done += len(chunk)
        return True
