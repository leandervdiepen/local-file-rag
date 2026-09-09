"""The /chat wire contract, through the Flask test client."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.answer_question import AnswerQuestion
from sidecar.application.search import Search
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.interface.auth import register_auth
from sidecar.interface.chat_routes import build_chat_blueprint
from sidecar.interface.errors import register_error_handlers
from tests.fakes.answerer import FakeAnswerer
from tests.fakes.cold_pages import FakeColdPages
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.vector_store import FakeVectorStore

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
NOW = datetime(2026, 9, 9, tzinfo=UTC)


class StubRenderPage:
    def run(self, page_id: str, size: object) -> bytes:
        return f"png-{page_id}".encode()


def a_store() -> FakeIndexStore:
    store = FakeIndexStore()
    store.upsert_file(
        IndexedFile(
            id="f1",
            path=Path("/corpus/invoice.pdf"),
            folder_id="d1",
            content_hash="h1",
            size_bytes=64,
            mtime=NOW,
            kind=FileKind.PDF,
            state=FileState.TEXT_INDEXED,
            page_count=2,
        )
    )
    store.upsert_pages(
        [
            Page(id="f1:1", file_id="f1", page_no=1, text="egress 18.4 TB"),
            Page(id="f1:2", file_id="f1", page_no=2, text="support plan"),
        ]
    )
    return store


def a_client(answerer: FakeAnswerer) -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    store = a_store()
    # The pages already have vectors, which is what a real index looks like
    # after a crawl. A natural question shares no whole substring with a page,
    # so it is the visual half of the candidate set that finds them.
    embedder = FakePageEmbedder({"f1:1": ["egress", "cost"], "f1:2": ["support"]})
    vectors = FakeVectorStore()
    vectors.put_vectors(embedder.embed_pages(["f1:1", "f1:2"], [b"png", b"png"]))
    search = Search(store, vectors, embedder, FakeColdPages(embedder, vectors))
    answer = AnswerQuestion(StubRenderPage(), answerer)  # type: ignore[arg-type]
    app.register_blueprint(build_chat_blueprint(search, answer))
    return app.test_client()


def ask(answerer: FakeAnswerer, **body: Any) -> list[tuple[str, dict[str, Any]]]:
    payload = {"question": "what did egress cost", **body}
    response = a_client(answerer).post("/chat", json=payload, headers=AUTH)
    assert response.status_code == 200
    return events_in(response.get_data(as_text=True))


def events_in(stream: str) -> list[tuple[str, dict[str, Any]]]:
    parsed: list[tuple[str, dict[str, Any]]] = []
    for block in stream.split("\n\n"):
        if not block.strip():
            continue
        fields = dict(line.split(": ", 1) for line in block.split("\n"))
        parsed.append((fields["event"], json.loads(fields["data"])))
    return parsed


def names(stream: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [name for name, _ in stream]


def test_the_pages_come_first_then_the_answer_then_exactly_one_done() -> None:
    stream = ask(FakeAnswerer().saying("Egress was 18.4 TB [1]."))

    assert names(stream)[0] == "retrieval"
    assert names(stream)[-1] == "done"
    assert names(stream).count("done") == 1
    assert "token" in names(stream)


def test_the_retrieval_event_names_the_pages_the_answer_may_use() -> None:
    stream = ask(FakeAnswerer().saying("ok"))

    pages = stream[0][1]["pages"]
    assert pages[0]["index"] == 1
    assert pages[0]["path"] == "/corpus/invoice.pdf"
    assert {"index", "page_id", "path", "page_no"} == set(pages[0])


def test_a_citation_arrives_as_its_own_event_pointing_at_a_page_that_was_sent() -> None:
    stream = ask(FakeAnswerer().saying("Egress was 18.4 TB [1]."))

    sent = {page["page_id"] for page in stream[0][1]["pages"]}
    cited = [payload for name, payload in stream if name == "citation"]
    assert cited
    assert all(citation["page_id"] in sent for citation in cited)


def test_the_marker_stays_in_the_sentence_and_the_citation_also_arrives_on_its_own() -> None:
    """Lifting the marker out leaves "the invoice on page  says", so it stays and the chip repeats it."""
    stream = ask(FakeAnswerer().saying("Egress was 18.4 TB [1]."))

    text = "".join(payload["text"] for name, payload in stream if name == "token")
    assert text == "Egress was 18.4 TB [1]."
    assert [payload["index"] for name, payload in stream if name == "citation"] == [1]


def test_done_carries_the_usage_the_cost_and_the_model() -> None:
    stream = ask(FakeAnswerer().saying("ok"))

    done = stream[-1][1]
    assert done["usage"] == {"input_tokens": 9000, "output_tokens": 120}
    assert done["cost_usd"] == 0.0
    assert done["model_id"] == "openrouter/free"


def test_a_provider_that_refuses_ends_the_stream_in_an_error_rather_than_a_done() -> None:
    """Once the stream is open a refusal cannot be a status code, so it is the other terminal event."""
    answerer = FakeAnswerer().saying("ok")
    answerer.refuses = "That key was refused. Check it in Settings."

    stream = ask(answerer)

    assert names(stream)[-1] == "error"
    assert "done" not in names(stream)
    assert stream[-1][1]["message"] == "That key was refused. Check it in Settings."


def test_a_body_with_no_question_is_400_before_the_stream_opens() -> None:
    response = a_client(FakeAnswerer()).post("/chat", json={"question": "  "}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "missing_question"


def test_a_model_this_app_cannot_use_is_400() -> None:
    response = a_client(FakeAnswerer()).post("/chat", json={"question": "q", "model_id": "made/up"}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "unknown_model"


def test_the_stream_is_named_uncached_and_unbuffered() -> None:
    response = a_client(FakeAnswerer().saying("ok")).post("/chat", json={"question": "q"}, headers=AUTH)

    assert response.mimetype == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Accel-Buffering"] == "no"


def test_chat_is_behind_the_token_like_every_other_route() -> None:
    assert a_client(FakeAnswerer()).post("/chat", json={"question": "q"}).status_code == 401
