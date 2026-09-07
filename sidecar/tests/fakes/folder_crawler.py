"""A real, in-memory FolderCrawler. Not a mock."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sidecar.domain.entities import FileCandidate
from sidecar.domain.errors import FolderUnreadableError


class FakeFolderCrawler:
    """Tests seed `files` with the candidates a crawl of some root should yield.

    `crawl` yields every candidate whose path is under the requested root,
    same as a real crawler restricted to one subtree. Add a root to
    `unreadable_roots` to make `crawl` raise `FolderUnreadableError` for it.
    """

    def __init__(self, files: dict[Path, FileCandidate] | None = None) -> None:
        self.files: dict[Path, FileCandidate] = dict(files or {})
        self.unreadable_roots: set[Path] = set()

    def crawl(self, root: Path) -> Iterator[FileCandidate]:
        if root in self.unreadable_roots:
            raise FolderUnreadableError(f"Cannot read folder: {root}")
        for path, candidate in self.files.items():
            if path == root or root in path.parents:
                yield candidate
