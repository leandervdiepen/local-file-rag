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

from sidecar.domain.errors import ValidationError

_ID_BYTES = 16


def file_id(path: Path) -> str:
    """A stable id for a file at this path."""
    return hashlib.blake2b(str(path).encode("utf-8"), digest_size=_ID_BYTES).hexdigest()


def page_id(owner: str, page_no: int) -> str:
    """A stable id for one page of a file, readable so a log line can be traced by eye."""
    return f"{owner}:{page_no}"


def split_page_id(page_id_value: str) -> tuple[str, int]:
    """The file id and page number inside a page id.

    Splits from the right, because a file id is fixed width hex and a page
    number has no colon in it, while nothing stops a future owner prefix from
    carrying one.

    Raises `ValidationError` for anything this module did not produce. A page
    id arrives from the URL of an image request, so it is untrusted input
    rather than a value the caller can be assumed to have built correctly.
    """
    owner, separator, page_part = page_id_value.rpartition(":")
    if not separator or not owner or not page_part.isdigit() or int(page_part) < 1:
        raise ValidationError(f"{page_id_value!r} is not a page id.")
    return owner, int(page_part)
