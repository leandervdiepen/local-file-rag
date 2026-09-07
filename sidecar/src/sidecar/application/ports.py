"""Ports the application layer depends on.

Each `Protocol` plus its docstrings is the entire contract: an agent
implementing an adapter reads this file and nothing else.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sidecar.domain.entities import FileCandidate, IndexedFile, Page
from sidecar.domain.search import IndexStats, PageHit


class Clock(Protocol):
    """Provides the current time. Use cases take time from here, never from the system clock directly."""

    def now(self) -> datetime:
        """Return the current time. Never blocks."""
        ...


class HealthProbe(Protocol):
    """Reports the facts `/health` exposes about the running sidecar."""

    def model_loaded(self) -> bool:
        """True once the retrieval model is loaded in memory. Never triggers loading it."""
        ...

    def db_path(self) -> Path:
        """The directory the index database lives in. Does not imply the directory exists yet."""
        ...


class FolderCrawler(Protocol):
    """Walks a folder tree and reports the files in it."""

    def crawl(self, root: Path) -> Iterator[FileCandidate]:
        """Yield every file under `root`, lazily.

        Does not follow symlinks, so a link loop cannot hang a crawl.
        Does not descend into a directory the gate excludes, because the point
        of excluding `node_modules` is not paying to walk it.
        Yields nothing and raises nothing if `root` does not exist. A folder the
        user removed is an empty folder, not a crash.
        Raises `FolderUnreadableError` when the folder exists but permission is denied,
        because that one the user can fix.
        """
        ...


class FileProbe(Protocol):
    """Reads the few bytes and facts that decide a file's fate, without parsing it."""

    def head(self, path: Path, count: int) -> bytes:
        """First `count` bytes, or fewer if the file is shorter. Never raises on a short file."""
        ...

    def content_hash(self, path: Path, size_bytes: int) -> str:
        """A stable content identity used to detect a change and to dedupe.

        Hashes the whole file below 50 MB. Above it, samples, so a large file
        never costs a full read on every rescan. Two files with the same hash
        are treated as the same content.
        """
        ...

    def image_size(self, path: Path) -> tuple[int, int]:
        """Width and height in pixels, read from the header rather than by decoding.

        Raises `UnreadableFileError` when the bytes are not a decodable image.
        """
        ...


class PageSource(Protocol):
    """Reads one kind of file as pages: how many, what each says, what each looks like.

    One implementation per `FileKind`. The composition root builds the mapping
    and `IndexFolder` dispatches on kind, so no adapter knows about another.

    A text file is one page. An image is one page. A PDF is one page per page.
    """

    def page_count(self, path: Path) -> int:
        """Number of pages. Always at least 1 for a file that opened.

        Raises `EncryptedFileError` when the file needs a password.
        Raises `UnreadableFileError` when it will not open at all.
        """
        ...

    def page_text(self, path: Path, page_no: int) -> str:
        """The text of one 1-based page, empty when the page carries none.

        An empty string is a real answer: a scanned PDF page has no text layer,
        and the caller decides whether to send it to OCR.
        """
        ...

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        """The page as PNG bytes, scaled so its long side is `long_side_px`.

        Never upscales. A page smaller than the target comes back at its own size.
        """
        ...


class ImageTextReader(Protocol):
    """Reads the text that exists only inside an image."""

    def read_text(self, image_png: bytes) -> str:
        """Text found in the image, empty when there is none.

        Never raises for an image with no text. That is the common case, not an error.
        """
        ...


class IndexStore(Protocol):
    """The one place index state lives. A crash loses nothing that got here."""

    def upsert_file(self, file: IndexedFile) -> None:
        """Insert or replace by `file.id`. Idempotent: the same file twice is one row."""
        ...

    def upsert_pages(self, pages: Sequence[Page]) -> None:
        """Insert or replace by `page.id`, as one batch. Idempotent."""
        ...

    def forget_file(self, file_id: str) -> None:
        """Remove a file and its pages. Silent when the file is already gone."""
        ...

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        """Full-text search over page and file text, best first.

        Returns an empty list for a query that matches nothing, and for an
        empty query. Never raises on punctuation or an unbalanced quote: a
        search box takes whatever the user typed.
        """
        ...

    def stats(self) -> IndexStats:
        """Counts for the index screen, computed from rows rather than kept as counters."""
        ...
