"""Answering a question from the pages a search found."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from sidecar.application.ports import Answerer
from sidecar.application.render_page import PageImageSize, RenderPage
from sidecar.domain.answers import AnswerRequest, PageImage, Usage
from sidecar.domain.citations import Citation, CitationReader
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.domain.providers import cost_usd, find_model
from sidecar.domain.search import PageHit

logger = logging.getLogger(__name__)

# Five pages is what fits without the question getting lost among them, and it
# is what the answer is allowed to have looked at. More pages is a longer bill
# and a weaker answer, not a better one.
PAGES_PER_ANSWER = 5


@dataclass(frozen=True)
class RetrievedPage:
    """One page the answer was allowed to use, as the panel lists it."""

    index: int
    page_id: str
    path: str
    page_no: int


@dataclass(frozen=True)
class AnswerEvent:
    """One thing that happened while answering. Exactly one field is set."""

    retrieval: tuple[RetrievedPage, ...] | None = None
    text: str = ""
    citation: Citation | None = None
    done: Usage | None = None
    cost_usd: float = 0.0


class AnswerQuestion:
    """Answers from the pages a search found, and says which page each claim came from.

    Invariant: every citation the caller receives points at a page that was
    actually sent to the model. A citation the user can click and find nothing
    behind is worse than no citation, because it is the thing that makes the
    answer look checked.

    Nothing is invented here about what the model said: text is passed through
    exactly as it arrives, minus the citation markers, which are handed over
    separately so the panel can render them as chips.
    """

    def __init__(self, render: RenderPage, answerer: Answerer, pages_per_answer: int = PAGES_PER_ANSWER) -> None:
        self._render = render
        self._answerer = answerer
        self._pages_per_answer = pages_per_answer

    def run(self, question: str, hits: list[PageHit], model_id: str) -> Iterator[AnswerEvent]:
        """Stream the answer, starting with what it is allowed to look at.

        The retrieval event comes first and always, even when no page could be
        rendered, so the panel can show what was consulted before any text
        arrives. Raises `AnswerUnavailableError` when the provider refuses.
        """
        images, retrieved = self._evidence(hits)
        yield AnswerEvent(retrieval=retrieved)
        if not images:
            return

        reader = CitationReader({page.index: page.page_id for page in images})
        request = AnswerRequest(question=question, pages=tuple(images), model_id=model_id)
        usage = Usage()

        for chunk in self._answerer.stream(request):
            if chunk.usage is not None:
                usage = chunk.usage
            if not chunk.text:
                continue
            text, citations = reader.feed(chunk.text)
            if text:
                yield AnswerEvent(text=text)
            for citation in citations:
                yield AnswerEvent(citation=citation)

        tail = reader.flush()
        if tail:
            yield AnswerEvent(text=tail)
        yield AnswerEvent(done=usage, cost_usd=self._cost(model_id, usage))

    def _evidence(self, hits: list[PageHit]) -> tuple[list[PageImage], tuple[RetrievedPage, ...]]:
        """Render the top pages. A page that will not render is left out rather than sent empty."""
        images: list[PageImage] = []
        retrieved: list[RetrievedPage] = []
        for hit in hits[: self._pages_per_answer]:
            index = len(images) + 1
            try:
                png = self._render.run(hit.page_id, PageImageSize.FULL)
            except Exception:
                logger.warning("leaving page %s out of the answer: it would not render", hit.page_id)
                continue
            images.append(PageImage(page_id=hit.page_id, index=index, png=png))
            retrieved.append(RetrievedPage(index, hit.page_id, str(hit.path), hit.page_no))
        return images, tuple(retrieved)

    @staticmethod
    def _cost(model_id: str, usage: Usage) -> float:
        model = find_model(model_id)
        if model is None:
            raise AnswerUnavailableError(f"No model called {model_id} is configured.")
        return cost_usd(model, usage.input_tokens, usage.output_tokens)
