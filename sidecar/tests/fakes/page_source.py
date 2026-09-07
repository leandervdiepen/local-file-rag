"""A real, in-memory PageSource. Not a mock."""

from __future__ import annotations

from pathlib import Path

from sidecar.domain.errors import EncryptedFileError, UnreadableFileError


class FakePageSource:
    """Backed by a dict of path to its pages' text. One fake covers every `FileKind`.

    Tests seed `pages` with the text each 1-based page returns, and
    `renders` with the PNG bytes a given page renders as. A path added to
    `encrypted` or `unreadable` fails `page_count` the way a real adapter
    would fail to open that file.
    """

    def __init__(self, pages: dict[Path, list[str]] | None = None) -> None:
        self.pages: dict[Path, list[str]] = dict(pages or {})
        self.renders: dict[tuple[Path, int], bytes] = {}
        self.encrypted: set[Path] = set()
        self.unreadable: set[Path] = set()

    def page_count(self, path: Path) -> int:
        if path in self.encrypted:
            raise EncryptedFileError(f"PDF needs a password: {path}")
        if path in self.unreadable or path not in self.pages:
            raise UnreadableFileError(f"Not a readable file: {path}")
        return len(self.pages[path])

    def page_text(self, path: Path, page_no: int) -> str:
        return self.pages[path][page_no - 1]

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        return self.renders.get((path, page_no), b"")
