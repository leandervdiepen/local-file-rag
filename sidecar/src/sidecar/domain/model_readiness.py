"""How far the retrieval model is from being usable.

First run fetches about four and a half gigabytes before anything can be
searched, and a progress bar is the difference between waiting and thinking
the app is broken. What the states mean lives here; who reports them is the
embedder's business.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelState(StrEnum):
    ABSENT = "absent"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    READY = "ready"


@dataclass(frozen=True)
class ModelProgress:
    """Where the model is now, and how much of the download is done.

    The byte counts are zero unless a download is running, because the only
    thing they are for is the bar drawn during one.
    """

    state: ModelState = ModelState.ABSENT
    bytes_done: int = 0
    bytes_total: int = 0

    @property
    def fraction(self) -> float | None:
        """How far along, or `None` while the total is still unknown.

        `None` rather than zero: a bar sitting at zero percent says the
        download is stuck, and at the start of one the total genuinely is not
        known yet. A caller shows a spinner until this is a number.
        """
        if self.state is not ModelState.DOWNLOADING or self.bytes_total <= 0:
            return None
        return min(1.0, self.bytes_done / self.bytes_total)

    @property
    def usable(self) -> bool:
        return self.state is ModelState.READY
