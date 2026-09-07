"""Rendering an indexed page as a picture.

Search results are shown as thumbnails, so this is what makes a result list
look like the user's files rather than a list of paths.
"""

from __future__ import annotations

from enum import StrEnum

from sidecar.application.ports import PageSource
from sidecar.application.store_ports import IndexStore
from sidecar.domain.entities import FileKind, IndexedFile
from sidecar.domain.errors import NotFoundError
from sidecar.domain.identity import split_page_id

THUMB_LONG_SIDE_PX = 320
FULL_LONG_SIDE_PX = 1600


class PageImageSize(StrEnum):
    """What the picture is wanted for: a cell in the result grid, or the preview."""

    THUMB = "thumb"
    FULL = "full"


_LONG_SIDE_PX: dict[PageImageSize, int] = {
    PageImageSize.THUMB: THUMB_LONG_SIDE_PX,
    PageImageSize.FULL: FULL_LONG_SIDE_PX,
}


class RenderPage:
    """Renders one page of one indexed file as PNG bytes.

    Invariant: what comes back is that page at the size asked for, or nothing
    comes back at all. There is no placeholder image, because a grey box
    sitting in a result grid looks like a page that rendered badly and
    teaches the user to distrust the thumbnails next to it.
    """

    def __init__(self, store: IndexStore, sources: dict[FileKind, PageSource]) -> None:
        self._store = store
        self._sources = sources

    def run(self, page_id: str, size: PageImageSize) -> bytes:
        """The page as PNG bytes, scaled to the long side that `size` names.

        Raises `ValidationError` when `page_id` is not a page id, because it
        arrives from a URL and nothing upstream has vouched for it.
        Raises `NotFoundError` when the file is not indexed, and when its
        kind has no source: the store can hold a row this build cannot
        render, and to a caller waiting for an image both are the same answer.
        """
        file, page_no = self._locate(page_id)
        source = self._sources.get(file.kind)
        if source is None:
            raise NotFoundError("There is no page image for this file. Open the file to see it.")
        return source.render(file.path, page_no, _LONG_SIDE_PX[size])

    def content_hash_for(self, page_id: str) -> str:
        """The owning file's content hash, which the ETag is built from.

        Raises what `run` raises for a page id that is malformed or not
        indexed. Renders nothing and opens no file, which is what lets a
        conditional request be answered for the price of one store lookup.
        """
        file, _ = self._locate(page_id)
        return file.content_hash

    def _locate(self, page_id: str) -> tuple[IndexedFile, int]:
        owner, page_no = split_page_id(page_id)
        file = self._store.get_file(owner)
        if file is None:
            raise NotFoundError("That page is not in the index. Rescan the folder it lives in.")
        return file, page_no
