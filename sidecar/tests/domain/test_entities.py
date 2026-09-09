"""Entities refuse to exist in an invalid state."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.errors import ValidationError

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def a_file(**overrides: object) -> IndexedFile:
    defaults: dict[str, object] = {
        "id": "f1",
        "path": Path("/Users/x/Desktop/a.pdf"),
        "folder_id": "d1",
        "content_hash": "abc",
        "size_bytes": 100,
        "mtime": NOW,
        "kind": FileKind.PDF,
        "state": FileState.TEXT_INDEXED,
    }
    return IndexedFile(**{**defaults, **overrides})  # type: ignore[arg-type]


def test_a_valid_file_constructs() -> None:
    assert a_file().state is FileState.TEXT_INDEXED


def test_negative_size_is_refused() -> None:
    with pytest.raises(ValidationError):
        a_file(size_bytes=-1)


def test_negative_page_count_is_refused() -> None:
    with pytest.raises(ValidationError):
        a_file(page_count=-1)


def test_a_skipped_file_must_carry_a_reason() -> None:
    with pytest.raises(ValidationError):
        a_file(state=FileState.SKIPPED)


def test_an_unskipped_file_must_not_carry_a_reason() -> None:
    with pytest.raises(ValidationError):
        a_file(state=FileState.TEXT_INDEXED, skip_reason="empty")


def test_a_skipped_file_with_its_reason_is_valid() -> None:
    """Skipped files stay in the index. The index screen exists to show them."""
    f = a_file(state=FileState.SKIPPED, skip_reason="empty")
    assert f.skip_reason == "empty"


def test_pages_are_one_based() -> None:
    with pytest.raises(ValidationError):
        Page(id="p1", file_id="f1", page_no=0)


def test_negative_hit_count_is_refused() -> None:
    with pytest.raises(ValidationError):
        Page(id="p1", file_id="f1", page_no=1, hit_count=-1)


def test_a_fresh_page_has_seen_no_use() -> None:
    """The storage cap evicts by these two, so an unset pair has to mean untouched."""
    page = Page(id="p1", file_id="f1", page_no=1)

    assert page.last_hit_at is None
    assert page.hit_count == 0
