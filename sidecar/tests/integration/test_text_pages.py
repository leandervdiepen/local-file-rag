"""`TextFilePageSource` against real files on disk, including invalid UTF-8."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.domain.errors import UnreadableFileError
from sidecar.infrastructure.text_pages import TextFilePageSource

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


def test_render_raises_because_there_is_nothing_to_render(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello")

    with pytest.raises(UnreadableFileError):
        TextFilePageSource().render(path, 1, long_side_px=512)


def test_missing_file_raises_unreadable(tmp_path: Path) -> None:
    with pytest.raises(UnreadableFileError):
        TextFilePageSource().page_count(tmp_path / "missing.txt")


def test_zero_byte_file_is_still_one_readable_empty_page(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    source = TextFilePageSource()
    assert source.page_count(path) == 1
    assert source.page_text(path, 1) == ""
