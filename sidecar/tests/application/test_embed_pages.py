"""`EmbedPages` against in-memory fakes. No adapter, no model, no disk.

The invariant under test: after a run every stored page asked for has
vectors, nothing that already had them was touched, and the progress a
watcher saw counted only the work that happened.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sidecar.application.embed_pages import EMBED_BATCH_PAGES, EMBED_LONG_SIDE_PX, EmbedPages
from sidecar.application.ports import PageSource
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.errors import ValidationError
from sidecar.domain.identity import file_id, page_id
from sidecar.domain.progress import EmbedProgress
from sidecar.domain.vectors import PageVectors
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.page_source import FakePageSource
from tests.fakes.vector_store import FakeVectorStore

ROOT = Path("/corpus")
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
ALL_KINDS = (FileKind.PDF, FileKind.IMAGE, FileKind.TEXT)


class RecordingPageSource(FakePageSource):
    """The same source, keeping every render it was asked for. Still a real source, not a mock."""

    def __init__(self) -> None:
        super().__init__()
        self.rendered: list[tuple[Path, int, int]] = []

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        self.rendered.append((path, page_no, long_side_px))
        return super().render(path, page_no, long_side_px)


class RecordingEmbedder(FakePageEmbedder):
    """The same embedder, keeping the size of every call. Still a real embedder, not a mock."""

    def __init__(self) -> None:
        super().__init__()
        self.call_sizes: list[int] = []

    def embed_pages(self, page_ids: Sequence[str], images_png: Sequence[bytes]) -> list[PageVectors]:
        self.call_sizes.append(len(page_ids))
        return super().embed_pages(page_ids, images_png)


class World:
    """The fakes `EmbedPages` needs, plus the use case wired to them and the progress it reported."""

    def __init__(self, served_kinds: tuple[FileKind, ...] = ALL_KINDS) -> None:
        self.store = FakeIndexStore()
        self.source = RecordingPageSource()
        self.embedder = RecordingEmbedder()
        self.vectors = FakeVectorStore()
        sources: dict[FileKind, PageSource] = dict.fromkeys(served_kinds, self.source)
        self.use_case = EmbedPages(self.store, sources, self.embedder, self.vectors)
        self.seen: list[EmbedProgress] = []

    def add(self, name: str, pages: int, kind: FileKind = FileKind.PDF, decodable: bool = True) -> list[str]:
        """One indexed file of `pages` pages, returning their ids in page order.

        A page that is not decodable renders to empty bytes, which is the
        image the fake embedder refuses the way the real one refuses garbage.
        """
        path = ROOT / name
        owner = file_id(path)
        file = IndexedFile(owner, path, "d1", "hash", 1, NOW, kind, FileState.TEXT_INDEXED, page_count=pages)
        self.store.upsert_file(file)
        self.store.upsert_pages([Page(id=page_id(owner, n), file_id=owner, page_no=n) for n in range(1, pages + 1)])
        for n in range(1, pages + 1):
            self.source.renders[(path, n)] = f"{name}:{n}".encode() if decodable else b""
        return [page_id(owner, n) for n in range(1, pages + 1)]

    def run(self, page_ids: Sequence[str]) -> int:
        return self.use_case.run(page_ids, self.seen.append)

    def counts(self) -> list[tuple[int, int]]:
        return [(progress.pages_read, progress.pages_total) for progress in self.seen]


def test_a_page_that_already_has_vectors_is_neither_rendered_nor_embedded() -> None:
    world = World()
    first, second = world.add("report.pdf", 2)
    world.run([first])
    world.source.rendered.clear()
    world.embedder.embedded_page_ids.clear()

    assert world.run([first, second]) == 1
    assert world.embedder.embedded_page_ids == [second]
    assert world.source.rendered == [(ROOT / "report.pdf", 2, EMBED_LONG_SIDE_PX)]


def test_progress_counts_only_the_work_needed_in_the_order_asked_and_ends_done() -> None:
    world = World()
    ids = world.add("report.pdf", 3)
    world.run(ids[:1])
    world.seen.clear()
    asked = [ids[2], ids[0], ids[1]]

    world.run(asked)

    assert world.counts() == [(1, 2), (2, 2)]
    assert [progress.current_page_id for progress in world.seen] == [ids[2], ids[1]]
    assert world.embedder.embedded_page_ids == [ids[0], ids[2], ids[1]]
    assert world.seen[-1].done


def test_a_page_whose_file_left_the_index_is_skipped_without_raising_and_not_counted() -> None:
    world = World()
    kept = world.add("kept.pdf", 1)
    gone = page_id(file_id(ROOT / "gone.pdf"), 1)

    assert world.run([gone, *kept]) == 1
    assert world.counts() == [(1, 1)]
    assert world.vectors.embedded_ids([gone, *kept]) == set(kept)
    assert world.source.rendered == [(ROOT / "kept.pdf", 1, EMBED_LONG_SIDE_PX)]


def test_a_kind_this_build_cannot_render_is_skipped_rather_than_a_key_error() -> None:
    world = World(served_kinds=(FileKind.PDF,))
    shot = world.add("shot.png", 1, kind=FileKind.IMAGE)
    report = world.add("report.pdf", 1)

    assert world.run([*shot, *report]) == 1
    assert world.vectors.embedded_ids([*shot, *report]) == set(report)


def test_embedding_pages_never_writes_the_index() -> None:
    """A crawl owns the pages table. A search embedding a page must not also write it."""
    world = World()
    ids = world.add("report.pdf", 3)
    before = world.store.get_pages(file_id(ROOT / "report.pdf"))

    world.run(ids[:2])

    assert world.store.get_pages(file_id(ROOT / "report.pdf")) == before
    assert world.vectors.embedded_ids(ids) == set(ids[:2])


def test_batches_send_at_most_the_batch_size_per_embedder_call_and_report_per_page() -> None:
    world = World()
    remainder = 3
    ids = world.add("deck.pdf", 2 * EMBED_BATCH_PAGES + remainder)

    assert world.run(ids) == len(ids)
    assert world.embedder.call_sizes == [EMBED_BATCH_PAGES, EMBED_BATCH_PAGES, remainder]
    assert world.counts() == [(n, len(ids)) for n in range(1, len(ids) + 1)]
    assert world.vectors.count() == len(ids)


def test_a_page_whose_image_will_not_decode_is_skipped_and_the_rest_of_its_batch_lands() -> None:
    world = World()
    good = world.add("report.pdf", 2)
    bad = world.add("blank.pdf", 1, decodable=False)

    assert world.run([good[0], *bad, good[1]]) == 2
    assert world.vectors.embedded_ids([*good, *bad]) == set(good)
    assert world.counts() == [(1, 2), (2, 2)]
    assert world.vectors.embedded_ids(bad) == set()


def test_an_id_asked_for_twice_is_one_page_embedded_once() -> None:
    world = World()
    ids = world.add("report.pdf", 1)

    assert world.run([*ids, *ids]) == 1
    assert world.embedder.embedded_page_ids == ids
    assert world.counts() == [(1, 1)]


def test_nothing_to_do_reports_nothing_and_never_touches_the_embedder() -> None:
    world = World()
    ids = world.add("report.pdf", 2)
    world.run(ids)
    world.seen.clear()

    assert world.run(ids) == 0
    assert world.seen == []
    assert world.embedder.call_sizes == [2]


@pytest.mark.parametrize("malformed", ["", "no-colon", "abc:0", "abc:two"])
def test_a_page_id_the_identity_module_never_produced_is_a_bug_not_a_skip(malformed: str) -> None:
    world = World()

    with pytest.raises(ValidationError):
        world.run([malformed])
    assert world.embedder.call_sizes == []
