"""Turning a folder into an index."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from sidecar.application.ports import (
    FileProbe,
    FolderCrawler,
    ImageTextReader,
    IndexStore,
    PageSource,
)
from sidecar.domain.entities import FileCandidate, FileKind, FileState, IndexedFile, Page
from sidecar.domain.errors import EncryptedFileError, UnreadableFileError
from sidecar.domain.gate import GateDecision, SkipReason, pages_to_index, screen_image, screen_path
from sidecar.domain.identity import file_id, page_id
from sidecar.domain.kind_detection import MAGIC_PREFIX_BYTES, detect_kind, kind_from_suffix
from sidecar.domain.progress import IndexProgress

OCR_RENDER_LONG_SIDE_PX = 1600

# OCR is the expensive part of a first index, and a file with hundreds of
# scanned pages is rare enough that reading the first fifty and saying so
# beats making everyone else wait for it.
MAX_OCR_PAGES_PER_FILE = 50

ProgressSink = Callable[[IndexProgress], None]


class IndexFolder:
    """Puts every file under a folder into the index.

    Invariant: when this returns, every file the crawler found is in the
    index exactly once, either with its pages or with a reason it has none.
    A file is never silently absent, because the index screen's job is to be
    trusted and a missing file it never mentions is the one thing that would
    break that.

    Running it twice over an unchanged folder leaves the index unchanged.
    """

    def __init__(
        self,
        crawler: FolderCrawler,
        probe: FileProbe,
        sources: dict[FileKind, PageSource],
        ocr: ImageTextReader,
        store: IndexStore,
    ) -> None:
        self._crawler = crawler
        self._probe = probe
        self._sources = sources
        self._ocr = ocr
        self._store = store

    def run(self, folder_id: str, root: Path, on_progress: ProgressSink | None = None) -> IndexProgress:
        progress = IndexProgress(folder_id=folder_id)

        for candidate in self._crawler.crawl(root):
            progress = replace(progress, files_seen=progress.files_seen + 1, current_path=str(candidate.path))
            kind, decision = self._classify(candidate)

            if kind is None:
                self._store_skip(candidate, folder_id, decision)
                progress = replace(progress, files_skipped=progress.files_skipped + 1)
            else:
                pages = self._index_one(candidate, folder_id, kind)
                if pages is None:
                    progress = replace(progress, files_skipped=progress.files_skipped + 1)
                else:
                    progress = replace(
                        progress,
                        files_indexed=progress.files_indexed + 1,
                        pages_indexed=progress.pages_indexed + pages,
                    )

            if on_progress is not None:
                on_progress(progress)

        progress = replace(progress, done=True, current_path="")
        if on_progress is not None:
            on_progress(progress)
        return progress

    def _classify(self, candidate: FileCandidate) -> tuple[FileKind | None, GateDecision]:
        """Decide what a file is, cheapest checks first.

        Ordered by cost: the path costs nothing, the first eight bytes cost an
        open, and an image header costs a parse. A crawl of forty thousand
        files pays this per file, so the order is the performance design.
        """
        decision = screen_path(candidate.path, candidate.size_bytes)
        if not decision.accepted:
            return None, decision

        head = self._probe.head(candidate.path, MAGIC_PREFIX_BYTES)
        kind, decision = detect_kind(candidate.path, head)
        if kind is None:
            return None, decision

        if kind is FileKind.IMAGE:
            try:
                width, height = self._probe.image_size(candidate.path)
            except UnreadableFileError:
                return None, GateDecision(SkipReason.CORRUPT, {"kind": str(kind)})
            decision = screen_image(width, height)
            if not decision.accepted:
                return None, decision

        return kind, decision

    def _index_one(self, candidate: FileCandidate, folder_id: str, kind: FileKind) -> int | None:
        """Extract and store one file's pages. `None` when it turned out to be unreadable."""
        source = self._sources[kind]
        try:
            page_count = source.page_count(candidate.path)
        except EncryptedFileError:
            self._store_skip(candidate, folder_id, GateDecision(SkipReason.ENCRYPTED))
            return None
        except UnreadableFileError:
            self._store_skip(candidate, folder_id, GateDecision(SkipReason.CORRUPT))
            return None

        wanted, truncated = pages_to_index(page_count)
        owner = file_id(candidate.path)
        pages = [self._read_page(source, candidate.path, kind, owner, n) for n in range(1, wanted + 1)]

        self._store.upsert_file(
            IndexedFile(
                id=owner,
                path=candidate.path,
                folder_id=folder_id,
                content_hash=self._probe.content_hash(candidate.path, candidate.size_bytes),
                size_bytes=candidate.size_bytes,
                mtime=candidate.mtime,
                kind=kind,
                state=FileState.TEXT_INDEXED,
                page_count=wanted,
                truncated_pages=truncated,
            )
        )
        self._store.upsert_pages(pages)
        return len(pages)

    def _read_page(self, source: PageSource, path: Path, kind: FileKind, owner: str, page_no: int) -> Page:
        """Read one page's text, falling back to OCR when the page carries none.

        An empty text layer is the normal state of a screenshot and of a
        scanned PDF, so it routes to OCR rather than counting as a failure.
        """
        text = source.page_text(path, page_no)
        if not text.strip() and kind is not FileKind.TEXT and page_no <= MAX_OCR_PAGES_PER_FILE:
            text = self._ocr.read_text(source.render(path, page_no, OCR_RENDER_LONG_SIDE_PX))
        return Page(id=page_id(owner, page_no), file_id=owner, page_no=page_no, text=text)

    def _store_skip(self, candidate: FileCandidate, folder_id: str, decision: GateDecision) -> None:
        """Record a skipped file. It stays in the index so the index screen can explain it.

        The kind is whatever the name claimed, or unknown. Nothing opened the
        file, so anything more confident would be a guess in a table the
        index screen presents as fact.
        """
        reason = decision.reason or SkipReason.CORRUPT
        self._store.upsert_file(
            IndexedFile(
                id=file_id(candidate.path),
                path=candidate.path,
                folder_id=folder_id,
                content_hash="",
                size_bytes=candidate.size_bytes,
                mtime=candidate.mtime,
                kind=kind_from_suffix(candidate.path) or FileKind.UNKNOWN,
                state=FileState.SKIPPED,
                skip_reason=str(reason),
            )
        )
