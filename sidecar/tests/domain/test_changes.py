"""What a filesystem event means. Pure rules, no filesystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.domain.changes import ChangeKind, FileChange, collapse, worth_reacting_to

ROOT = Path("/corpus")
SMALL = 1024


def touched(name: str) -> FileChange:
    return FileChange(ROOT / name, ChangeKind.TOUCHED)


def gone(name: str) -> FileChange:
    return FileChange(ROOT / name, ChangeKind.GONE)


def test_a_file_the_gate_accepts_is_worth_re_indexing() -> None:
    assert worth_reacting_to(touched("report.pdf"), SMALL)


@pytest.mark.parametrize("name", ["notes.log", "archive.zip", "photo.heic"])
def test_a_kind_the_gate_refuses_is_not_worth_reacting_to(name: str) -> None:
    """Re-indexing a file that can never be a result costs work and changes nothing."""
    assert not worth_reacting_to(touched(name), SMALL)


def test_a_file_in_a_folder_the_crawler_never_walks_is_ignored() -> None:
    assert not worth_reacting_to(FileChange(ROOT / "node_modules" / "x" / "readme.md", ChangeKind.TOUCHED), SMALL)
    assert not worth_reacting_to(FileChange(ROOT / ".git" / "HEAD", ChangeKind.GONE), SMALL)


def test_an_empty_or_oversized_file_is_not_worth_re_indexing() -> None:
    assert not worth_reacting_to(touched("report.pdf"), 0)
    assert not worth_reacting_to(touched("report.pdf"), 300 * 1024 * 1024)


def test_a_deletion_is_always_worth_reacting_to_even_for_a_file_the_gate_refuses() -> None:
    """The index may hold it as a skipped row, and the index screen must stop listing it."""
    assert worth_reacting_to(gone("notes.log"), 0)
    assert worth_reacting_to(gone("report.pdf"), 0)


def test_a_save_that_arrives_as_three_writes_is_one_re_index() -> None:
    collapsed = collapse([touched("a.pdf"), touched("a.pdf"), touched("a.pdf")])

    assert collapsed == [touched("a.pdf")]


def test_the_last_thing_that_happened_to_a_path_is_what_counts() -> None:
    collapsed = collapse([touched("a.pdf"), gone("a.pdf")])

    assert collapsed == [gone("a.pdf")]


def test_a_file_deleted_and_written_again_ends_as_a_re_index() -> None:
    collapsed = collapse([gone("a.pdf"), touched("a.pdf")])

    assert collapsed == [touched("a.pdf")]


def test_paths_keep_the_order_they_were_first_seen_in() -> None:
    collapsed = collapse([touched("b.pdf"), touched("a.pdf"), touched("b.pdf")])

    assert [change.path.name for change in collapsed] == ["b.pdf", "a.pdf"]


def test_a_move_is_the_old_path_gone_and_the_new_one_touched() -> None:
    collapsed = collapse([gone("old.pdf"), touched("new.pdf")])

    assert collapsed == [gone("old.pdf"), touched("new.pdf")]


def test_nothing_happened_is_nothing_to_do() -> None:
    assert collapse([]) == []
