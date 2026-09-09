"""`ApplyChanges` over the in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from sidecar.application.apply_changes import ApplyChanges
from sidecar.application.index_folder import IndexFolder
from sidecar.domain.changes import ChangeKind, FileChange
from sidecar.domain.entities import FileCandidate, FileKind
from sidecar.domain.identity import file_id, page_id
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors
from tests.fakes.file_probe import FakeFileProbe
from tests.fakes.folder_crawler import FakeFolderCrawler
from tests.fakes.image_text_reader import FakeImageTextReader
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_source import FakePageSource
from tests.fakes.vector_store import FakeVectorStore

ROOT = Path("/corpus")
NOW = datetime(2026, 9, 9, tzinfo=UTC)
FOLDER = "d1"


class World:
    """A real indexing pipeline over fakes, plus the vector store a deletion has to clear."""

    def __init__(self) -> None:
        self.store = FakeIndexStore()
        self.vectors = FakeVectorStore()
        self.pages = FakePageSource()
        self.crawler = FakeFolderCrawler()
        self.probe = FakeFileProbe()
        self.indexer = IndexFolder(
            crawler=self.crawler,
            probe=self.probe,
            sources=dict.fromkeys((FileKind.PDF, FileKind.IMAGE, FileKind.TEXT), self.pages),
            ocr=FakeImageTextReader(),
            store=self.store,
        )
        self.use_case = ApplyChanges(self.indexer, self.store, self.vectors)

    def a_file(self, name: str, pages: list[str]) -> Path:
        path = ROOT / name
        self.pages.pages[path] = pages
        self.probe.files[path] = b"%PDF-1.4 body"
        self.crawler.files[path] = FileCandidate(path=path, size_bytes=1024, mtime=NOW)
        return path

    def index(self, path: Path) -> None:
        self.indexer.run(FOLDER, path)
        owner = file_id(path)
        for page in self.store.get_pages(owner):
            self.vectors.put_vectors([_vectors_for(page.id)])

    def apply(self, *changes: FileChange, sizes: dict[Path, int] | None = None) -> int:
        return self.use_case.run(FOLDER, list(changes), sizes or {c.path: 1024 for c in changes})


def _vectors_for(page: str) -> PageVectors:
    return PageVectors(page_id=page, vectors=np.ones((2, VECTOR_DIM), dtype=STORED_DTYPE), pool_factor=3)


def test_a_deleted_file_leaves_nothing_behind() -> None:
    """The failure a user notices and cannot explain: they deleted it and the app keeps offering it."""
    world = World()
    path = world.a_file("gone.pdf", ["one", "two"])
    world.index(path)
    owner = file_id(path)
    assert world.store.get_file(owner) is not None
    assert world.vectors.count() == 2

    world.apply(FileChange(path, ChangeKind.GONE))

    assert world.store.get_file(owner) is None
    assert world.store.get_pages(owner) == []
    assert world.vectors.count() == 0


def test_an_edited_file_reads_as_its_new_content() -> None:
    world = World()
    path = world.a_file("notes.md", ["the old text"])
    world.index(path)

    world.pages.pages[path] = ["the new text"]
    world.apply(FileChange(path, ChangeKind.TOUCHED))

    [page] = world.store.get_pages(file_id(path))
    assert page.text == "the new text"


def test_a_file_that_lost_pages_loses_their_vectors_too() -> None:
    world = World()
    path = world.a_file("shrunk.pdf", ["one", "two", "three"])
    world.index(path)
    owner = file_id(path)
    assert world.vectors.count() == 3

    world.pages.pages[path] = ["one"]
    world.apply(FileChange(path, ChangeKind.TOUCHED))

    assert [page.page_no for page in world.store.get_pages(owner)] == [1]
    assert world.vectors.embedded_ids([page_id(owner, n) for n in (1, 2, 3)]) == {page_id(owner, 1)}


def test_a_change_the_gate_would_refuse_costs_nothing() -> None:
    world = World()
    path = ROOT / "notes.log"

    assert world.apply(FileChange(path, ChangeKind.TOUCHED)) == 0


def test_three_writes_to_one_file_are_one_re_index() -> None:
    world = World()
    path = world.a_file("saved.md", ["v1"])
    world.index(path)
    world.pages.pages[path] = ["v2"]

    acted = world.apply(*[FileChange(path, ChangeKind.TOUCHED)] * 3)

    assert acted == 1
    assert [page.text for page in world.store.get_pages(file_id(path))] == ["v2"]


def test_a_move_forgets_the_old_path_and_indexes_the_new_one() -> None:
    world = World()
    before = world.a_file("before.pdf", ["content"])
    world.index(before)
    after = world.a_file("after.pdf", ["content"])

    world.apply(FileChange(before, ChangeKind.GONE), FileChange(after, ChangeKind.TOUCHED))

    assert world.store.get_file(file_id(before)) is None
    assert world.store.get_file(file_id(after)) is not None


def test_a_file_that_will_not_re_index_leaves_the_rest_alone() -> None:
    world = World()
    good = world.a_file("good.pdf", ["fine"])
    world.index(good)
    broken = world.a_file("broken.pdf", ["x"])
    world.pages.unreadable.add(broken)

    world.apply(FileChange(broken, ChangeKind.TOUCHED), FileChange(good, ChangeKind.TOUCHED))

    assert world.store.get_file(file_id(good)) is not None
