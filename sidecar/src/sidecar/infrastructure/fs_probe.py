"""Adapter for the `FileProbe` port, backed by BLAKE3 and Pillow."""

from __future__ import annotations

from pathlib import Path

import blake3
from PIL import Image

from sidecar.domain.errors import UnreadableFileError

# Hashing every byte of a multi-gigabyte file on every rescan is the kind of
# cost that only shows up once a real folder is indexed. Below this, a full
# read is cheap enough that sampling would only add complexity.
FULL_HASH_THRESHOLD_BYTES = 50 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024
SAMPLE_BYTES = 65536


class FilesystemProbe:
    """Reads bytes and header facts straight off disk. Never parses a file's format."""

    def head(self, path: Path, count: int) -> bytes:
        with path.open("rb") as f:
            return f.read(count)

    def content_hash(self, path: Path, size_bytes: int) -> str:
        if size_bytes < FULL_HASH_THRESHOLD_BYTES:
            return self._hash_full(path)
        return self._hash_sampled(path, size_bytes)

    def image_size(self, path: Path) -> tuple[int, int]:
        try:
            with Image.open(path) as image:
                # `.size` comes from the header Pillow already parsed on
                # open. Calling `.load()` would decode every pixel for
                # nothing, which is exactly what this method promises not to do.
                return image.size
        except OSError as exc:
            # PIL.UnidentifiedImageError subclasses OSError, so catching the
            # parent covers both a corrupt header and a file that isn't there.
            raise UnreadableFileError(f"Not a decodable image: {path}") from exc

    def _hash_full(self, path: Path) -> str:
        hasher = blake3.blake3()
        # A domain-separation tag keeps this scheme's hashes distinguishable
        # from the sampled scheme's below, so a file that crosses the size
        # threshold between rescans cannot collide with its own former hash.
        hasher.update(b"full\0")
        with path.open("rb") as f:
            while chunk := f.read(READ_CHUNK_BYTES):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _hash_sampled(self, path: Path, size_bytes: int) -> str:
        hasher = blake3.blake3()
        hasher.update(b"sampled\0")
        mtime_ns = path.stat().st_mtime_ns
        hasher.update(f"{size_bytes}:{mtime_ns}".encode())
        with path.open("rb") as f:
            hasher.update(f.read(SAMPLE_BYTES))
            middle = max(size_bytes // 2 - SAMPLE_BYTES // 2, 0)
            f.seek(middle)
            hasher.update(f.read(SAMPLE_BYTES))
            tail = max(size_bytes - SAMPLE_BYTES, 0)
            f.seek(tail)
            hasher.update(f.read(SAMPLE_BYTES))
        return hasher.hexdigest()
