"""What a file actually is, as opposed to what its name claims.

An extension is a claim by whoever named the file. A magic number is what
the bytes say. When they disagree the file is corrupt, and saying so is more
useful than failing later inside a parser with a library traceback.
"""

from __future__ import annotations

from pathlib import Path

from sidecar.domain.entities import FileKind
from sidecar.domain.gate import (
    IMAGE_SUFFIXES,
    PDF_SUFFIXES,
    TEXT_SUFFIXES,
    GateDecision,
    SkipReason,
)

PDF_MAGIC = b"%PDF-"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

# Enough for every signature above, and cheap to read per file.
MAGIC_PREFIX_BYTES = 8


def kind_from_suffix(path: Path) -> FileKind | None:
    """The kind the filename claims. `None` when nothing in scope claims it."""
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        return FileKind.PDF
    if suffix in IMAGE_SUFFIXES:
        return FileKind.IMAGE
    if suffix in TEXT_SUFFIXES:
        return FileKind.TEXT
    return None


def kind_from_magic(head: bytes) -> FileKind | None:
    """The kind the bytes prove. `None` for text, which has no signature."""
    if head.startswith(PDF_MAGIC):
        return FileKind.PDF
    if head.startswith(PNG_MAGIC) or head.startswith(JPEG_MAGIC):
        return FileKind.IMAGE
    return None


def detect_kind(path: Path, head: bytes) -> tuple[FileKind | None, GateDecision]:
    """Reconcile the claim with the evidence.

    Text is the one kind with no signature, so a text extension is trusted on
    its own. Anything else must prove itself: a `.pdf` whose bytes are not a
    PDF is corrupt, not a PDF that will fail to parse later.
    """
    claimed = kind_from_suffix(path)
    if claimed is None:
        return None, GateDecision(SkipReason.UNSUPPORTED_TYPE, {"suffix": path.suffix.lower() or path.name})

    if claimed is FileKind.TEXT:
        return FileKind.TEXT, GateDecision()

    actual = kind_from_magic(head)
    if actual is None:
        return None, GateDecision(SkipReason.CORRUPT, {"claimed": str(claimed), "reason": "no known signature"})
    if actual is not claimed:
        return None, GateDecision(SkipReason.CORRUPT, {"claimed": str(claimed), "actual": str(actual)})

    return actual, GateDecision()
