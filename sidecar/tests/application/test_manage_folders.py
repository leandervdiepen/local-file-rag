from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.application.manage_folders import ManageFolders
from sidecar.domain.errors import NotFoundError, ValidationError
from tests.fakes.clock import FakeClock
from tests.fakes.folder_store import FakeFolderStore
from tests.fakes.folder_watch import FakeFolderWatch

ADDED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _use_case() -> ManageFolders:
    return ManageFolders(folders=FakeFolderStore(FakeClock(ADDED_AT)))


def test_add_stores_an_enabled_folder_with_the_time_it_was_added(tmp_path: Path) -> None:
    manage = _use_case()

    folder = manage.add(tmp_path)

    assert folder.path == tmp_path
    assert folder.enabled is True
    assert folder.added_at == ADDED_AT
    assert manage.list() == [folder]


def test_adding_the_same_folder_twice_is_one_folder(tmp_path: Path) -> None:
    manage = _use_case()

    first = manage.add(tmp_path)
    second = manage.add(tmp_path)

    assert second == first
    assert manage.list() == [first]


def test_add_rejects_a_relative_path() -> None:
    manage = _use_case()

    with pytest.raises(ValidationError):
        manage.add(Path("Documents/reports"))

    assert manage.list() == []


def test_add_rejects_a_folder_that_is_not_there(tmp_path: Path) -> None:
    manage = _use_case()
    missing = tmp_path / "gone"

    with pytest.raises(ValidationError):
        manage.add(missing)

    assert manage.list() == []


def test_add_rejects_a_file(tmp_path: Path) -> None:
    manage = _use_case()
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.7")

    with pytest.raises(ValidationError):
        manage.add(report)

    assert manage.list() == []


def test_a_rejection_names_the_path_the_user_picked(tmp_path: Path) -> None:
    manage = _use_case()
    missing = tmp_path / "gone"

    with pytest.raises(ValidationError) as rejection:
        manage.add(missing)

    assert str(missing) in rejection.value.message


def test_list_is_ordered_by_path(tmp_path: Path) -> None:
    manage = _use_case()
    second = tmp_path / "b"
    first = tmp_path / "a"
    second.mkdir()
    first.mkdir()

    manage.add(second)
    manage.add(first)

    assert [folder.path for folder in manage.list()] == [first, second]


def test_remove_forgets_the_folder(tmp_path: Path) -> None:
    manage = _use_case()
    folder = manage.add(tmp_path)

    manage.remove(folder.id)

    assert manage.list() == []


def test_remove_is_silent_for_an_id_that_is_not_there() -> None:
    manage = _use_case()

    manage.remove("not-an-id")

    assert manage.list() == []


def test_set_enabled_turns_a_folder_off_and_back_on(tmp_path: Path) -> None:
    manage = _use_case()
    folder = manage.add(tmp_path)

    manage.set_enabled(folder.id, False)
    assert manage.list()[0].enabled is False

    manage.set_enabled(folder.id, True)
    assert manage.list()[0].enabled is True


def test_set_enabled_raises_for_an_id_that_is_not_there() -> None:
    manage = _use_case()

    with pytest.raises(NotFoundError):
        manage.set_enabled("not-an-id", False)


def test_a_folder_that_was_added_is_watched(tmp_path: Path) -> None:
    watch = FakeFolderWatch()
    manage = ManageFolders(folders=FakeFolderStore(FakeClock(ADDED_AT)), watch=watch)

    manage.add(tmp_path)

    assert watch.watching == {tmp_path}


def test_a_folder_that_was_removed_is_not_watched(tmp_path: Path) -> None:
    watch = FakeFolderWatch()
    manage = ManageFolders(folders=FakeFolderStore(FakeClock(ADDED_AT)), watch=watch)
    folder = manage.add(tmp_path)

    manage.remove(folder.id)

    assert watch.watching == set()


def test_turning_a_folder_off_stops_watching_it_and_on_starts_again(tmp_path: Path) -> None:
    """A disabled folder that keeps firing events is the toggle doing nothing."""
    watch = FakeFolderWatch()
    manage = ManageFolders(folders=FakeFolderStore(FakeClock(ADDED_AT)), watch=watch)
    folder = manage.add(tmp_path)

    manage.set_enabled(folder.id, False)
    assert watch.watching == set()

    manage.set_enabled(folder.id, True)
    assert watch.watching == {tmp_path}


def test_watching_resumes_for_folders_that_outlived_the_process(tmp_path: Path) -> None:
    """Folders are stored and the watch is not, so a restart has to point it again."""
    store = FakeFolderStore(FakeClock(ADDED_AT))
    off = tmp_path / "off"
    off.mkdir()
    ManageFolders(folders=store).add(tmp_path)
    disabled = ManageFolders(folders=store).add(off)
    store.set_enabled(disabled.id, False)

    watch = FakeFolderWatch()
    ManageFolders(folders=store, watch=watch).resume_watching()

    assert watch.watching == {tmp_path}
