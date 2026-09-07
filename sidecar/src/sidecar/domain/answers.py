"""What goes to an answer model and what comes back.

The adapter's whole job is wire format. Building the prompt, parsing
citations and pricing the exchange all happen here, so adding a provider
costs one file and changes no behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from sidecar.domain.errors import ValidationError


@dataclass(frozen=True)
class PageImage:
    """One page sent as evidence.

    `index` is the number the model is told to cite, 1-based and stable for
    the length of one exchange, which is what lets `[2]` be mapped back to a
    page id the UI can open.
    """

    page_id: str
    index: int
    png: bytes

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValidationError(f"Citation indexes are 1-based, got {self.index}.")
        if not self.png:
            raise ValidationError("A page image cannot be empty.")


@dataclass(frozen=True)
class AnswerRequest:
    question: str
    pages: tuple[PageImage, ...]
    model_id: str
    max_tokens: int = 4096


@dataclass(frozen=True)
class Usage:
    """What the exchange consumed. Zeros when a provider declines to say."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class AnswerChunk:
    """One piece of a streamed answer.

    Text and usage arrive separately: providers send usage at the end, and
    some send none at all, so a chunk carries whichever it has.
    """

    text: str = ""
    usage: Usage | None = None
