"""When the app may spend the machine's power on work nobody asked for.

Pre-embedding a page costs about a second of GPU and a few watts. Done while
the user is reading, it makes their search slower; done on battery, it costs
them the afternoon. So it is allowed only when all three conditions hold, and
this file is the whole rule.
"""

from __future__ import annotations

from dataclasses import dataclass

# Long enough that a pause to read a result does not start a background job
# whose first page lands while the user is typing again.
IDLE_AFTER_SECONDS = 60.0

# The plan's number. Two hundred files is a working set: a few weeks of what
# someone actually opens, rather than the whole folder.
RECENT_FILE_LIMIT = 200

# Small enough that stopping between batches is quick, so the first search
# after the user comes back waits for at most one batch rather than a job.
BATCH_PAGES = 8


@dataclass(frozen=True)
class Conditions:
    """What the machine looks like right now, as far as this decision cares."""

    on_ac_power: bool
    idle_seconds: float
    indexing: bool
    storage_full: bool = False


def may_pre_embed(conditions: Conditions, idle_after_seconds: float = IDLE_AFTER_SECONDS) -> bool:
    """True when background embedding is free enough to be worth doing."""
    return refusal(conditions, idle_after_seconds) is None


def refusal(conditions: Conditions, idle_after_seconds: float = IDLE_AFTER_SECONDS) -> str | None:
    """Why pre-embedding is not allowed, or `None` when it is.

    A reason rather than a bare False, because the one question asked about
    this feature is why it is not running, and a log line that says "waiting"
    cannot answer it.
    """
    if not conditions.on_ac_power:
        return "on battery"
    if conditions.indexing:
        return "a crawl is running"
    if conditions.storage_full:
        return "the index is at its storage cap"
    if conditions.idle_seconds < idle_after_seconds:
        return "the app is in use"
    return None
