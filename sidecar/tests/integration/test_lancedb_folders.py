"""The `FolderStore` contract, run against the real table and against the fake.

Both implementations take the same tests. A fake that has drifted from the
adapter turns every unit test written against it into a false pass, and this
file is the only thing that can catch that drift.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sidecar.application.store_ports import FolderStore
from sidecar.domain.errors import NotFoundError
from sidecar.domain.identity import file_id
from sidecar.infrastructure.lancedb_folders import LanceDBFolders
from tests.fakes.clock import FakeClock
from tests.fakes.folder_store import FakeFolderStore

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=2)
DECKS = Path("/corpus/decks")
REPORTS = Path("/corpus/reports")


@pytest.fixture(params=["lancedb", "fake"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> FolderStore:
    if request.param == "fake":
        return FakeFolderStore(FakeClock(NOW))
    return LanceDBFolders(tmp_path / "db", FakeClock(NOW))


def test_a_store_with_nothing_in_it_lists_nothing(store: FolderStore) -> None:
    assert store.list() == []


def test_add_returns_an_enabled_folder_whose_id_comes_from_its_path(store: FolderStore) -> None:
    folder = store.add(REPORTS)

    assert (folder.path, folder.enabled, folder.added_at) == (REPORTS, True, NOW)
    assert folder.id == file_id(REPORTS)
    assert store.list() == [folder]


def test_adding_the_same_path_twice_is_one_folder_and_keeps_the_one_already_there(store: FolderStore) -> None:
    first = store.add(REPORTS)
    store.set_enabled(first.id, False)

    again = store.add(REPORTS)

    assert again.enabled is False
    assert again.added_at == first.added_at
    assert store.list() == [again]


def test_folders_come_back_ordered_by_path(store: FolderStore) -> None:
    store.add(REPORTS)
    store.add(DECKS)

    assert [folder.path for folder in store.list()] == [DECKS, REPORTS]


def test_remove_forgets_one_folder_and_leaves_the_rest(store: FolderStore) -> None:
    reports = store.add(REPORTS)
    store.add(DECKS)

    store.remove(reports.id)

    assert [folder.path for folder in store.list()] == [DECKS]


def test_remove_is_silent_for_an_id_that_is_not_there(store: FolderStore) -> None:
    store.remove("never-added")  # must not raise, with or without a table

    store.add(REPORTS)
    store.remove("never-added")

    assert [folder.path for folder in store.list()] == [REPORTS]


def test_set_enabled_toggles_the_folder_and_is_idempotent(store: FolderStore) -> None:
    folder = store.add(DECKS)

    store.set_enabled(folder.id, False)
    store.set_enabled(folder.id, False)

    assert [(f.path, f.enabled) for f in store.list()] == [(DECKS, False)]

    store.set_enabled(folder.id, True)

    assert store.list()[0].enabled is True


def test_set_enabled_raises_for_an_id_that_is_not_there(store: FolderStore) -> None:
    with pytest.raises(NotFoundError):
        store.set_enabled("never-added", False)


def test_a_folder_outlives_the_connection_that_added_it(tmp_path: Path) -> None:
    db_path = tmp_path / "db"
    added = LanceDBFolders(db_path, FakeClock(NOW)).add(REPORTS)

    reopened = LanceDBFolders(db_path, FakeClock(LATER))

    assert reopened.list() == [added]
    assert reopened.add(REPORTS).added_at == NOW
