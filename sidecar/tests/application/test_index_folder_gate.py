"""Why `IndexFolder` refused a file, and that the refusal is still in the index.

A skipped file the index screen never mentions is the one thing that would
make the screen untrustworthy, so every reason is checked for a row that is
present, carries the reason, and has no pages.
"""

from __future__ import annotations

import pytest

from sidecar.domain.entities import FileKind, FileState
from sidecar.domain.errors import FolderUnreadableError
from sidecar.domain.gate import MAX_FILE_BYTES, SkipReason
from sidecar.domain.search import IndexStats
from tests.application.index_folder_world import PDF_BYTES, ROOT, World, a_mixed_world, png


@pytest.mark.parametrize(
    ("name", "content", "size_bytes", "reason", "kind"),
    [
        ("node_modules/dep.pdf", PDF_BYTES, None, SkipReason.EXCLUDED_PATH, FileKind.PDF),
        ("installer.exe", b"MZ and machine code", None, SkipReason.UNSUPPORTED_TYPE, FileKind.UNKNOWN),
        ("empty.pdf", PDF_BYTES, 0, SkipReason.EMPTY, FileKind.PDF),
        ("huge.pdf", PDF_BYTES, MAX_FILE_BYTES + 1, SkipReason.OVERSIZED, FileKind.PDF),
        ("icon.png", png(48, 48), None, SkipReason.IMAGE_TOO_SMALL, FileKind.IMAGE),
        ("claims.pdf", b"not a pdf at all", None, SkipReason.CORRUPT, FileKind.PDF),
    ],
)
def test_every_gate_refusal_stays_in_the_index_with_its_reason(
    name: str, content: bytes, size_bytes: int | None, reason: SkipReason, kind: FileKind
) -> None:
    world = World()
    path = world.add(name, content, pages=["never read"], size_bytes=size_bytes)

    progress = world.run()

    skipped = world.stored(path)
    assert (skipped.state, skipped.skip_reason, skipped.kind) == (FileState.SKIPPED, reason.value, kind)
    assert (skipped.page_count, world.pages_of(path)) == (0, [])
    assert (progress.files_seen, progress.files_skipped, progress.files_indexed) == (1, 1, 0)


def test_an_encrypted_pdf_and_an_unreadable_one_each_get_their_own_reason() -> None:
    world = World()
    locked = world.add("locked.pdf", PDF_BYTES)
    broken = world.add("broken.pdf", PDF_BYTES)
    world.source.encrypted.add(locked)
    world.source.unreadable.add(broken)

    world.run()

    assert world.stored(locked).skip_reason == SkipReason.ENCRYPTED.value
    assert world.stored(broken).skip_reason == SkipReason.CORRUPT.value
    assert (world.pages_of(locked), world.pages_of(broken)) == ([], [])


def test_a_folder_that_cannot_be_read_raises_and_indexes_nothing() -> None:
    world = a_mixed_world()
    world.crawler.unreadable_roots.add(ROOT)

    with pytest.raises(FolderUnreadableError):
        world.run()

    assert world.store.stats() == IndexStats()
