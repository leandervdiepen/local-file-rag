"""`FilesystemProbe` against real files, both hashing schemes and the image header path."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from sidecar.domain.errors import UnreadableFileError
from sidecar.infrastructure.fs_probe import FULL_HASH_THRESHOLD_BYTES, FilesystemProbe

pytestmark = pytest.mark.integration


def _write(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_head_returns_at_most_count_bytes(tmp_path: Path) -> None:
    path = _write(tmp_path / "f.txt", b"0123456789")

    assert FilesystemProbe().head(path, 4) == b"0123"


def test_head_on_a_short_file_never_raises(tmp_path: Path) -> None:
    path = _write(tmp_path / "short.txt", b"ab")

    assert FilesystemProbe().head(path, 100) == b"ab"


def test_zero_byte_file_hashes_and_heads_cleanly(tmp_path: Path) -> None:
    path = _write(tmp_path / "empty.txt", b"")

    probe = FilesystemProbe()
    assert probe.head(path, 10) == b""
    assert isinstance(probe.content_hash(path, 0), str)


def test_full_hash_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    probe = FilesystemProbe()
    a = _write(tmp_path / "a.txt", b"same content")
    b = _write(tmp_path / "b.txt", b"same content")
    c = _write(tmp_path / "c.txt", b"different content")

    assert probe.content_hash(a, 12) == probe.content_hash(b, 12)
    assert probe.content_hash(a, 12) != probe.content_hash(c, 18)


def test_sampled_hash_used_above_the_threshold(tmp_path: Path) -> None:
    # One byte over the threshold is enough to exercise the sampled path
    # without writing a real 50 MB fixture to disk.
    size = FULL_HASH_THRESHOLD_BYTES + 1
    path = tmp_path / "huge.bin"
    with path.open("wb") as f:
        f.seek(size - 1)
        f.write(b"\0")

    probe = FilesystemProbe()
    digest = probe.content_hash(path, size)

    assert isinstance(digest, str)
    assert len(digest) > 0


def test_full_and_sampled_hashes_differ_for_the_same_bytes(tmp_path: Path) -> None:
    """The same file, hashed under each scheme, must not produce the same digest.

    Passing a fabricated `size_bytes` forces one real file through both code
    paths, isolating what the scheme tag alone is responsible for: without
    it, a file that grows past 50 MB between rescans could hash the same as
    its own former self.
    """
    size = FULL_HASH_THRESHOLD_BYTES + 1
    path = tmp_path / "boundary.bin"
    with path.open("wb") as f:
        f.seek(size - 1)
        f.write(b"\0")

    probe = FilesystemProbe()
    as_full_scheme = probe.content_hash(path, FULL_HASH_THRESHOLD_BYTES - 1)
    as_sampled_scheme = probe.content_hash(path, size)

    assert as_full_scheme != as_sampled_scheme


def test_image_size_reads_header_without_decoding(tmp_path: Path) -> None:
    path = tmp_path / "pic.png"
    Image.new("RGB", (37, 21)).save(path, format="PNG")

    assert FilesystemProbe().image_size(path) == (37, 21)


def test_image_size_raises_for_bytes_that_are_not_an_image(tmp_path: Path) -> None:
    path = _write(tmp_path / "not-an-image.png", b"just plain bytes, not a PNG")

    with pytest.raises(UnreadableFileError):
        FilesystemProbe().image_size(path)


def test_image_size_matches_a_real_pillow_open(tmp_path: Path) -> None:
    path = tmp_path / "check.png"
    buf = io.BytesIO()
    Image.new("RGBA", (64, 32)).save(buf, format="PNG")
    path.write_bytes(buf.getvalue())

    assert FilesystemProbe().image_size(path) == (64, 32)
