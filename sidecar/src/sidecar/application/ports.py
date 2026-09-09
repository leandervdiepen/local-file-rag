"""Ports the application layer depends on.

Each `Protocol` plus its docstrings is the entire contract: an agent
implementing an adapter reads this file and nothing else.

The ports that hold state are in `store_ports.py`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sidecar.domain.answers import AnswerChunk, AnswerRequest
from sidecar.domain.entities import FileCandidate


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

        A `root` that is itself a file is a tree of one and yields that file,
        which is how a single changed file is re-indexed through the same
        pipeline as a crawl rather than a second one that could disagree with
        it about the gate, about OCR or about page ids.
        Does not follow symlinks, so a link loop cannot hang a crawl.
        Does not descend into a directory the gate excludes, because the point
        of excluding `node_modules` is not paying to walk it.
        Yields nothing and raises nothing if `root` does not exist. A folder the
        user removed is an empty folder, not a crash.
        Raises `FolderUnreadableError` when the folder exists but permission is denied,
        because that one the user can fix.
        """
        ...


class FolderWatch(Protocol):
    """Watches folders for changes and reports them once they settle.

    The application layer decides which folders are watched. When and how a
    change is noticed is the adapter's business, and a build with no watcher
    satisfies this port by doing nothing.
    """

    def watch(self, root: Path) -> None:
        """Start reporting changes under `root`. Idempotent: watching twice is watched once."""
        ...

    def unwatch(self, root: Path) -> None:
        """Stop reporting changes under `root`. Silent for a root that was never watched."""
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


class Answerer(Protocol):
    """Streams an answer grounded in the page images it is given.

    Implementations translate wire format and nothing else. They do not build
    prompts, parse citations, price the exchange or decide which pages to
    send, because those are the same for every provider and live in the
    domain.
    """

    def stream(self, request: AnswerRequest) -> Iterator[AnswerChunk]:
        """Yield chunks until the answer ends, then stop.

        Yields text as it arrives and usage when the provider reports it,
        which is usually once at the end and sometimes never.

        Raises `AnswerUnavailableError` when the provider refuses, is out of
        quota, or is unreachable. That error carries a message a person can
        act on, because it is shown in the chat panel.

        Abandons the request if the consumer stops iterating, so a user who
        closes the panel does not pay for the rest of an answer.
        """
        ...
