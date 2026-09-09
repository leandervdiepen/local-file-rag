"""`LazyModel` against a fake loader. No torch, no model, no sleeping on a duration."""

from __future__ import annotations

import threading

import pytest

from sidecar.infrastructure.lazy_model import LazyModel

NEVER_IDLE = 3600.0


class FakeLoader:
    """Counts loads and unloads, and can be held mid-load on an event the test controls."""

    def __init__(self) -> None:
        self.loads = 0
        self.unloads: list[str] = []
        self.release = threading.Event()
        self.release.set()
        self.entered = threading.Event()
        self.unloaded = threading.Event()

    def load(self) -> str:
        self.entered.set()
        self.release.wait(timeout=5)
        self.loads += 1
        return f"model-{self.loads}"

    def unload(self, held: str) -> None:
        self.unloads.append(held)
        self.unloaded.set()


def test_nothing_is_loaded_until_something_uses_it() -> None:
    loader = FakeLoader()

    holder = LazyModel(loader.load, loader.unload, NEVER_IDLE)

    assert not holder.is_loaded()
    assert loader.loads == 0


def test_the_first_use_loads_and_the_second_reuses() -> None:
    loader = FakeLoader()
    holder = LazyModel(loader.load, loader.unload, NEVER_IDLE)

    assert holder.use(lambda m: m) == "model-1"
    assert holder.use(lambda m: m) == "model-1"
    assert loader.loads == 1
    assert holder.is_loaded()


def test_two_threads_arriving_together_share_one_load() -> None:
    loader = FakeLoader()
    loader.release.clear()
    holder = LazyModel(loader.load, loader.unload, NEVER_IDLE)
    seen: list[str] = []

    threads = [threading.Thread(target=lambda: seen.append(holder.use(lambda m: m))) for _ in range(2)]
    for thread in threads:
        thread.start()
    assert loader.entered.wait(timeout=5), "no thread reached the loader"
    loader.release.set()
    for thread in threads:
        thread.join(timeout=5)

    assert loader.loads == 1, "the model was loaded twice for two callers"
    assert seen == ["model-1", "model-1"]


def test_unload_releases_and_the_next_use_loads_again() -> None:
    loader = FakeLoader()
    holder = LazyModel(loader.load, loader.unload, NEVER_IDLE)
    holder.use(lambda m: m)

    holder.unload()

    assert not holder.is_loaded()
    assert loader.unloads == ["model-1"]
    assert holder.use(lambda m: m) == "model-2"


def test_unloading_when_nothing_is_held_does_nothing() -> None:
    loader = FakeLoader()
    holder = LazyModel(loader.load, loader.unload, NEVER_IDLE)

    holder.unload()
    holder.unload()

    assert loader.unloads == []


def test_it_releases_itself_once_it_has_been_idle() -> None:
    loader = FakeLoader()
    holder = LazyModel(loader.load, loader.unload, idle_seconds=0.01)

    holder.use(lambda m: m)

    assert loader.unloaded.wait(timeout=5), "the idle timer never released the model"
    assert not holder.is_loaded()
    assert loader.unloads == ["model-1"]


def test_a_use_in_progress_is_never_released_underneath_it() -> None:
    loader = FakeLoader()
    holder = LazyModel(loader.load, loader.unload, idle_seconds=0.01)
    inside = threading.Event()
    may_finish = threading.Event()

    def slow(model: str) -> str:
        inside.set()
        may_finish.wait(timeout=5)
        return model

    worker = threading.Thread(target=lambda: holder.use(slow))
    worker.start()
    assert inside.wait(timeout=5)
    # The timer from a previous use would fire around now if it could.
    assert loader.unloads == [], "the model was released while a caller was inside it"
    may_finish.set()
    worker.join(timeout=5)

    assert loader.unloaded.wait(timeout=5)


def test_a_load_that_raises_leaves_the_holder_empty_so_the_next_call_retries() -> None:
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("no weights on disk")
        return "model"

    holder = LazyModel(flaky, lambda _: None, NEVER_IDLE)

    with pytest.raises(RuntimeError):
        holder.use(lambda m: m)
    assert not holder.is_loaded()

    assert holder.use(lambda m: m) == "model"
    assert attempts["n"] == 2
