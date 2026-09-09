"""Fetching the model files before anything tries to load them.

`sentence_transformers` downloads whatever is missing as a side effect of
construction, which is convenient and reports nothing anyone can show a user.
Fetching first, through the hub's own API, is what makes a progress bar
possible; the constructor afterwards finds every file already on disk.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from typing import Any, ClassVar

from tqdm.auto import tqdm as base_tqdm

# The Xet download backend stalled at 65 MB of a 4.4 GB file and stayed there,
# so downloads go over plain HTTP (D27). Set here, in the module that actually
# downloads, rather than as a side effect of importing the embedder: anything
# that fetches without going through that import would otherwise stall.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

logger = logging.getLogger(__name__)

Progress = Callable[[int, int], None]


class _Aggregating(base_tqdm):  # type: ignore[misc]
    """A tqdm that adds every live bar together and reports one pair of numbers.

    The hub downloads several files at once, each with its own bar, so a
    single bar's numbers are a fraction of a fraction. Bars register
    themselves here and the totals are summed across whatever is alive.
    """

    # Class level on purpose: the hub opens one of these per file and never
    # hands the caller a handle, so the only place they can find each other
    # is the class.
    #
    # Reentrant, and it has to be. Dropping the last reference to a bar makes
    # CPython run `tqdm.__del__` on the spot, which calls `close`, which
    # reports, which wants this lock on the thread that is already holding it.
    # With a plain Lock the first model download on a fresh machine hangs
    # forever and the app never starts. Measured 2026-09-09.
    _lock: ClassVar[threading.RLock] = threading.RLock()
    _live: ClassVar[list[_Aggregating]] = []
    _sink: ClassVar[Progress | None] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        with _Aggregating._lock:
            _Aggregating._live.append(self)

    def update(self, n: float | None = 1) -> bool | None:
        changed: bool | None = super().update(n)
        self._report()
        return changed

    def close(self) -> None:
        super().close()
        self._report()

    @classmethod
    def _report(cls) -> None:
        with cls._lock:
            sink = cls._sink
            done = sum(int(bar.n or 0) for bar in cls._live)
            total = sum(int(bar.total or 0) for bar in cls._live)
        if sink is not None:
            sink(done, total)

    @classmethod
    def reporting_to(cls, sink: Progress) -> None:
        with cls._lock:
            cls._sink = sink
            cls._live = []

    @classmethod
    def done(cls) -> None:
        with cls._lock:
            cls._sink = None
            # Cleared before the bars are released, so the `close` that
            # releasing them triggers finds no sink and reports nothing.
            cls._live = []


def fetch_model(model_id: str, on_progress: Progress) -> None:
    """Download whatever of `model_id` is missing, reporting bytes as they land.

    Returns as soon as everything is on disk, which for a second run is
    immediately and with no progress reported at all. Any failure is left to
    the caller: this cannot tell a dead connection from a full disk, and the
    caller is the one with a message to give.
    """
    from huggingface_hub import snapshot_download

    _Aggregating.reporting_to(on_progress)
    try:
        snapshot_download(model_id, tqdm_class=_Aggregating)
    finally:
        _Aggregating.done()
