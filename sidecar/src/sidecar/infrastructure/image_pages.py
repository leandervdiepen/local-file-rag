"""Adapter for the `PageSource` port over `FileKind.IMAGE`, backed by Pillow."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from sidecar.domain.errors import UnreadableFileError

PAGE_COUNT = 1


class ImagePageSource:
    """Treats one image file as the one page it is.

    An image carries no text layer of its own: `page_text` is always empty
    and OCR, a different port, is the use case's job to call.
    """

    def page_count(self, path: Path) -> int:
        try:
            with Image.open(path):
                pass  # Opening already reads and validates the header; nothing more to check.
        except OSError as exc:
            raise UnreadableFileError(f"Not a decodable image: {path}") from exc
        return PAGE_COUNT

    def page_text(self, path: Path, page_no: int) -> str:
        return ""

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        with Image.open(path) as image:
            width, height = image.size
            scale = min(long_side_px / max(width, height), 1.0)  # never upscale
            target = (round(width * scale), round(height * scale))
            # P (palette) mode interpolates badly under LANCZOS; every other
            # mode Pillow decodes for us (RGB, RGBA, L, ...) resizes cleanly.
            source = image.convert("RGBA") if image.mode == "P" else image
            resized = source if target == source.size else source.resize(target, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            resized.save(buffer, format="PNG")
            return buffer.getvalue()
