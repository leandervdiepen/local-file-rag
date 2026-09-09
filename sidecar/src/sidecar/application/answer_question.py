"""Answering a question from the pages a search found."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from sidecar.application.choose_answerer import ChooseAnswerer
from sidecar.application.render_page import PageImageSize, RenderPage
from sidecar.domain.answers import AnswerRequest, PageImage, Usage
from sidecar.domain.catalogue import OfferedModel, cost_usd
from sidecar.domain.citations import Citation, CitationReader
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.domain.search import PageHit

logger = logging.getLogger(__name__)

# Given a provider and a model, what that provider says it charges, if anything.
PriceLookup = Callable[[str, str], OfferedModel | None]

# Five pages is what fits without the question getting lost among them, and it
# is what the answer is allowed to have looked at. More pages is a longer bill
# and a weaker answer, not a better one.
PAGES_PER_ANSWER = 5

# Measured 2026-09-09 against the free default: asked something its pages
# could not answer, it spent its budget reasoning and streamed no content at
# all. An empty panel reads as a broken app, and the user cannot tell a
# refusal from a failure, so an answer with no answer in it is unavailable.
EMPTY_ANSWER = "The model returned nothing. Ask again, or pick another model in Settings."


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
    # `None` when this model's price was never checked, so the footer says so
    # rather than printing a question that cost money as having cost nothing.
    cost_usd: float | None = 0.0


class AnswerQuestion:
    """Answers from the pages a search found, and says which page each claim came from.

    Invariant: every citation the caller receives points at a page that was
    actually sent to the model. A citation the user can click and find nothing
    behind is worse than no citation, because it is the thing that makes the
    answer look checked.

    Nothing is invented here about what the model said. The text arrives
    exactly as written, markers included, and each citation is additionally
    handed over on its own so the panel can offer it as something to click.
    """

    def __init__(
        self,
        render: RenderPage,
        answerers: ChooseAnswerer,
        price: PriceLookup | None = None,
        pages_per_answer: int = PAGES_PER_ANSWER,
    ) -> None:
        self._render = render
        self._answerers = answerers
        self._price = price
        self._pages_per_answer = pages_per_answer

    def run(self, question: str, hits: list[PageHit], provider_id: str, model_id: str) -> Iterator[AnswerEvent]:
        """Stream the answer, starting with what it is allowed to look at.

        The retrieval event comes first and always, even when no page could be
        rendered, so the panel can show what was consulted before any text
        arrives. Raises `AnswerUnavailableError` when the provider refuses and
        when the model chosen has no key yet.

        Where the answer comes from is resolved per question rather than at
        startup, so changing the model or the key in settings takes effect on
        the next question instead of on the next launch.
        """
        answerer = self._answerers.for_provider(provider_id)
        images, retrieved = self._evidence(hits)
        yield AnswerEvent(retrieval=retrieved)
        if not images:
            return

        reader = CitationReader({page.index: page.page_id for page in images})
        request = AnswerRequest(question=question, pages=tuple(images), model_id=model_id)
        usage = Usage()
        said_anything = False

        for chunk in answerer.stream(request):
            if chunk.usage is not None:
                usage = chunk.usage
            if not chunk.text:
                continue
            said_anything = True
            text, citations = reader.feed(chunk.text)
            if text:
                yield AnswerEvent(text=text)
            for citation in citations:
                yield AnswerEvent(citation=citation)

        tail = reader.flush()
        if tail:
            yield AnswerEvent(text=tail)
        if not said_anything:
            raise AnswerUnavailableError(EMPTY_ANSWER)
        yield AnswerEvent(done=usage, cost_usd=self._cost(provider_id, model_id, usage))

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

    def _cost(self, provider_id: str, model_id: str, usage: Usage) -> float | None:
        """What this exchange cost, or `None` when nobody published a price for it.

        `None` reaches the footer as "price not checked". Guessing here would
        put a number the app made up next to a real bill.
        """
        if self._price is None:
            return None
        model = self._price(provider_id, model_id)
        return None if model is None else cost_usd(model, usage.input_tokens, usage.output_tokens)
