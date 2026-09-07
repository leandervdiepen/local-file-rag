"""What a file is, versus what its name claims."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.domain.entities import FileKind
from sidecar.domain.gate import SkipReason
from sidecar.domain.kind_detection import (
    JPEG_MAGIC,
    PDF_MAGIC,
    PNG_MAGIC,
    detect_kind,
    kind_from_magic,
    kind_from_suffix,
)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("a.pdf", FileKind.PDF),
        ("a.PDF", FileKind.PDF),
        ("a.png", FileKind.IMAGE),
        ("a.jpg", FileKind.IMAGE),
        ("a.jpeg", FileKind.IMAGE),
        ("a.txt", FileKind.TEXT),
        ("a.md", FileKind.TEXT),
        ("a.zip", None),
        ("a", None),
    ],
)
def test_kind_from_suffix(name: str, kind: FileKind | None) -> None:
    assert kind_from_suffix(Path(name)) == kind


@pytest.mark.parametrize(
    ("head", "kind"),
    [
        (PDF_MAGIC + b"1.7", FileKind.PDF),
        (PNG_MAGIC, FileKind.IMAGE),
        (JPEG_MAGIC + b"\xe0", FileKind.IMAGE),
        (b"# a markdown file", None),
        (b"", None),
    ],
)
def test_kind_from_magic(head: bytes, kind: FileKind | None) -> None:
    assert kind_from_magic(head) == kind


def test_a_real_pdf_is_accepted() -> None:
    kind, decision = detect_kind(Path("report.pdf"), PDF_MAGIC + b"1.7")
    assert kind is FileKind.PDF
    assert decision.accepted


def test_text_is_trusted_on_its_extension_alone() -> None:
    """Text has no signature, so demanding one would reject every note."""
    kind, decision = detect_kind(Path("notes.md"), b"anything at all")
    assert kind is FileKind.TEXT
    assert decision.accepted


def test_a_pdf_extension_over_non_pdf_bytes_is_corrupt() -> None:
    kind, decision = detect_kind(Path("invoice.pdf"), b"not a pdf at all")
    assert kind is None
    assert decision.reason is SkipReason.CORRUPT


def test_a_png_extension_over_jpeg_bytes_is_still_an_image() -> None:
    """Not corruption. The decoder sniffs content, so this file opens and renders.

    Detection answers what the extractor should do with a file, and the answer
    for both signatures is the same: treat it as an image.
    """
    kind, decision = detect_kind(Path("shot.png"), JPEG_MAGIC + b"\xe0")
    assert kind is FileKind.IMAGE
    assert decision.accepted


def test_an_image_extension_over_bytes_that_are_no_image_is_corrupt() -> None:
    kind, decision = detect_kind(Path("shot.png"), b"just some text")
    assert kind is None
    assert decision.reason is SkipReason.CORRUPT


def test_an_out_of_scope_extension_is_unsupported_not_corrupt() -> None:
    kind, decision = detect_kind(Path("archive.zip"), PDF_MAGIC)
    assert kind is None
    assert decision.reason is SkipReason.UNSUPPORTED_TYPE
