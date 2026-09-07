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
from tests.fakes.index_store import FakeIndexStore

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
    store.upsert_pages([Page(id=f"p{n}", file_id="f1", page_no=n, text=t) for n, t in enumerate(texts, start=1)])
    return store


def a_client_over(store: FakeIndexStore) -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    app.register_blueprint(build_search_blueprint(Search(store)))
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


def test_a_match_streams_the_hit_then_a_done_carrying_the_count() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast for hosting"]))

    stream = search(client, q="forecast")

    assert [name for name, _ in stream] == ["candidates", "done"]
    assert stream[0][1]["hits"] == [
        {
            "page_id": "p1",
            "file_id": "f1",
            "path": "/corpus/notes.md",
            "page_no": 1,
            "kind": "text",
            "score": 1.0,
            "stage": "content",
            "snippet": "quarterly forecast for hosting",
        }
    ]
    assert stream[1][1] == {"count": 1}


def test_took_ms_is_a_whole_number_of_milliseconds() -> None:
    client = a_client_over(a_store_holding(["quarterly forecast"]))

    took_ms = search(client, q="forecast")[0][1]["took_ms"]

    assert isinstance(took_ms, int)
    assert took_ms >= 0


@pytest.mark.parametrize("query", ["", "   ", "\t\n"])
def test_nothing_typed_streams_no_hits_rather_than_the_whole_index(query: str) -> None:
    client = a_client_over(a_store_holding(["quarterly forecast"]))

    stream = search(client, q=query)

    assert [name for name, _ in stream] == ["candidates", "done"]
    assert stream[0][1]["hits"] == []
    assert stream[1][1] == {"count": 0}


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

    assert len(stream[0][1]["hits"]) == 2
    assert stream[1][1] == {"count": 2}
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
