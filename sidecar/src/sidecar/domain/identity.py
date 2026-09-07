"""Stable ids for files and pages.

Ids are derived from the path rather than generated, so a rescan updates the
row it wrote last time instead of inserting a second one. That is what makes
indexing idempotent, and idempotent indexing is what lets a crashed job be
retried without cleanup.

A path is the identity. Moving a file makes a new row, and the old one is
removed when the crawl no longer finds it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_ID_BYTES = 16


def file_id(path: Path) -> str:
    """A stable id for a file at this path."""
    return hashlib.blake2b(str(path).encode("utf-8"), digest_size=_ID_BYTES).hexdigest()


def page_id(owner: str, page_no: int) -> str:
    """A stable id for one page of a file, readable so a log line can be traced by eye."""
    return f"{owner}:{page_no}"
