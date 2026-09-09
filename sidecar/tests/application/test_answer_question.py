"""`AnswerQuestion` over fakes. No model, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidecar.application.answer_question import PAGES_PER_ANSWER, AnswerEvent, AnswerQuestion
from sidecar.domain.answers import Usage
from sidecar.domain.entities import FileKind
from sidecar.domain.errors import AnswerUnavailableError, NotFoundError
from sidecar.domain.providers import DEFAULT_MODEL_ID
from sidecar.domain.search import PageHit
from tests.fakes.answerer import FakeAnswerer

CORPUS = Path("/corpus")


class FakeRenderPage:
    """Renders every page except the ones a test says will not render."""

    def __init__(self, unrenderable: set[str] | None = None) -> None:
        self.unrenderable = unrenderable or set()
        self.rendered: list[str] = []

    def run(self, page_id: str, size: object) -> bytes:
        if page_id in self.unrenderable:
            raise NotFoundError(f"No page {page_id}.")
        self.rendered.append(page_id)
        return f"png-{page_id}".encode()


def hit(page_id: str, page_no: int = 1) -> PageHit:
    return PageHit(
        page_id=page_id,
        file_id=page_id.split(":")[0],
        path=CORPUS / f"{page_id.split(':')[0]}.pdf",
        page_no=page_no,
        kind=FileKind.PDF,
        score=1.0,
        stage="visual",
    )


def answer_with(
    answerer: FakeAnswerer, hits: list[PageHit], unrenderable: set[str] | None = None
) -> tuple[list[AnswerEvent], FakeRenderPage]:
    render = FakeRenderPage(unrenderable)
    use_case = AnswerQuestion(render, answerer)  # type: ignore[arg-type]
    return list(use_case.run("what did egress cost", hits, DEFAULT_MODEL_ID)), render


def test_what_the_answer_may_look_at_is_reported_before_any_text() -> None:
    events, _ = answer_with(FakeAnswerer().saying("Egress was 18.4 TB [1]."), [hit("a:1"), hit("b:4", 4)])

    assert events[0].retrieval is not None
    assert [page.index for page in events[0].retrieval] == [1, 2]
    assert [page.page_id for page in events[0].retrieval] == ["a:1", "b:4"]


def test_the_retrieval_event_comes_even_when_no_page_could_be_rendered() -> None:
    """The panel has to be able to say it looked at nothing, rather than showing no state at all."""
    events, _ = answer_with(FakeAnswerer().saying("anything"), [hit("a:1")], unrenderable={"a:1"})

    assert len(events) == 1
    assert events[0].retrieval == ()


def test_text_passes_through_and_citations_come_out_separately() -> None:
    events, _ = answer_with(FakeAnswerer().saying("Egress was 18.4 TB [1] last quarter."), [hit("a:1")])

    text = "".join(event.text for event in events)
    cited = [event.citation for event in events if event.citation is not None]
    assert text == "Egress was 18.4 TB  last quarter."
    assert [(c.index, c.page_id) for c in cited] == [(1, "a:1")]


def test_a_citation_split_across_chunks_arrives_once() -> None:
    """The fake chunks at seven characters, which lands inside the brackets."""
    events, _ = answer_with(FakeAnswerer().saying("aaaaaaaaaaaa[1]bbbb"), [hit("a:1")])

    cited = [event.citation for event in events if event.citation is not None]
    assert len(cited) == 1
    assert "".join(event.text for event in events) == "aaaaaaaaaaaabbbb"


def test_only_the_top_pages_are_sent_and_their_indexes_are_their_positions() -> None:
    answerer = FakeAnswerer().saying("ok")
    hits = [hit(f"p{n}:1") for n in range(PAGES_PER_ANSWER + 3)]

    events, render = answer_with(answerer, hits)

    assert len(render.rendered) == PAGES_PER_ANSWER
    sent = answerer.requests[0].pages
    assert [page.index for page in sent] == list(range(1, PAGES_PER_ANSWER + 1))
    assert [page.page_id for page in sent] == [f"p{n}:1" for n in range(PAGES_PER_ANSWER)]
    assert events[0].retrieval is not None


def test_a_page_that_will_not_render_is_left_out_and_the_rest_stay_numbered_from_one() -> None:
    answerer = FakeAnswerer().saying("ok")

    events, _ = answer_with(answerer, [hit("a:1"), hit("bad:1"), hit("c:1")], unrenderable={"bad:1"})

    sent = answerer.requests[0].pages
    assert [(page.index, page.page_id) for page in sent] == [(1, "a:1"), (2, "c:1")]
    assert events[0].retrieval is not None
    assert [page.index for page in events[0].retrieval] == [1, 2]


def test_the_answer_carries_what_it_used_and_what_that_cost() -> None:
    answerer = FakeAnswerer().saying("ok", usage=Usage(input_tokens=1_000_000, output_tokens=1_000_000))

    events, _ = answer_with(answerer, [hit("a:1")])

    done = events[-1]
    assert done.done == Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert done.cost_usd == 0.0, "the default model is free, so a million tokens of it still costs nothing"


def test_a_model_that_is_not_configured_is_refused_rather_than_priced_at_zero() -> None:
    render = FakeRenderPage()
    use_case = AnswerQuestion(render, FakeAnswerer().saying("ok"))  # type: ignore[arg-type]

    with pytest.raises(AnswerUnavailableError):
        list(use_case.run("q", [hit("a:1")], "something/made-up"))


def test_the_pages_reach_the_model_as_the_images_that_were_rendered() -> None:
    answerer = FakeAnswerer().saying("ok")

    answer_with(answerer, [hit("a:1")])

    assert answerer.requests[0].pages[0].png == b"png-a:1"
    assert answerer.requests[0].question == "what did egress cost"
