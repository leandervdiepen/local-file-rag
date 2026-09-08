"""The POST /eval/golden/run wire contract, through the Flask test client over a working fake search."""

from __future__ import annotations

import json
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.run_golden_set import RunGoldenSet
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.eval_routes import build_eval_blueprint
from tests.application.test_run_golden_set import CORPUS, FakeTwoStageSearch, hit
from tests.fakes.vector_store import FakeVectorStore

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

GOLDEN_ROW = {
    "id": "g02",
    "query": "funnel chart",
    "expected_file": "decks/growth.pdf",
    "expected_page": 4,
    "text_free": True,
    "match_channel": "visual",
}


def a_search_that_finds_the_funnel_chart() -> FakeTwoStageSearch:
    search = FakeTwoStageSearch(FakeVectorStore())
    expected = hit("p4", page_no=4, score=0.5)
    other = hit("p1", page_no=1, score=3.0)
    search.stage_one_by_query["funnel chart"] = [other, expected]
    search.stage_two_by_query["funnel chart"] = [expected, other]
    return search


def a_client_over(search: FakeTwoStageSearch) -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    app.register_blueprint(build_eval_blueprint(RunGoldenSet(search, search.vectors, lambda: 0.0)))
    return app.test_client()


def events_in(body: str) -> list[tuple[str, Any]]:
    """Every named event in an SSE body, in order, as (name, payload)."""
    parsed: list[tuple[str, Any]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        fields = dict(line.partition(": ")[::2] for line in block.split("\n"))
        parsed.append((fields["event"], json.loads(fields["data"])))
    return parsed


def a_body(*rows: dict[str, Any], corpus_root: str = str(CORPUS)) -> dict[str, Any]:
    return {"corpus_root": corpus_root, "queries": list(rows or [GOLDEN_ROW])}


def run_golden(client: FlaskClient, body: dict[str, Any]) -> list[tuple[str, Any]]:
    response = client.post("/eval/golden/run", json=body, headers=AUTH)
    assert response.status_code == 200
    return events_in(response.get_data(as_text=True))


def test_the_stream_is_progress_then_query_per_row_and_exactly_one_done() -> None:
    second_row = {**GOLDEN_ROW, "id": "g11", "query": "hosting invoice", "text_free": False, "match_channel": "content"}

    stream = run_golden(a_client_over(a_search_that_finds_the_funnel_chart()), a_body(GOLDEN_ROW, second_row))

    assert [name for name, _ in stream] == ["progress", "query", "progress", "query", "done"]
    assert stream[0][1] == {"done": 0, "total": 2}
    assert stream[2][1] == {"done": 1, "total": 2}
    assert [payload["id"] for name, payload in stream if name == "query"] == ["g02", "g11"]


def test_a_query_event_carries_every_field_with_files_relative_to_the_corpus_root() -> None:
    stream = run_golden(a_client_over(a_search_that_finds_the_funnel_chart()), a_body())

    query = stream[1][1]
    assert query == {
        "id": "g02",
        "query": "funnel chart",
        "expected": {"file": "decks/growth.pdf", "page": 4},
        "text_free": True,
        "match_channel": "visual",
        "candidates": 2,
        "stage1_rank": 2,
        "embedded_before_run": 0,
        "cap_miss": False,
        "visual_only": False,
        "top10": [
            {"page_id": "p4", "file": "decks/growth.pdf", "page": 4, "score": 0.5, "stage": "content"},
            {"page_id": "p1", "file": "decks/growth.pdf", "page": 1, "score": 3.0, "stage": "content"},
        ],
        "rank": 1,
        "hit1": True,
        "hit5": True,
        "hit10": True,
        "stage1_ms": 0,
        "stage2_ms": 0,
        "cold_pages": 2,
    }


def test_done_carries_the_aggregates_with_null_rates_for_an_empty_split() -> None:
    stream = run_golden(a_client_over(a_search_that_finds_the_funnel_chart()), a_body())

    aggregates = stream[-1][1]["aggregates"]
    assert aggregates["overall"] == {
        "count": 1,
        "hit1": 1.0,
        "hit5": 1.0,
        "hit10": 1.0,
        "mrr10": 1.0,
        "stage1_hit": 1.0,
        "stage2_hit5": 1.0,
    }
    assert aggregates["by_text_free"]["true"]["count"] == 1
    assert aggregates["by_text_free"]["false"] == {
        "count": 0,
        "hit1": None,
        "hit5": None,
        "hit10": None,
        "mrr10": None,
        "stage1_hit": None,
        "stage2_hit5": None,
    }
    assert set(aggregates["by_match_channel"]) == {"visual", "filename", "content"}
    assert aggregates["by_match_channel"]["content"]["count"] == 0


def test_a_miss_streams_null_ranks_rather_than_zero() -> None:
    search = FakeTwoStageSearch(FakeVectorStore())
    search.stage_one_by_query["funnel chart"] = [hit("p1", page_no=1)]

    stream = run_golden(a_client_over(search), a_body())

    query = stream[1][1]
    assert (query["stage1_rank"], query["rank"], query["hit10"]) == (None, None, False)
    assert stream[-1][1]["aggregates"]["overall"]["mrr10"] == 0.0


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {"queries": [GOLDEN_ROW]},
        {"corpus_root": "relative/corpus", "queries": [GOLDEN_ROW]},
        {"corpus_root": str(CORPUS), "queries": []},
        {"corpus_root": str(CORPUS), "queries": "g02"},
        {"corpus_root": str(CORPUS), "queries": ["g02"]},
        {"corpus_root": str(CORPUS), "queries": [{k: v for k, v in GOLDEN_ROW.items() if k != "expected_page"}]},
        {"corpus_root": str(CORPUS), "queries": [{**GOLDEN_ROW, "expected_page": "4"}]},
        {"corpus_root": str(CORPUS), "queries": [{**GOLDEN_ROW, "expected_page": True}]},
        {"corpus_root": str(CORPUS), "queries": [{**GOLDEN_ROW, "text_free": "yes"}]},
        {"corpus_root": str(CORPUS), "queries": [{**GOLDEN_ROW, "match_channel": "ocr"}]},
        {"corpus_root": str(CORPUS), "queries": [{**GOLDEN_ROW, "expected_file": "/corpus/decks/growth.pdf"}]},
    ],
)
def test_a_body_that_is_not_a_golden_set_is_400_and_never_a_stream(body: Any) -> None:
    client = a_client_over(a_search_that_finds_the_funnel_chart())

    response = client.post("/eval/golden/run", json=body, headers=AUTH)

    assert response.status_code == 400
    assert response.mimetype == "application/json"
    error = response.get_json()["error"]
    assert error["code"] == "invalid_golden_set"
    assert error["message"]
    assert error["detail"] == {}


def test_a_body_that_is_not_json_is_400() -> None:
    client = a_client_over(a_search_that_finds_the_funnel_chart())

    response = client.post("/eval/golden/run", data="corpus_root=/corpus", headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_golden_set"


def test_the_stream_is_named_uncached_and_unbuffered() -> None:
    response = a_client_over(a_search_that_finds_the_funnel_chart()).post(
        "/eval/golden/run", json=a_body(), headers=AUTH
    )

    assert response.mimetype == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Accel-Buffering"] == "no"


def test_the_route_is_behind_the_token_like_every_other_route() -> None:
    response = a_client_over(a_search_that_finds_the_funnel_chart()).post("/eval/golden/run", json=a_body())

    assert response.status_code == 401
