"""When the index has grown past what the user agreed to spend on it.

Vectors are the only part of the index worth evicting. They are about
nine tenths of it on disk, and a page that loses them is still indexed,
still searchable by its words and still able to earn them back the next
time it is a candidate. Nothing here reads a disk or a clock: what the
store costs and what time it is are both told to it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

DEFAULT_CAP_BYTES = 2 * 1024**3

# Evicting exactly to the cap means the next page written is over it again,
# and the store spends the rest of its life one page above the line. Going
# below buys room for the pages a normal session adds.
RECLAIM_TO = 0.9

_NEVER = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class PageHeat:
    """How much use one page has seen. The whole input to which pages go first."""

    page_id: str
    last_hit_at: datetime | None
    hit_count: int


def pages_to_evict(
    pages: Sequence[PageHeat],
    bytes_on_disk: int,
    cap_bytes: int,
    reclaim_to: float = RECLAIM_TO,
) -> list[str]:
    """The pages whose vectors to drop, coldest first, or nothing when the store fits.

    `pages` is every page that currently holds vectors, so the average page
    size is `bytes_on_disk` divided by how many there are. Averaging rather
    than measuring each row: pages are rendered to one patch grid and pooled
    by one factor, so they are within a few percent of each other, and asking
    the store for a per row size would mean reading every vector to decide
    which ones not to keep.

    Returns an empty list for an empty store and for a cap that is already
    met, so a caller can run this on every write without asking first.
    """
    if not pages or bytes_on_disk <= cap_bytes:
        return []
    per_page = bytes_on_disk / len(pages)
    target = cap_bytes * reclaim_to
    wanted = math.ceil((bytes_on_disk - target) / per_page)
    return [page.page_id for page in coldest_first(pages)[:wanted]]


def coldest_first(pages: Sequence[PageHeat]) -> list[PageHeat]:
    """Least recently hit first, so what goes is what the user has not looked at.

    A page nobody has ever opened sorts as if it were hit at the beginning of
    time, which puts every untouched page ahead of every touched one without
    needing a case for it. Ties break on the fewest hits and then on the id,
    so two runs over the same store evict the same pages.
    """
    return sorted(pages, key=lambda page: (page.last_hit_at or _NEVER, page.hit_count, page.page_id))
