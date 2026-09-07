"""`TextFilePageSource` against real files on disk, including invalid UTF-8."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from sidecar.domain.errors import UnreadableFileError
from sidecar.infrastructure.text_pages import CANONICAL_LONG_SIDE_PX, TextFilePageSource

pytestmark = pytest.mark.integration


def test_page_count_is_always_one(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello")

    assert TextFilePageSource().page_count(path) == 1


def test_page_text_returns_the_whole_file(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("line one\nline two")

    assert TextFilePageSource().page_text(path, 1) == "line one\nline two"


def test_invalid_utf8_is_replaced_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "bad-encoding.txt"
    path.write_bytes(b"before \xff\xfe after")

    text = TextFilePageSource().page_text(path, 1)

    assert "before" in text
    assert "after" in text


def test_render_draws_the_text_on_a_portrait_page_at_the_requested_size(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello from a note\nwith two lines")

    png = TextFilePageSource().render(path, 1, long_side_px=512)

    with Image.open(io.BytesIO(png)) as image:
        assert image.format == "PNG"
        assert image.height == 512
        assert image.width < image.height
        darkest, _ = image.convert("L").getextrema()
    assert darkest < 128, "the page carries ink, so the text was drawn rather than a blank sheet returned"


def test_render_never_upscales_past_the_canonical_page(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("short")

    png = TextFilePageSource().render(path, 1, long_side_px=4000)

    with Image.open(io.BytesIO(png)) as image:
        assert image.height == CANONICAL_LONG_SIDE_PX


def test_render_of_an_empty_file_is_a_blank_page_not_an_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_text("")

    png = TextFilePageSource().render(path, 1, long_side_px=256)

    with Image.open(io.BytesIO(png)) as image:
        assert image.height == 256
        assert image.convert("L").getextrema() == (255, 255)


def test_render_is_deterministic_for_the_same_text(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("the same words")
    source = TextFilePageSource()

    assert source.render(path, 1, 300) == source.render(path, 1, 300)


def test_missing_file_raises_unreadable(tmp_path: Path) -> None:
    with pytest.raises(UnreadableFileError):
        TextFilePageSource().page_count(tmp_path / "missing.txt")


def test_zero_byte_file_is_still_one_readable_empty_page(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    source = TextFilePageSource()
    assert source.page_count(path) == 1
    assert source.page_text(path, 1) == ""
