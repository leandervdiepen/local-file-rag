"""Adapter for the `PageSource` port over `FileKind.TEXT`, backed by the filesystem."""

from __future__ import annotations

from pathlib import Path

from sidecar.domain.errors import UnreadableFileError

PAGE_COUNT = 1


class TextFilePageSource:
    """Treats one text file as the one page it is. There is nothing to render."""

    def page_count(self, path: Path) -> int:
        try:
            with path.open("rb"):
                pass  # Confirms the file opens without reading its content twice.
        except OSError as exc:
            raise UnreadableFileError(f"Not a readable text file: {path}") from exc
        return PAGE_COUNT

    def page_text(self, path: Path, page_no: int) -> str:
        # errors="replace" so one stray non-UTF-8 byte never fails indexing
        # of an otherwise-fine file.
        return path.read_text(encoding="utf-8", errors="replace")

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        # A blank image would put a lie in the UI: there is nothing to show
        # for a page whose content is just text.
        raise UnreadableFileError(f"Text files have nothing to render: {path}")
