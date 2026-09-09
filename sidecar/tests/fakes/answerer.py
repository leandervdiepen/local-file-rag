"""A real, in-memory Answerer. Not a mock.

Scripted with the chunks to yield, and it keeps the request it was given so a
test can assert what was actually sent to a model rather than that a method
was called.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from sidecar.domain.answers import AnswerChunk, AnswerRequest, Usage
from sidecar.domain.errors import AnswerUnavailableError


class FakeAnswerer:
    def __init__(self, chunks: Sequence[AnswerChunk] | None = None) -> None:
        self.chunks: list[AnswerChunk] = list(chunks or [])
        self.requests: list[AnswerRequest] = []
        self.refuses: str | None = None

    def saying(self, text: str, usage: Usage | None = None) -> FakeAnswerer:
        """Answer with this text, split into small pieces the way a real stream arrives."""
        self.chunks = [AnswerChunk(text=piece) for piece in _in_pieces(text)]
        self.chunks.append(AnswerChunk(usage=usage or Usage(input_tokens=9000, output_tokens=120)))
        return self

    def stream(self, request: AnswerRequest) -> Iterator[AnswerChunk]:
        self.requests.append(request)
        if self.refuses is not None:
            raise AnswerUnavailableError(self.refuses)
        yield from self.chunks


def _in_pieces(text: str, size: int = 7) -> list[str]:
    """Chunk boundaries that fall in awkward places, including inside a citation."""
    return [text[at : at + size] for at in range(0, len(text), size)] or [""]
