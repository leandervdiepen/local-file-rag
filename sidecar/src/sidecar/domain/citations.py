"""Finding `[n]` citations in text that arrives a few characters at a time.

A streamed answer can split `[12]` across three chunks, so this cannot be a
regex over the whole string: the text is rendered as it arrives and a citation
must not be shown half-written and then rewritten.

The marker stays in the text. Lifting it out leaves "the invoice on page
says", measured against a real answer on 2026-09-09, and the chip the citation
becomes is labelled with the same number, so the two read as one thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_CITATION_CHARS = 6


@dataclass(frozen=True)
class Citation:
    """One `[n]` in the answer, resolved to the page it points at."""

    index: int
    page_id: str


@dataclass
class CitationReader:
    """Splits a stream into text that is safe to render and the citations in it.

    Invariant: every character fed in comes out exactly once, in order. The
    text is the answer verbatim, and the citations are reported alongside it
    rather than instead of it, so the panel can append what it is given and
    never repaint.

    A `[` is held back until it either closes or turns out not to be a
    citation, because rendering it and then taking it away is a flicker the
    user reads as a bug.
    """

    page_by_index: dict[int, str]
    _held: str = field(default="", init=False)

    def feed(self, chunk: str) -> tuple[str, list[Citation]]:
        """Text to render now, and any citations that completed in this chunk."""
        text: list[str] = []
        found: list[Citation] = []

        for character in chunk:
            if self._held:
                self._held += character
                if character == "]":
                    citation = self._resolve(self._held)
                    if citation is not None:
                        found.append(citation)
                    text.append(self._held)
                    self._held = ""
                elif not self._could_still_be_a_citation():
                    text.append(self._held)
                    self._held = ""
            elif character == "[":
                self._held = character
            else:
                text.append(character)

        return "".join(text), found

    def flush(self) -> str:
        """Whatever was held when the stream ended, because an unclosed bracket is just text."""
        held, self._held = self._held, ""
        return held

    def _could_still_be_a_citation(self) -> bool:
        return len(self._held) <= MAX_CITATION_CHARS and self._held[1:].isdigit()

    def _resolve(self, held: str) -> Citation | None:
        inside = held[1:-1]
        if not inside.isdigit():
            return None
        page_id = self.page_by_index.get(int(inside))
        return None if page_id is None else Citation(index=int(inside), page_id=page_id)
