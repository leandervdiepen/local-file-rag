"""What an indexing job reports while it runs.

Progress is counted in files, which is the unit the user recognizes, and
carries the current filename because "reading invoice-q2.pdf" answers a
different question than "62 percent".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FolderFailure:
    """A folder the crawl could not read, and what to do about it.

    Carried through progress rather than only logged. A crawl that quietly
    indexes nothing is the failure a user cannot diagnose: to them the app is
    simply broken, and the one thing that would fix it is a permission dialog
    they were never shown.
    """

    path: str
    reason: str


@dataclass(frozen=True)
class IndexProgress:
    """A snapshot of one indexing job. Every field is a count of something real."""

    folder_id: str
    files_seen: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    pages_indexed: int = 0
    pages_embedded: int = 0
    current_path: str = ""
    failures: tuple[FolderFailure, ...] = ()
    done: bool = False


@dataclass(frozen=True)
class EmbedProgress:
    """A snapshot of pages being read by the vision model during one search.

    Counted in pages because that is what the partial state shows: "reading
    page 4 of 12" is a promise with a visible end, and a percentage is not.
    """

    pages_read: int
    pages_total: int
    current_page_id: str = ""

    @property
    def done(self) -> bool:
        return self.pages_read >= self.pages_total
