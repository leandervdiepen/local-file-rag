"""`PdfiumPageSource` against a real PDF, opened through actual pdfium handles."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from sidecar.domain.errors import EncryptedFileError, UnreadableFileError
from sidecar.infrastructure.pdfium_pages import PdfiumPageSource

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent.parent / "fixtures"
SAMPLE_PDF = FIXTURES / "sample_3page.pdf"
ENCRYPTED_PDF = FIXTURES / "encrypted.pdf"


def test_page_count_matches_the_real_pdf() -> None:
    assert PdfiumPageSource().page_count(SAMPLE_PDF) == 3


def test_page_text_reads_each_page_independently() -> None:
    source = PdfiumPageSource()

    first = source.page_text(SAMPLE_PDF, 1)
    second = source.page_text(SAMPLE_PDF, 2)

    assert "Page 1" in first
    assert "Page 2" in second
    assert first != second


def test_render_never_upscales_past_the_page_native_size() -> None:
    source = PdfiumPageSource()

    png_bytes = source.render(SAMPLE_PDF, 1, long_side_px=10_000)

    with Image.open(io.BytesIO(png_bytes)) as image:
        # The fixture's native page is 612 x 792pt; asking for a much larger
        # long side must not blow the render past that native resolution.
        assert max(image.size) <= 792


def test_render_downscales_to_the_requested_long_side() -> None:
    source = PdfiumPageSource()

    png_bytes = source.render(SAMPLE_PDF, 1, long_side_px=100)

    with Image.open(io.BytesIO(png_bytes)) as image:
        assert max(image.size) == 100


def test_encrypted_pdf_raises_encrypted_file_error() -> None:
    with pytest.raises(EncryptedFileError):
        PdfiumPageSource().page_count(ENCRYPTED_PDF)


def test_pdf_extension_on_non_pdf_bytes_raises_unreadable(tmp_path: Path) -> None:
    fake = tmp_path / "not-really.pdf"
    fake.write_bytes(b"%PDF-1.4\nthis is not a real pdf body\n")

    with pytest.raises(UnreadableFileError):
        PdfiumPageSource().page_count(fake)


def test_missing_file_raises_unreadable(tmp_path: Path) -> None:
    with pytest.raises(UnreadableFileError):
        PdfiumPageSource().page_count(tmp_path / "missing.pdf")


def test_documents_and_pages_close_deterministically_across_repeated_calls() -> None:
    """pdfium holds native handles; calling every method many times must not leak them."""
    source = PdfiumPageSource()

    for _ in range(20):
        assert source.page_count(SAMPLE_PDF) == 3
        source.page_text(SAMPLE_PDF, 1)
        source.render(SAMPLE_PDF, 1, long_side_px=50)
