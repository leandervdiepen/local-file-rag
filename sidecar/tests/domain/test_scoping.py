"""Which folder a path belongs to, and whether it may be searched. Pure rules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sidecar.domain.entities import Folder
from sidecar.domain.scoping import folder_holding, is_searchable

ADDED = datetime(2026, 9, 9, tzinfo=UTC)
DOCUMENTS = Folder.at(Path("/Users/x/Documents"), ADDED)
INVOICES = Folder.at(Path("/Users/x/Documents/invoices"), ADDED)
DOWNLOADS = Folder.at(Path("/Users/x/Downloads"), ADDED, enabled=False)


def test_a_path_belongs_to_the_folder_it_is_under() -> None:
    assert folder_holding(Path("/Users/x/Documents/report.pdf"), [DOCUMENTS, DOWNLOADS]) == DOCUMENTS


def test_the_innermost_folder_wins_when_one_is_inside_another() -> None:
    assert folder_holding(Path("/Users/x/Documents/invoices/q2.pdf"), [DOCUMENTS, INVOICES]) == INVOICES


def test_a_path_under_no_folder_belongs_to_none() -> None:
    assert folder_holding(Path("/tmp/stray.pdf"), [DOCUMENTS]) is None


def test_a_path_in_an_enabled_folder_is_searchable() -> None:
    assert is_searchable(Path("/Users/x/Documents/report.pdf"), [DOCUMENTS, DOWNLOADS])


def test_a_path_in_a_folder_the_user_turned_off_is_not() -> None:
    assert not is_searchable(Path("/Users/x/Downloads/receipt.pdf"), [DOCUMENTS, DOWNLOADS])


def test_turning_off_the_parent_does_not_hide_a_folder_indexed_inside_it() -> None:
    """The user named the inner one separately, and it is still on."""
    off_parent = Folder.at(DOCUMENTS.path, ADDED, enabled=False)

    assert is_searchable(Path("/Users/x/Documents/invoices/q2.pdf"), [off_parent, INVOICES])
    assert not is_searchable(Path("/Users/x/Documents/report.pdf"), [off_parent, INVOICES])


def test_a_file_whose_folder_was_removed_stays_searchable() -> None:
    """Removing a folder leaves its files indexed on purpose, for the user who is moving one."""
    assert is_searchable(Path("/Users/x/Documents/report.pdf"), [])
