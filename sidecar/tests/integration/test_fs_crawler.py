"""`FilesystemCrawler` against a real directory tree, including its failure modes."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from sidecar.domain.errors import FolderUnreadableError
from sidecar.infrastructure.fs_crawler import FilesystemCrawler

pytestmark = pytest.mark.integration


def _names(root: Path) -> set[str]:
    return {c.path.name for c in FilesystemCrawler().crawl(root)}


def test_missing_root_yields_nothing(tmp_path: Path) -> None:
    assert list(FilesystemCrawler().crawl(tmp_path / "does-not-exist")) == []


def test_unreadable_root_raises(tmp_path: Path) -> None:
    root = tmp_path / "locked"
    root.mkdir()
    root.chmod(0o000)
    try:
        with pytest.raises(FolderUnreadableError):
            list(FilesystemCrawler().crawl(root))
    finally:
        root.chmod(0o700)  # tmp_path cleanup needs to traverse it again.


def test_yields_files_at_every_depth(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("top level")
    nested = tmp_path / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "b.txt").write_text("deep")

    assert _names(tmp_path) == {"a.txt", "b.txt"}


def test_does_not_descend_into_a_gate_excluded_directory(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("ignored")
    (tmp_path / "keep.txt").write_text("kept")

    assert _names(tmp_path) == {"keep.txt"}


def test_symlink_loop_does_not_hang_the_crawl(tmp_path: Path) -> None:
    (tmp_path / "real.txt").write_text("real")
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)

    assert _names(tmp_path) == {"real.txt"}


def test_symlinked_file_is_not_followed(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("content")
    (tmp_path / "link.txt").symlink_to(target)

    assert _names(tmp_path) == {"target.txt"}


def test_unreadable_subdirectory_is_skipped_not_fatal(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "good.txt").write_text("fine")
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "hidden.txt").write_text("unreachable")
    locked.chmod(0o000)

    try:
        with caplog.at_level("WARNING"):
            names = _names(tmp_path)
    finally:
        locked.chmod(0o700)

    assert names == {"good.txt"}
    assert any("locked" in record.getMessage() for record in caplog.records)


def test_reports_real_size_and_mtime(tmp_path: Path) -> None:
    path = tmp_path / "sized.txt"
    path.write_bytes(b"0123456789")

    [candidate] = list(FilesystemCrawler().crawl(tmp_path))

    assert candidate.size_bytes == 10
    assert candidate.mtime.timestamp() == pytest.approx(path.stat().st_mtime, abs=1)
    assert stat.S_ISREG(candidate.path.stat().st_mode)


def test_a_file_root_is_a_tree_of_one(tmp_path: Path) -> None:
    """`ApplyChanges` re-indexes one changed file by crawling its own path.

    The fake crawler always did this and the real one did not, so every unit
    test passed while the watcher indexed nothing. Measured 2026-09-09.
    """
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.4 body")

    found = list(FilesystemCrawler().crawl(report))

    assert [candidate.path for candidate in found] == [report]
    assert found[0].size_bytes == report.stat().st_size
