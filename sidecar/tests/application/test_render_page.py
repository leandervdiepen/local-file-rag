"""`RenderPage` against in-memory fakes. No adapter, no disk, no network."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from sidecar.application.ports import PageSource
from sidecar.application.render_page import FULL_LONG_SIDE_PX, THUMB_LONG_SIDE_PX, PageImageSize, RenderPage
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.errors import NotFoundError, ValidationError
from sidecar.domain.identity import file_id, page_id
from tests.fakes.index_store import FakeIndexStore

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
REPORT = Path("/corpus/report.pdf")
MISSING = Path("/corpus/gone.pdf")
CONTENT_HASH = "hash-of-report"


def a_png(long_side_px: int, page_no: int) -> bytes:
    """A real landscape PNG whose size and color say which page at which long side made it."""
    buffer = io.BytesIO()
    Image.new("RGB", (long_side_px, long_side_px // 2), (page_no * 60 % 256, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class CountingPageSource:
    """A real, in-memory PageSource keeping every render it was asked for. Not a mock.

    Each render is a distinct PNG, so a test asserts on the picture that came
    back rather than on there being bytes at all. The route test imports this
    from here rather than keeping a second copy.
    """

    def __init__(self, pages: dict[Path, int] | None = None) -> None:
        self.pages: dict[Path, int] = dict(pages or {})
        self.renders: list[tuple[Path, int, int]] = []

    def page_count(self, path: Path) -> int:
        return self.pages[path]

    def page_text(self, path: Path, page_no: int) -> str:
        return ""

    def render(self, path: Path, page_no: int, long_side_px: int) -> bytes:
        self.renders.append((path, page_no, long_side_px))
        return a_png(long_side_px, page_no)


def an_indexed_file(path: Path, kind: FileKind) -> IndexedFile:
    return IndexedFile(
        id=file_id(path),
        path=path,
        folder_id="d1",
        content_hash=CONTENT_HASH,
        size_bytes=1024,
        mtime=NOW,
        kind=kind,
        state=FileState.TEXT_INDEXED,
        page_count=3,
    )


def a_render_page(
    file_kind: FileKind = FileKind.PDF,
    served_kinds: tuple[FileKind, ...] = (FileKind.PDF,),
) -> tuple[RenderPage, dict[FileKind, CountingPageSource]]:
    """One indexed file of `file_kind`, plus one source per kind in `served_kinds`."""
    render, sources, _ = a_render_page_over_a_store(file_kind, served_kinds)
    return render, sources


def a_render_page_over_a_store(
    file_kind: FileKind = FileKind.PDF,
    served_kinds: tuple[FileKind, ...] = (FileKind.PDF,),
) -> tuple[RenderPage, dict[FileKind, CountingPageSource], FakeIndexStore]:
    """The same, and the store behind it, for a caller that asserts on what a render recorded."""
    store = FakeIndexStore()
    store.upsert_file(an_indexed_file(REPORT, file_kind))
    store.upsert_pages([Page(id=page_id(file_id(REPORT), n), file_id=file_id(REPORT), page_no=n) for n in (1, 2, 3)])
    sources = {kind: CountingPageSource({REPORT: 3}) for kind in served_kinds}
    ports: dict[FileKind, PageSource] = dict(sources)
    return RenderPage(store=store, sources=ports), sources, store


def page_two() -> str:
    return page_id(file_id(REPORT), 2)


def test_a_thumb_is_the_page_rendered_at_the_thumb_long_side() -> None:
    render, sources = a_render_page()

    png = render.run(page_two(), PageImageSize.THUMB)

    assert sources[FileKind.PDF].renders == [(REPORT, 2, THUMB_LONG_SIDE_PX)]
    assert png == a_png(THUMB_LONG_SIDE_PX, 2)
    assert Image.open(io.BytesIO(png)).width == THUMB_LONG_SIDE_PX


def test_full_is_the_same_page_at_the_full_long_side_and_different_bytes() -> None:
    render, sources = a_render_page()

    thumb = render.run(page_two(), PageImageSize.THUMB)
    full = render.run(page_two(), PageImageSize.FULL)

    assert sources[FileKind.PDF].renders == [(REPORT, 2, THUMB_LONG_SIDE_PX), (REPORT, 2, FULL_LONG_SIDE_PX)]
    assert Image.open(io.BytesIO(full)).width == FULL_LONG_SIDE_PX
    assert full != thumb


def test_the_source_that_renders_is_the_one_for_the_file_kind() -> None:
    render, sources = a_render_page(file_kind=FileKind.IMAGE, served_kinds=(FileKind.PDF, FileKind.IMAGE))

    render.run(page_id(file_id(REPORT), 1), PageImageSize.THUMB)

    assert sources[FileKind.IMAGE].renders == [(REPORT, 1, THUMB_LONG_SIDE_PX)]
    assert sources[FileKind.PDF].renders == []


@pytest.mark.parametrize("malformed", ["", "no-colon", "abc:", ":2", "abc:0", "abc:two", "abc:-1"])
def test_a_page_id_the_identity_module_never_produced_is_rejected(malformed: str) -> None:
    render, sources = a_render_page()

    with pytest.raises(ValidationError):
        render.run(malformed, PageImageSize.THUMB)
    assert sources[FileKind.PDF].renders == []


def test_a_page_of_a_file_that_is_not_indexed_is_not_found() -> None:
    render, sources = a_render_page()

    with pytest.raises(NotFoundError):
        render.run(page_id(file_id(MISSING), 1), PageImageSize.THUMB)
    assert sources[FileKind.PDF].renders == []


def test_a_kind_this_build_cannot_render_is_not_found_rather_than_a_key_error() -> None:
    render, _ = a_render_page(file_kind=FileKind.UNKNOWN, served_kinds=(FileKind.PDF,))

    with pytest.raises(NotFoundError):
        render.run(page_two(), PageImageSize.THUMB)


def test_the_content_hash_is_the_owning_file_s_and_renders_nothing() -> None:
    render, sources = a_render_page()

    assert render.content_hash_for(page_two()) == CONTENT_HASH
    assert sources[FileKind.PDF].renders == []


def test_the_content_hash_of_a_page_that_is_not_indexed_is_not_found() -> None:
    render, _ = a_render_page()

    with pytest.raises(NotFoundError):
        render.content_hash_for(page_id(file_id(MISSING), 1))


def test_the_content_hash_of_a_malformed_page_id_is_rejected() -> None:
    render, _ = a_render_page()

    with pytest.raises(ValidationError):
        render.content_hash_for("not-a-page-id")
