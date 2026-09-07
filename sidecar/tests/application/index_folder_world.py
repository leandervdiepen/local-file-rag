"""The fakes an `IndexFolder` test runs against, wired together once.

Two test files use it: one for the files that make it into the index, one for
the files the gate refuses. Both need the same five fakes seeded the same way.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from sidecar.application.index_folder import IndexFolder
from sidecar.application.ports import PageSource
from sidecar.domain.entities import FileCandidate, FileKind, IndexedFile, Page
from sidecar.domain.identity import file_id
from sidecar.domain.progress import IndexProgress
from tests.fakes.file_probe import FakeFileProbe
from tests.fakes.folder_crawler import FakeFolderCrawler
from tests.fakes.image_text_reader import FakeImageTextReader
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_source import FakePageSource

ROOT = Path("/corpus")
FOLDER_ID = "folder-1"
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
PDF_BYTES = b"%PDF-1.7 followed by a body"


def png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


class World:
    """The five fakes `IndexFolder` needs, plus the use case wired to them."""

    def __init__(self) -> None:
        self.crawler = FakeFolderCrawler()
        self.probe = FakeFileProbe()
        self.source = FakePageSource()
        self.ocr = FakeImageTextReader()
        self.store = FakeIndexStore()
        sources: dict[FileKind, PageSource] = dict.fromkeys(FileKind, self.source)
        self.use_case = IndexFolder(self.crawler, self.probe, sources, self.ocr, self.store)

    def add(self, name: str, content: bytes, pages: list[str] | None = None, size_bytes: int | None = None) -> Path:
        """Put one file under the root: what the crawler finds, what its bytes are, what its pages say."""
        path = ROOT / name
        size = len(content) if size_bytes is None else size_bytes
        self.crawler.files[path] = FileCandidate(path=path, size_bytes=size, mtime=NOW)
        self.probe.files[path] = content
        if pages is not None:
            self.source.pages[path] = pages
        return path

    def run(self, on_progress: Callable[[IndexProgress], None] | None = None) -> IndexProgress:
        return self.use_case.run(FOLDER_ID, ROOT, on_progress)

    def stored(self, path: Path) -> IndexedFile:
        file = self.store.get_file(file_id(path))
        assert file is not None, f"{path} is missing from the index"
        return file

    def pages_of(self, path: Path) -> list[Page]:
        return self.store.get_pages(file_id(path))


def a_mixed_world() -> World:
    """A crawl of three files that index, one unsupported and one image the gate refuses."""
    world = World()
    world.add("report.pdf", PDF_BYTES, ["a page with text", ""])
    world.add("shot.png", png(400, 300), [""])
    world.add("notes.md", b"# notes", ["# notes"])
    world.add("installer.exe", b"MZ and machine code")
    world.add("icon.png", png(48, 48))
    return world


def snapshot(world: World) -> tuple[object, ...]:
    """Everything the store holds about every file the crawler yields, read through the port."""
    files = [(world.store.get_file(file_id(p)), world.store.get_pages(file_id(p))) for p in sorted(world.crawler.files)]
    return (world.store.stats(), tuple(files))
