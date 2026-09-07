"""What a search returns, and what the index screen reports about itself."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sidecar.domain.entities import FileKind
from sidecar.domain.errors import ValidationError


@dataclass(frozen=True)
class PageHit:
    """One page that matched, with the score that put it there.

    `stage` says which signal found it, so the UI can be honest about a
    result that came from a filename match rather than from the page itself.
    """

    page_id: str
    file_id: str
    path: Path
    page_no: int
    kind: FileKind
    score: float
    stage: str
    snippet: str = ""

    def __post_init__(self) -> None:
        if self.page_no < 1:
            raise ValidationError(f"page_no is 1-based, got {self.page_no}.")


@dataclass(frozen=True)
class IndexStats:
    """The numbers the index screen shows. Every one is a count of something real."""

    files_scanned: int = 0
    files_text_indexed: int = 0
    files_skipped: int = 0
    pages_total: int = 0
    pages_embedded: int = 0
    bytes_on_disk: int = 0
    skips_by_reason: tuple[tuple[str, int], ...] = ()
