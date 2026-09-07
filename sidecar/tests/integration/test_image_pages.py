"""`ImagePageSource` against real Pillow-generated images."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from sidecar.domain.errors import UnreadableFileError
from sidecar.infrastructure.image_pages import ImagePageSource

pytestmark = pytest.mark.integration


def _png(path: Path, size: tuple[int, int], mode: str = "RGB") -> Path:
    Image.new(mode, size, "blue").save(path, format="PNG")
    return path


def test_page_count_is_always_one(tmp_path: Path) -> None:
    path = _png(tmp_path / "pic.png", (200, 100))

    assert ImagePageSource().page_count(path) == 1


def test_page_text_is_always_empty(tmp_path: Path) -> None:
    """An image's text comes from OCR, a different port; this one never claims to know it."""
    path = _png(tmp_path / "pic.png", (200, 100))

    assert ImagePageSource().page_text(path, 1) == ""


def test_render_downscales_to_the_requested_long_side(tmp_path: Path) -> None:
    path = _png(tmp_path / "big.png", (800, 400))

    png_bytes = ImagePageSource().render(path, 1, long_side_px=200)

    with Image.open(io.BytesIO(png_bytes)) as image:
        assert image.size == (200, 100)


def test_render_never_upscales_an_image_smaller_than_the_target(tmp_path: Path) -> None:
    path = _png(tmp_path / "small.png", (40, 20))

    png_bytes = ImagePageSource().render(path, 1, long_side_px=300)

    with Image.open(io.BytesIO(png_bytes)) as image:
        assert image.size == (40, 20)


def test_render_output_is_always_png(tmp_path: Path) -> None:
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (300, 150), "green").save(path, format="JPEG")

    png_bytes = ImagePageSource().render(path, 1, long_side_px=100)

    with Image.open(io.BytesIO(png_bytes)) as image:
        assert image.format == "PNG"


def test_palette_mode_image_renders_without_error(tmp_path: Path) -> None:
    path = tmp_path / "palette.png"
    Image.new("P", (500, 250)).save(path, format="PNG")

    png_bytes = ImagePageSource().render(path, 1, long_side_px=100)

    with Image.open(io.BytesIO(png_bytes)) as image:
        assert max(image.size) == 100


def test_extension_that_is_not_a_real_image_raises_unreadable(tmp_path: Path) -> None:
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not actually a png")

    with pytest.raises(UnreadableFileError):
        ImagePageSource().page_count(fake)
