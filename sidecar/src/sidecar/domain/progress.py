"""What an indexing job reports while it runs.

Progress is counted in files, which is the unit the user recognizes, and
carries the current filename because "reading invoice-q2.pdf" answers a
different question than "62 percent".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexProgress:
    """A snapshot of one indexing job. Every field is a count of something real."""

    folder_id: str
    files_seen: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    pages_indexed: int = 0
    current_path: str = ""
    done: bool = False
