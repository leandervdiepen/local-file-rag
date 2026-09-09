"""`PreEmbedRecent` over the in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sidecar.application.embed_pages import EmbedPages
from sidecar.application.pre_embed_recent import PreEmbedRecent
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.identity import file_id, page_id
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.page_source import FakePageSource
from tests.fakes.power_source import FakePowerSource
from tests.fakes.vector_store import FakeVectorStore

NOW = datetime(2026, 9, 9, tzinfo=UTC)
IDLE_AFTER = 60.0


class Clockwork:
    """An idleness the test sets directly, in place of a real monotonic clock."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def idle_seconds(self) -> float:
        return self.seconds


class Crawling:
    def __init__(self, running: bool = False) -> None:
        self.running = running

    def is_running(self) -> bool:
        return self.running


class World:
    def __init__(self, batch_pages: int = 8, file_limit: int = 200, cap_bytes: int = 1024**3) -> None:
        self.store = FakeIndexStore()
        self.vectors = FakeVectorStore()
        self.pages = FakePageSource()
        self.embedder = FakePageEmbedder()
        self.power = FakePowerSource(on_ac=True)
        self.activity = Clockwork(seconds=IDLE_AFTER * 2)
        self.jobs = Crawling()
        self.use_case = PreEmbedRecent(
            store=self.store,
            vectors=self.vectors,
            embed_pages=EmbedPages(
                self.store,
                dict.fromkeys((FileKind.PDF, FileKind.IMAGE, FileKind.TEXT), self.pages),
                self.embedder,
                self.vectors,
            ),
            power=self.power,
            activity=self.activity,
            jobs=self.jobs,
            cap_bytes=cap_bytes,
            file_limit=file_limit,
            batch_pages=batch_pages,
            idle_after_seconds=IDLE_AFTER,
        )

    def a_file(self, name: str, page_count: int, last_used: datetime | None = None) -> str:
        """One indexed file whose pages carry the ids the rest of the app would give them."""
        path = Path("/corpus") / f"{name}.pdf"
        owner = file_id(path)
        self.pages.pages[path] = [f"page {n}" for n in range(1, page_count + 1)]
        for n in range(1, page_count + 1):
            self.pages.renders[(path, n)] = f"png-{name}-{n}".encode()
        self.store.upsert_file(
            IndexedFile(
                id=owner,
                path=path,
                folder_id="d1",
                content_hash=f"hash-{name}",
                size_bytes=1024,
                mtime=NOW,
                kind=FileKind.PDF,
                state=FileState.TEXT_INDEXED,
                page_count=page_count,
                last_used=last_used,
            )
        )
        self.store.upsert_pages(
            [Page(id=page_id(owner, n), file_id=owner, page_no=n) for n in range(1, page_count + 1)]
        )
        return owner


def test_a_quiet_plugged_in_machine_embeds_a_batch() -> None:
    world = World(batch_pages=2)
    world.a_file("f1", page_count=5)

    assert world.use_case.tick() == 2
    assert world.vectors.count() == 2


def test_a_machine_on_battery_embeds_nothing() -> None:
    world = World()
    world.a_file("f1", page_count=5)
    world.power.on_ac = False

    assert world.use_case.tick() == 0
    assert world.vectors.count() == 0


def test_a_machine_in_use_embeds_nothing() -> None:
    world = World()
    world.a_file("f1", page_count=5)
    world.activity.seconds = 2.0

    assert world.use_case.tick() == 0


def test_a_machine_that_is_crawling_embeds_nothing() -> None:
    """Two jobs writing the index at once is the one thing the store cannot take."""
    world = World()
    world.a_file("f1", page_count=5)
    world.jobs.running = True

    assert world.use_case.tick() == 0


def test_the_most_recently_used_file_is_embedded_first() -> None:
    world = World(batch_pages=1)
    cold = page_id(world.a_file("cold", page_count=1), 1)
    warm = page_id(world.a_file("warm", page_count=1, last_used=NOW), 1)

    world.use_case.tick()

    assert world.vectors.embedded_ids([cold, warm]) == {warm}


def test_a_page_that_already_has_vectors_is_not_read_again() -> None:
    world = World(batch_pages=8)
    world.a_file("f1", page_count=3)
    world.use_case.tick()
    read_once = list(world.embedder.embedded_page_ids)

    assert world.use_case.tick() == 0
    assert world.embedder.embedded_page_ids == read_once


def test_ticking_a_fully_embedded_index_costs_nothing() -> None:
    world = World()

    assert world.use_case.tick() == 0


def test_only_the_working_set_is_pre_embedded() -> None:
    """Two hundred files is a working set. The rest wait for a search to want them."""
    world = World(batch_pages=8, file_limit=1)
    inside = page_id(world.a_file("inside", page_count=1, last_used=NOW), 1)
    outside = page_id(world.a_file("outside", page_count=1), 1)

    world.use_case.tick()

    assert world.vectors.embedded_ids([inside, outside]) == {inside}


def test_a_batch_that_fails_leaves_the_loop_alive() -> None:
    """This runs on a timer with nobody waiting on it, so a failure has nothing to reach."""
    world = World(batch_pages=2)
    world.a_file("f1", page_count=2)
    world.pages.renders.clear()

    assert world.use_case.tick() == 0


def test_nothing_is_pre_embedded_into_a_store_that_is_already_full() -> None:
    """The cap would evict whatever this adds, and the two jobs would run all night."""
    world = World(batch_pages=2, cap_bytes=0)
    world.a_file("f1", page_count=5)

    assert world.use_case.tick() == 0
    assert world.vectors.count() == 0
