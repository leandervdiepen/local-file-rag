"""`AppleVisionTextReader` against real Vision OCR, on this machine only.

Uses Pillow's bundled scalable font so the rendered text does not depend on
which system fonts happen to be installed.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from sidecar.infrastructure.vision_ocr import AppleVisionTextReader

pytestmark = pytest.mark.integration


def _rendered(lines: list[tuple[str, tuple[int, int]]], size: tuple[int, int] = (500, 300)) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=40)
    for text, position in lines:
        draw.text(position, text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_reads_real_text_from_a_rendered_image() -> None:
    png = _rendered([("Sidecar Test 123", (10, 10))])

    text = AppleVisionTextReader().read_text(png)

    assert "Sidecar" in text
    assert "123" in text


def test_blank_image_returns_empty_string_not_an_error() -> None:
    blank = Image.new("RGB", (200, 200), "white")
    buffer = io.BytesIO()
    blank.save(buffer, format="PNG")

    text = AppleVisionTextReader().read_text(buffer.getvalue())

    assert text == ""


def test_multiple_lines_come_back_in_top_to_bottom_reading_order() -> None:
    # Drawn bottom line first, so a naive detector order would read reversed.
    png = _rendered([("Second line", (10, 150)), ("First line", (10, 10))])

    text = AppleVisionTextReader().read_text(png)
    lines = text.splitlines()

    assert lines == ["First line", "Second line"]
