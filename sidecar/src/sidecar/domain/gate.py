"""What the indexer refuses, and why.

Every refusal is a named reason with the facts that caused it, never a
boolean. The index screen groups and counts by reason, and a person reading
that list is deciding whether to trust the index, so "unsupported" is a
wasted answer and "Image is 48 x 48, below the 300 px minimum" is not.

The interface layer turns a reason plus its facts into that sentence.
This module stays prose free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

MAX_FILE_BYTES = 200 * 1024 * 1024
MIN_IMAGE_SHORT_SIDE_PX = 300
MAX_PDF_PAGES = 300

# Directories that are someone else's business: package managers, version
# control, application bundles, and the caches macOS regenerates anyway.
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "Library",
        "__pycache__",
        ".venv",
        "venv",
        "Caches",
        ".Trash",
        "DerivedData",
        ".next",
        "dist",
        "build",
    }
)

EXCLUDED_DIR_SUFFIXES = (".app", ".framework", ".bundle", ".xcodeproj", ".photoslibrary")

# Formats that are chrome rather than content. An icon has no page to show.
ICON_SUFFIXES = frozenset({".ico", ".icns", ".cur"})

PDF_SUFFIXES = frozenset({".pdf"})
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
TEXT_SUFFIXES = frozenset({".txt", ".md", ".markdown"})
SUPPORTED_SUFFIXES = PDF_SUFFIXES | IMAGE_SUFFIXES | TEXT_SUFFIXES

_EMPTY: Mapping[str, object] = MappingProxyType({})


class SkipReason(StrEnum):
    """Why a file is not in the index.

    These strings are stable. They are stored on every skipped file and the
    renderer switches on them, so renaming one is a migration, not a rename.
    """

    EXCLUDED_PATH = "excluded_path"
    UNSUPPORTED_TYPE = "unsupported_type"
    EMPTY = "empty"
    OVERSIZED = "oversized"
    IMAGE_TOO_SMALL = "image_too_small"
    ENCRYPTED = "encrypted"
    CORRUPT = "corrupt"


@dataclass(frozen=True)
class GateDecision:
    """Accepted, or refused with a reason and the numbers behind it."""

    reason: SkipReason | None = None
    facts: Mapping[str, object] = field(default=_EMPTY)

    @property
    def accepted(self) -> bool:
        return self.reason is None


ACCEPTED = GateDecision()


def _refuse(reason: SkipReason, **facts: object) -> GateDecision:
    return GateDecision(reason=reason, facts=MappingProxyType(dict(facts)))


def is_excluded_dir(name: str) -> bool:
    """True for a directory the crawler must not descend into.

    Hidden directories are excluded wholesale. A user who wants a dotfolder
    indexed can add it as a folder explicitly, which is a decision they made
    rather than forty thousand files they did not.
    """
    if name in EXCLUDED_DIR_NAMES:
        return True
    if name.startswith(".") and name not in {".", ".."}:
        return True
    return name.endswith(EXCLUDED_DIR_SUFFIXES)


def is_excluded_path(path: Path) -> bool:
    """True if any directory on the way to this file is excluded."""
    return any(is_excluded_dir(part) for part in path.parts[:-1])


def screen_path(path: Path, size_bytes: int) -> GateDecision:
    """Decide everything decidable without opening the file.

    Runs once per file on a crawl of tens of thousands, so it touches only
    what `os.scandir` already returned.
    """
    if is_excluded_path(path):
        return _refuse(SkipReason.EXCLUDED_PATH, path=str(path))

    suffix = path.suffix.lower()
    if suffix in ICON_SUFFIXES or suffix not in SUPPORTED_SUFFIXES:
        return _refuse(SkipReason.UNSUPPORTED_TYPE, suffix=suffix or path.name)

    if size_bytes == 0:
        return _refuse(SkipReason.EMPTY)

    if size_bytes > MAX_FILE_BYTES:
        return _refuse(SkipReason.OVERSIZED, size_bytes=size_bytes, limit_bytes=MAX_FILE_BYTES)

    return ACCEPTED


def screen_image(width: int, height: int) -> GateDecision:
    """Refuse images too small to hold anything worth finding.

    The short side decides, so a wide thin banner passes on its height and a
    32 x 512 sprite sheet does not.
    """
    if min(width, height) < MIN_IMAGE_SHORT_SIDE_PX:
        return _refuse(
            SkipReason.IMAGE_TOO_SMALL,
            width=width,
            height=height,
            minimum_px=MIN_IMAGE_SHORT_SIDE_PX,
        )
    return ACCEPTED


def pages_to_index(page_count: int) -> tuple[int, bool]:
    """How many pages of a PDF to index, and whether that truncated it.

    A 900 page PDF is indexed to its first 300 rather than skipped, because a
    partial answer about a long document beats no answer, as long as the app
    says so.
    """
    if page_count > MAX_PDF_PAGES:
        return MAX_PDF_PAGES, True
    return page_count, False
