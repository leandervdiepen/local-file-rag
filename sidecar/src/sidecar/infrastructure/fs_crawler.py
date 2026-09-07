"""Adapter for the `FolderCrawler` port, backed by `os.scandir`."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sidecar.domain.entities import FileCandidate
from sidecar.domain.errors import FolderUnreadableError
from sidecar.domain.gate import is_excluded_dir

logger = logging.getLogger(__name__)


class FilesystemCrawler:
    """Walks a folder tree with `os.scandir`, never following a symlink.

    Skips a gate-excluded directory before opening it, which is what keeps a
    crawl of forty thousand files from paying to walk `node_modules`.
    """

    def crawl(self, root: Path) -> Iterator[FileCandidate]:
        if not root.is_dir():
            return  # A folder the user removed is an empty folder, not a crash.
        try:
            entries = list(os.scandir(root))
        except OSError as exc:
            raise FolderUnreadableError(f"Cannot read folder: {root}") from exc
        yield from self._candidates(entries)

    def _walk(self, directory: Path) -> Iterator[FileCandidate]:
        try:
            entries = list(os.scandir(directory))
        except OSError:
            # One bad folder must not kill a crawl of the other 39,999 files.
            logger.warning("skipping unreadable directory: %s", directory)
            return
        yield from self._candidates(entries)

    def _candidates(self, entries: list[os.DirEntry[str]]) -> Iterator[FileCandidate]:
        for entry in entries:
            try:
                # follow_symlinks=False: a symlink is neither a dir nor a file
                # by this check, so a link loop is never entered to begin with.
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                logger.warning("skipping unreadable entry: %s", entry.path)
                continue

            if is_dir:
                if not is_excluded_dir(entry.name):
                    yield from self._walk(Path(entry.path))
            elif is_file:
                yield from self._file_candidate(entry)

    def _file_candidate(self, entry: os.DirEntry[str]) -> Iterator[FileCandidate]:
        try:
            stat = entry.stat(follow_symlinks=False)
        except OSError:
            logger.warning("skipping unreadable entry: %s", entry.path)
            return
        yield FileCandidate(
            path=Path(entry.path),
            size_bytes=stat.st_size,
            mtime=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )
