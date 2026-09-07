"""The /search wire contract, through the Flask test client over a real in-memory store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.search import STAGE_ONE_CANDIDATE_LIMIT, Search
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.search import PageHit
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.search_routes import build_search_blueprint
from tests.fakes.cold_pages import FakeColdPages
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.page_embedder import FakePageEmbedder
from tests.fakes.vector_store import FakeVectorStore

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class RecordingStore(FakeIndexStore):
    """The same store, keeping the limits it was asked for. Still a real store, not a mock."""

    def __init__(self) -> None:
        super().__init__()
        self.limits: list[int] = []

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        self.limits.append(limit)
        return super().search_pages(query, limit)


def a_store_holding(texts: list[str]) -> RecordingStore:
    """One indexed file whose pages carry `texts`, page 1 first."""
    store = RecordingStore()
    store.upsert_file(
        IndexedFile(
            id="f1",
            path=Path("/corpus/notes.md"),
            folder_id="d1",
            content_hash="hash1",
            size_bytes=64,
            mtime=NOW,
            kind=FileKind.TEXT,
            state=FileState.TEXT_INDEXED,
            page_count=len(texts),
        )
    )
    store.upsert_pages([Page(id=f"f1:{n}", file_id="f1", page_no=n, text=t) for n, t in enumerate(texts, start=1)])
    return store


def a_search_over(store: FakeIndexStore, looks: dict[str, list[str]] | None = None) -> Search:
    embedder = FakePageEmbedder(looks)
    vectors = FakeVectorStore()
    return Search(store, vectors, embedder, FakeColdPages(embedder, vectors))


def a_client_over(store: FakeIndexStore, looks: dict[str, list[str]] | None = None) -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    app.register_blueprint(build_search_blueprint(a_search_over(store, looks)))
    return app.test_client()


def events_in(body: str) -> list[tuple[str, dict[str, Any]]]:
    """Every named event in an SSE body, in order, as (name, payload).

    Parsed rather than string matched, so these tests pin the contract instead
    of the encoder's newline placement.
    """
    parsed: list[tuple[str, dict[str, Any]]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        fields: dict[str, str] = {}
        for line in block.split("\n"):
            name, _, value = line.partition(": ")
            fields[name] = value
        parsed.append((fields["event"], json.loads(fields["data"])))
    return parsed


def search(client: FlaskClient, **params: str) -> list[tuple[str, dict[str, Any]]]:
    response = client.get("/search", query_string=params, headers=AUTH)
    assert response.status_code == 200
    return events_in(response.get_data(as_text=True))


def names_in(stream: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [name for name, _ in stream]


def payload_of(stream: list[tuple[str, dict[str, Any]]], event: str) -> dict[str, Any]:
    return next(payload for name, payload in stream if name == event)


def test_candidates_arrive_first_and_carry_the_whole_hit() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast for hosting"]))

    stream = search(client, q="forecast")

    assert names_in(stream)[0] == "candidates"
    assert payload_of(stream, "candidates")["hits"] == [
        {
            "page_id": "f1:1",
            "file_id": "f1",
            "path": "/corpus/notes.md",
            "page_no": 1,
            "kind": "text",
            "score": 1.0,
            "stage": "content",
            "snippet": "quarterly forecast for hosting",
        }
    ]


def test_the_stream_reaches_results_and_exactly_one_done() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast", "hosting spend"]))

    stream = search(client, q="forecast")

    assert names_in(stream)[0] == "candidates"
    assert names_in(stream)[-2:] == ["results", "done"]
    assert names_in(stream).count("done") == 1
    assert payload_of(stream, "done") == {"count": 1, "stage2": "ok"}


def test_reading_a_cold_page_is_reported_as_progress_before_the_results() -> None:
    client = a_client_over(a_store_holding(["forecast", "forecast", "forecast"]))

    stream = search(client, q="forecast")

    progress = [payload for name, payload in stream if name == "progress"]
    assert [p["pages_read"] for p in progress] == [1, 2, 3]
    assert {p["pages_total"] for p in progress} == {3}
    assert names_in(stream).index("progress") < names_in(stream).index("results")


def test_results_are_reranked_by_what_the_page_looks_like() -> None:
    # Page 1 says the word more often, so stage 1 puts it first. Page 2 is the
    # one that actually shows a chart, which only the second stage can know.
    store = a_store_holding(["chart chart chart", "chart"])
    looks = {"f1:1": ["table"], "f1:2": ["chart"]}
    client = a_client_over(store, looks)

    stream = search(client, q="chart")

    assert [hit["page_id"] for hit in payload_of(stream, "candidates")["hits"]] == ["f1:1", "f1:2"]
    assert [hit["page_id"] for hit in payload_of(stream, "results")["hits"]] == ["f1:2", "f1:1"]
    assert payload_of(stream, "results")["hits"][0]["stage"] == "visual"


def test_a_stage_two_that_fails_still_ends_the_stream_and_keeps_the_candidates() -> None:
    class BrokenSearch(Search):
        def stage_two(self, *args: Any, **kwargs: Any) -> list[PageHit]:
            raise RuntimeError("the model fell over")

    store = a_store_holding(["forecast"])
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    embedder = FakePageEmbedder()
    vectors = FakeVectorStore()
    broken = BrokenSearch(store, vectors, embedder, FakeColdPages(embedder, vectors))
    app.register_blueprint(build_search_blueprint(broken))

    stream = search(app.test_client(), q="forecast")

    assert names_in(stream) == ["candidates", "done"]
    assert payload_of(stream, "done") == {"count": 1, "stage2": "failed"}
    assert len(payload_of(stream, "candidates")["hits"]) == 1


def test_took_ms_is_a_whole_number_of_milliseconds() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast"]))

    took_ms = payload_of(search(client, q="forecast"), "candidates")["took_ms"]

    assert isinstance(took_ms, int)
    assert took_ms >= 0


@pytest.mark.parametrize("query", ["", "   ", "\t\n"])
def test_nothing_typed_streams_no_hits_rather_than_the_whole_index(query: str) -> None:
    client = a_client_over(a_store_holding(["quarterly forecast"]))

    stream = search(client, q=query)

    assert names_in(stream) == ["candidates", "done"]
    assert payload_of(stream, "candidates")["hits"] == []
    assert payload_of(stream, "done") == {"count": 0, "stage2": "skipped"}


def test_a_url_without_q_is_400_and_never_a_stream() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast"]))

    response = client.get("/search", headers=AUTH)

    assert response.status_code == 400
    assert response.mimetype == "application/json"
    error = response.get_json()["error"]
    assert error["code"] == "missing_query"
    assert error["detail"] == {}
    assert error["message"]


def test_a_limit_bounds_the_hits_and_the_count_a_terminal_only_client_reads() -> None:
    store = a_store_holding(["forecast"] * 5)

    stream = search(a_client_over(store), q="forecast", limit="2")

    assert len(payload_of(stream, "candidates")["hits"]) == 2
    assert payload_of(stream, "done")["count"] == 2
    assert store.limits == [2]


def test_no_limit_searches_with_the_use_case_default() -> None:
    store = a_store_holding(["forecast"])

    search(a_client_over(store), q="forecast")

    assert store.limits == [STAGE_ONE_CANDIDATE_LIMIT]


@pytest.mark.parametrize("limit", ["0", "-1", "1.5", "many", ""])
def test_a_limit_that_is_not_a_positive_integer_is_400_before_the_store_is_asked(limit: str) -> None:
    store = a_store_holding(["forecast"])

    response = a_client_over(store).get("/search", query_string={"q": "forecast", "limit": limit}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_limit"
    assert store.limits == []


def test_the_stream_is_named_uncached_and_unbuffered() -> None:
    client = a_client_over(a_store_holding(["forecast"]))

    response = client.get("/search", query_string={"q": "forecast"}, headers=AUTH)

    assert response.mimetype == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Accel-Buffering"] == "no"


def test_search_is_behind_the_token_like_every_other_route() -> None:
    client = a_client_over(a_store_holding(["forecast"]))

    response = client.get("/search", query_string={"q": "forecast"})

    assert response.status_code == 401
