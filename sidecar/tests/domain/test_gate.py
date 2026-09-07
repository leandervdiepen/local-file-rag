"""Every skip reason, and for each threshold the value that just passes."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.domain.gate import (
    MAX_FILE_BYTES,
    MAX_PDF_PAGES,
    MIN_IMAGE_SHORT_SIDE_PX,
    SkipReason,
    is_excluded_dir,
    is_excluded_path,
    pages_to_index,
    screen_image,
    screen_path,
)

OK_PATH = Path("/Users/x/Desktop/report.pdf")


def test_a_normal_pdf_passes() -> None:
    assert screen_path(OK_PATH, 1024).accepted


@pytest.mark.parametrize(
    "path",
    [
        Path("/Users/x/project/node_modules/pkg/readme.md"),
        Path("/Users/x/project/.git/COMMIT_EDITMSG"),
        Path("/Users/x/Library/Caches/thing.png"),
        Path("/Users/x/Applications/Thing.app/Contents/doc.pdf"),
        Path("/Users/x/.config/notes.md"),
        Path("/Users/x/Photos.photoslibrary/originals/a.jpg"),
    ],
)
def test_excluded_paths_are_refused(path: Path) -> None:
    assert screen_path(path, 1024).reason is SkipReason.EXCLUDED_PATH


def test_a_dotfile_is_not_an_excluded_path() -> None:
    """The rule is about directories on the way, not about the file's own name."""
    assert screen_path(Path("/Users/x/Desktop/.notes.md"), 10).accepted


@pytest.mark.parametrize("suffix", [".zip", ".dylib", ".sqlite", ".bin", ".ico", ".icns", ""])
def test_unsupported_types_are_refused(suffix: str) -> None:
    decision = screen_path(Path(f"/Users/x/Desktop/thing{suffix}"), 4096)
    assert decision.reason is SkipReason.UNSUPPORTED_TYPE


def test_empty_file_is_refused_before_size_limit() -> None:
    decision = screen_path(OK_PATH, 0)
    assert decision.reason is SkipReason.EMPTY


def test_oversized_file_is_refused_with_both_numbers() -> None:
    decision = screen_path(OK_PATH, MAX_FILE_BYTES + 1)
    assert decision.reason is SkipReason.OVERSIZED
    assert decision.facts["size_bytes"] == MAX_FILE_BYTES + 1
    assert decision.facts["limit_bytes"] == MAX_FILE_BYTES


def test_a_file_exactly_at_the_size_limit_passes() -> None:
    assert screen_path(OK_PATH, MAX_FILE_BYTES).accepted


def test_image_below_the_short_side_minimum_is_refused() -> None:
    decision = screen_image(48, 48)
    assert decision.reason is SkipReason.IMAGE_TOO_SMALL
    assert decision.facts == {"width": 48, "height": 48, "minimum_px": MIN_IMAGE_SHORT_SIDE_PX}


def test_the_short_side_decides_not_the_long_one() -> None:
    """A 32 x 4000 sprite sheet is still a sprite sheet."""
    assert screen_image(32, 4000).reason is SkipReason.IMAGE_TOO_SMALL
    assert screen_image(4000, 32).reason is SkipReason.IMAGE_TOO_SMALL


def test_an_image_exactly_at_the_minimum_passes() -> None:
    assert screen_image(MIN_IMAGE_SHORT_SIDE_PX, MIN_IMAGE_SHORT_SIDE_PX).accepted


def test_a_wide_thin_banner_passes_on_its_height() -> None:
    assert screen_image(4000, MIN_IMAGE_SHORT_SIDE_PX).accepted


@pytest.mark.parametrize(
    ("name", "excluded"),
    [
        ("node_modules", True),
        (".git", True),
        ("Thing.app", True),
        (".hidden", True),
        ("Documents", False),
        ("my.app.notes", False),
        ("report", False),
    ],
)
def test_excluded_dir_names(name: str, excluded: bool) -> None:
    assert is_excluded_dir(name) is excluded


def test_excluded_path_ignores_the_filename_itself() -> None:
    assert not is_excluded_path(Path("/Users/x/Desktop/node_modules.md"))
    assert is_excluded_path(Path("/Users/x/node_modules/a.md"))


def test_long_pdfs_are_truncated_rather_than_skipped() -> None:
    assert pages_to_index(900) == (MAX_PDF_PAGES, True)


def test_a_pdf_at_the_page_limit_is_not_truncated() -> None:
    assert pages_to_index(MAX_PDF_PAGES) == (MAX_PDF_PAGES, False)


def test_a_short_pdf_keeps_all_its_pages() -> None:
    assert pages_to_index(7) == (7, False)


def test_facts_cannot_be_mutated_by_a_caller() -> None:
    """A decision travels to the store and the UI, so it must not be editable in transit."""
    decision = screen_path(OK_PATH, MAX_FILE_BYTES + 1)
    with pytest.raises(TypeError):
        decision.facts["size_bytes"] = 0  # type: ignore[index]
