"""A real, in-memory ImageTextReader. Not a mock."""

from __future__ import annotations


class FakeImageTextReader:
    """Backed by a dict of PNG bytes to the text OCR should find in them.

    Bytes not present in `texts` read as having no text, same as a real
    image with nothing on it: the common case, not an error.
    """

    def __init__(self, texts: dict[bytes, str] | None = None) -> None:
        self.texts: dict[bytes, str] = dict(texts or {})

    def read_text(self, image_png: bytes) -> str:
        return self.texts.get(image_png, "")
