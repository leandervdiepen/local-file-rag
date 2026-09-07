"""What the index is made of.

Every entity is frozen and validates itself on construction, so an invalid
one cannot exist to be passed around and discovered later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from sidecar.domain.errors import ValidationError
from sidecar.domain.identity import file_id


class FileKind(StrEnum):
    """What the extractor will do with a file. Not the same as its extension."""

    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    # A file the gate refused before anything could establish what it was.
    # Recording it as text would put a guess in a table the index screen
    # presents as fact.
    UNKNOWN = "unknown"


class FileState(StrEnum):
    """How far a file got through the pipeline."""

    SCANNED = "scanned"
    TEXT_INDEXED = "text_indexed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class IndexedFile:
    """One file the crawler has seen, whatever became of it.

    A skipped file is still an `IndexedFile`. The index screen shows it with
    its reason, which is the whole point of being able to inspect the index.
    """

    id: str
    path: Path
    folder_id: str
    content_hash: str
    size_bytes: int
    mtime: datetime
    kind: FileKind
    state: FileState
    skip_reason: str | None = None
    page_count: int = 0
    last_used: datetime | None = None
    truncated_pages: bool = False

    def __post_init__(self) -> None:
        if self.size_bytes < 0:
            raise ValidationError(f"size_bytes cannot be negative, got {self.size_bytes}.")
        if self.page_count < 0:
            raise ValidationError(f"page_count cannot be negative, got {self.page_count}.")
        if (self.state is FileState.SKIPPED) != (self.skip_reason is not None):
            raise ValidationError("A file is skipped exactly when it carries a skip reason.")


@dataclass(frozen=True)
class Page:
    """One page of one file. The unit everything downstream ranks and shows.

    A text file is one page. An image is one page. A PDF is one page per page.
    Keeping that uniform is what lets search, preview, heatmap and chat all
    speak about the same thing.
    """

    id: str
    file_id: str
    page_no: int
    text: str = ""
    embedded_at: datetime | None = None
    last_hit_at: datetime | None = None
    hit_count: int = 0

    def __post_init__(self) -> None:
        if self.page_no < 1:
            raise ValidationError(f"page_no is 1-based, got {self.page_no}.")
        if self.hit_count < 0:
            raise ValidationError(f"hit_count cannot be negative, got {self.hit_count}.")

    @property
    def is_embedded(self) -> bool:
        return self.embedded_at is not None


@dataclass(frozen=True)
class Folder:
    """One folder the user chose to index.

    The id is derived from the path, so adding the same folder twice is one
    row rather than two rows pointing at one tree. `at` builds a new one;
    the constructor is for rebuilding one that was already stored.
    """

    id: str
    path: Path
    enabled: bool
    added_at: datetime

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise ValidationError(f"A folder path is absolute, got {self.path}.")
        if self.id != file_id(self.path):
            raise ValidationError(f"A folder's id is derived from its path, got {self.id}.")

    @classmethod
    def at(cls, path: Path, added_at: datetime, enabled: bool = True) -> Folder:
        """A folder for this path, carrying the id that path always gets."""
        return cls(id=file_id(path), path=path, enabled=enabled, added_at=added_at)


@dataclass(frozen=True)
class FileCandidate:
    """One filesystem entry the crawler found, before anything has been opened.

    Carries only what `os.scandir` already returned, because the crawler
    builds one of these per file across tens of thousands of them.
    """

    path: Path
    size_bytes: int
    mtime: datetime

    @property
    def name(self) -> str:
        return self.path.name
