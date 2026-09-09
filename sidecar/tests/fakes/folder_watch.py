"""A real, in-memory FolderWatch. Not a mock.

Keeps the set of watched roots rather than a call log, because what matters
about a watch is what it is pointed at now, not how it got there.
"""

from __future__ import annotations

from pathlib import Path


class FakeFolderWatch:
    def __init__(self) -> None:
        self.watching: set[Path] = set()

    def watch(self, root: Path) -> None:
        self.watching.add(root)

    def unwatch(self, root: Path) -> None:
        self.watching.discard(root)
