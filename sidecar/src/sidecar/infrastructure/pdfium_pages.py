"""Adapter for the `PageSource` port over `FileKind.PDF`, backed by pypdfium2."""

from __future__ import annotations

import io
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pypdfium2 as pdfium
from pypdfium2.raw import FPDF_ERR_PASSWORD, FPDF_GetLastError

from sidecar.domain.errors import EncryptedFileError, UnreadableFileError


class PdfiumPageSource:
    """Reads a PDF's pages through pdfium.

    pdfium holds native handles per document, page and bitmap, so every
    method closes exactly what it opened before returning.

    Every entry point holds `_LIBRARY`, because pdfium is one global C library
    and it is not thread safe. Two threads rendering pages at once aborted the
    whole sidecar six times on 2026-09-10 and 2026-09-11, every crash inside
    `CFX_FontMapper::AddInstalledFont` while pdfium built its font cache. The
    lock is on the class rather than the instance: the state being protected
    belongs to the library, not to any one adapter.
    """

    _LIBRARY = threading.RLock()

    def page_count(self, path: Path) -> int:
        with self._LIBRARY, self._document(path) as document:
            return len(document)

    def page_text(self, path: Path, page_no: int) -> str:
        with self._LIBRARY, self._document(path) as document, self._page(document, page_no) as page:
            textpage = page.get_textpage()
            try:
                return str(textpage.get_text_range())
            finally:
                textpage.close()

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        with self._LIBRARY, self._document(path) as document, self._page(document, page_no) as page:
            width, height = page.get_size()
            scale = min(long_side_px / max(width, height), 1.0)  # never upscale
            bitmap = page.render(scale=scale)
            try:
                buffer = io.BytesIO()
                bitmap.to_pil().save(buffer, format="PNG")
                return buffer.getvalue()
            finally:
                bitmap.close()

    @contextmanager
    def _document(self, path: Path) -> Iterator[pdfium.PdfDocument]:
        try:
            document = pdfium.PdfDocument(str(path))
        except pdfium.PdfiumError as exc:
            if FPDF_GetLastError() == FPDF_ERR_PASSWORD:
                raise EncryptedFileError(f"PDF needs a password: {path}") from exc
            raise UnreadableFileError(f"Not a readable PDF: {path}") from exc
        except OSError as exc:
            raise UnreadableFileError(f"Not a readable PDF: {path}") from exc
        try:
            yield document
        finally:
            document.close()

    @contextmanager
    def _page(self, document: pdfium.PdfDocument, page_no: int) -> Iterator[pdfium.PdfPage]:
        page = document[page_no - 1]
        try:
            yield page
        finally:
            page.close()
