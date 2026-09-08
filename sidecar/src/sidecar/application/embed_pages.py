"""Giving stored pages the vectors that stage 2 ranks them by.

Pages are embedded lazily, when a search first asks for them, so this runs
inside a search with a person watching. The work is batched so the model and
the store are paid per batch rather than per page, and progress is reported
per page so the wait stays legible.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import batched
from pathlib import Path

from sidecar.application.embedding_ports import PageEmbedder
from sidecar.application.ports import PageSource
from sidecar.application.store_ports import IndexStore, VectorStore
from sidecar.domain.entities import FileKind
from sidecar.domain.errors import UnreadableFileError
from sidecar.domain.identity import split_page_id
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.vectors import PageVectors

logger = logging.getLogger(__name__)

# The processor resizes to its patch budget from here, so a larger render only
# costs decode time and a smaller one loses detail the heatmap would show.
EMBED_LONG_SIDE_PX = 1024

# The embedder pays a fixed cost per call and the vector store per write, so
# one page at a time spends most of a search on overhead. A person watching
# "reading page 4 of 12" also needs the number to move every few pages, which
# is what keeps the batch this small.
EMBED_BATCH_PAGES = 8

ProgressSink = Callable[[EmbedProgress], None]


@dataclass(frozen=True)
class _PendingPage:
    """One page that still needs vectors, resolved to what rendering it takes."""

    page_id: str
    file_id: str
    path: Path
    page_no: int
    source: PageSource


class EmbedPages:
    """Gives a set of stored pages their vectors.

    Invariant: when `run` returns, every id in `page_ids` that names a stored
    page has vectors, and a page that already had them was neither
    re-rendered nor re-embedded. Progress is reported once per page embedded,
    in the order asked, and `pages_total` counts the pages that actually get
    vectors rather than the pages asked for: pages that already had them are
    left out from the start, and a page that turns out unreadable leaves the
    total as soon as that is known, so the last report always reads done.

    A page whose file has left the index, whose kind this build cannot
    render, or whose image will not decode is skipped and logged rather than
    raised. The search that asked for it still ranks that page by stage 1,
    which beats failing the whole search over one bad file.

    Nothing here writes the index. Whether a page has vectors is a fact about
    the vector store, and this used to also stamp it onto the page row so the
    index screen could count without opening the store. That made the `pages`
    table something two threads write, a search and a crawl, which
    `conventions/python.md` forbids for good reason. `ReadIndexStats` asks the
    vector store instead.
    """

    def __init__(
        self,
        store: IndexStore,
        sources: dict[FileKind, PageSource],
        embedder: PageEmbedder,
        vectors: VectorStore,
    ) -> None:
        self._store = store
        self._sources = sources
        self._embedder = embedder
        self._vectors = vectors

    def run(self, page_ids: Sequence[str], on_progress: ProgressSink | None = None) -> int:
        """Embed what still needs it and return how many pages were newly embedded.

        An id given twice is one page and is embedded once. Raises
        `ValidationError` for an id the identity module never produced: these
        ids come from the index, so a malformed one is a bug upstream rather
        than something to skip quietly.
        """
        pending = self._still_pending(page_ids)
        total = len(pending)
        embedded = 0
        for batch in batched(pending, EMBED_BATCH_PAGES):
            landed = self._embed_batch(batch)
            total -= len(batch) - len(landed)
            for page in landed:
                embedded += 1
                if on_progress is not None:
                    on_progress(EmbedProgress(pages_read=embedded, pages_total=total, current_page_id=page.page_id))
        return embedded

    def _still_pending(self, page_ids: Sequence[str]) -> list[_PendingPage]:
        """The pages that need vectors, in the order asked, each named once.

        Resolved before any work starts so the total reported is the work
        that will happen. Everything found missing here costs a lookup, not a
        render, so being honest about the total is cheap.
        """
        wanted = list(dict.fromkeys(page_ids))
        already = self._vectors.embedded_ids(wanted)
        pending: list[_PendingPage] = []
        for page_id in wanted:
            if page_id in already:
                continue
            page = self._locate(page_id)
            if page is not None:
                pending.append(page)
        return pending

    def _locate(self, page_id: str) -> _PendingPage | None:
        owner, page_no = split_page_id(page_id)
        file = self._store.get_file(owner)
        if file is None:
            logger.info("skipping page %s: its file is no longer in the index", page_id)
            return None
        source = self._sources.get(file.kind)
        if source is None:
            logger.info("skipping page %s: nothing renders %s files in this build", page_id, file.kind)
            return None
        return _PendingPage(page_id=page_id, file_id=owner, path=file.path, page_no=page_no, source=source)

    def _embed_batch(self, batch: Sequence[_PendingPage]) -> list[_PendingPage]:
        """Render, embed and store one batch. Returns the pages that got vectors, in order."""
        rendered = self._render(batch)
        vectors = self._embed(rendered)
        self._vectors.put_vectors(vectors)
        embedded_ids = {item.page_id for item in vectors}
        return [page for page, _ in rendered if page.page_id in embedded_ids]

    def _render(self, batch: Sequence[_PendingPage]) -> list[tuple[_PendingPage, bytes]]:
        rendered: list[tuple[_PendingPage, bytes]] = []
        for page in batch:
            try:
                rendered.append((page, page.source.render(page.path, page.page_no, EMBED_LONG_SIDE_PX)))
            except UnreadableFileError:
                logger.warning("skipping page %s: %s would not render", page.page_id, page.path)
        return rendered

    def _embed(self, rendered: Sequence[tuple[_PendingPage, bytes]]) -> list[PageVectors]:
        """One embedder call for the batch, then one per page if an image in it would not decode.

        The embedder refuses the whole call over one bad image without saying
        which, so the retry is what turns one corrupt page into one skip
        rather than a skipped batch.
        """
        try:
            return self._embedder.embed_pages([page.page_id for page, _ in rendered], [png for _, png in rendered])
        except UnreadableFileError:
            return self._embed_one_by_one(rendered)

    def _embed_one_by_one(self, rendered: Sequence[tuple[_PendingPage, bytes]]) -> list[PageVectors]:
        vectors: list[PageVectors] = []
        for page, png in rendered:
            try:
                vectors.extend(self._embedder.embed_pages([page.page_id], [png]))
            except UnreadableFileError:
                logger.warning("skipping page %s: its image would not decode", page.page_id)
        return vectors
