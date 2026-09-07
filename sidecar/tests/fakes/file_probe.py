"""A real, in-memory FileProbe. Not a mock."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image

from sidecar.domain.errors import UnreadableFileError


class FakeFileProbe:
    """Backed by a dict of path to file content. Tests seed `files` directly.

    Hashing and image decoding run for real against that in-memory content,
    so a test gets real answers rather than canned ones.
    """

    def __init__(self, files: dict[Path, bytes] | None = None) -> None:
        self.files: dict[Path, bytes] = dict(files or {})

    def head(self, path: Path, count: int) -> bytes:
        return self.files[path][:count]

    def content_hash(self, path: Path, size_bytes: int) -> str:
        return hashlib.sha256(self.files[path]).hexdigest()

    def image_size(self, path: Path) -> tuple[int, int]:
        try:
            with Image.open(io.BytesIO(self.files[path])) as image:
                return image.size
        except OSError as exc:
            raise UnreadableFileError(f"Not a decodable image: {path}") from exc
