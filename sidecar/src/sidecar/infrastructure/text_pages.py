"""Adapter for the `PageSource` port over `FileKind.TEXT`, backed by the filesystem."""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.ImageFont import ImageFont as BitmapFont

from sidecar.domain.errors import UnreadableFileError

PAGE_COUNT = 1

# A text file is laid out once, at the size the vision model reads pages at,
# and scaled down from there. A thumbnail rendered directly at 320 px would
# set type too small to rasterize into anything, while a downscaled page keeps
# the grey texture of lines that makes a note look like a note.
CANONICAL_LONG_SIDE_PX = 1600
PAGE_ASPECT = 1.414
MARGIN_RATIO = 0.06
FONT_SIZE_PX = 20
LINE_HEIGHT_RATIO = 1.45
TAB_WIDTH = 4
PAPER = (255, 255, 255)
INK = (34, 32, 30)

# The system monospace faces, in order of preference. This sidecar already
# depends on macOS for OCR, so leaning on its fonts adds nothing new.
FONT_PATHS = ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf")


class TextFilePageSource:
    """Treats one text file as the one page it is, and draws it the way an editor would."""

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
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise UnreadableFileError(f"Not a readable text file: {path}") from exc

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        page = _lay_out(self.page_text(path, page_no))
        target = min(long_side_px, CANONICAL_LONG_SIDE_PX)
        if target < CANONICAL_LONG_SIDE_PX:
            scale = target / CANONICAL_LONG_SIDE_PX
            page = page.resize((round(page.width * scale), round(page.height * scale)), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        page.save(buffer, format="PNG")
        return buffer.getvalue()


def _lay_out(text: str) -> Image.Image:
    height = CANONICAL_LONG_SIDE_PX
    width = round(height / PAGE_ASPECT)
    margin = round(width * MARGIN_RATIO)
    font = _load_font()
    columns = max(1, int((width - 2 * margin) // font.getlength("M")))
    line_height = round(FONT_SIZE_PX * LINE_HEIGHT_RATIO)
    max_lines = max(1, (height - 2 * margin) // line_height)

    page = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(page)
    for index, line in enumerate(_wrap(text, columns)[:max_lines]):
        draw.text((margin, margin + index * line_height), line, fill=INK, font=font)
    return page


def _wrap(text: str, columns: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        line = raw.expandtabs(TAB_WIDTH)
        lines.extend(textwrap.wrap(line, columns, break_long_words=True, replace_whitespace=False) or [""])
    return lines


def _load_font() -> FreeTypeFont | BitmapFont:
    for candidate in FONT_PATHS:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, FONT_SIZE_PX)
    return ImageFont.load_default(size=FONT_SIZE_PX)
