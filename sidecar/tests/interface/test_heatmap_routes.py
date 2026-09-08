"""The heatmap wire contract, through the Flask test client."""

from __future__ import annotations

from typing import Any

import numpy as np
from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.explain_page import ExplainPage
from sidecar.domain.heatmap import PatchGrid
from sidecar.domain.vectors import PageVectors, QueryVectors
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.heatmap_routes import build_heatmap_blueprint
from tests.fakes.page_embedder import feature_vector

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
GRID = PatchGrid(2, 2)
PATCH_WORDS = ["table", "chart", "notes", "funnel"]


class StubRenderPage:
    def run(self, page_id: str, size: object) -> bytes:
        return b"png"


class StubExplainer:
    def explain_page(self, image_png: bytes) -> tuple[PageVectors, PatchGrid]:
        rows = np.stack([feature_vector(word) for word in PATCH_WORDS]).astype(np.float16)
        return PageVectors(page_id="", vectors=rows, pool_factor=1), GRID

    def query_tokens(self, text: str) -> tuple[QueryVectors, tuple[str, ...]]:
        words = text.split()
        return QueryVectors(np.stack([feature_vector(word) for word in words])), tuple(words)


def a_client() -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    explain = ExplainPage(StubRenderPage(), StubExplainer())  # type: ignore[arg-type]
    app.register_blueprint(build_heatmap_blueprint(explain))
    return app.test_client()


def get(query: str) -> tuple[int, Any]:
    response = a_client().get("/pages/a:1/heatmap", query_string={"q": query}, headers=AUTH)
    return response.status_code, response.get_json()


def test_the_grid_comes_back_as_numbers_the_renderer_can_redraw() -> None:
    status, body = get("funnel")

    assert status == 200
    assert (body["rows"], body["cols"]) == (2, 2)
    assert np.array(body["combined"]).shape == (2, 2)
    assert body["combined"][1][1] == 1.0, "the patch carrying the query word is the hottest"


def test_one_map_per_typed_token_comes_back_named() -> None:
    _, body = get("chart funnel")

    assert [token["token"] for token in body["tokens"]] == ["chart", "funnel"]
    assert np.array(body["tokens"][0]["values"]).shape == (2, 2)


def test_the_default_threshold_travels_with_the_grid_so_the_slider_has_a_starting_point() -> None:
    _, body = get("funnel")

    assert body["threshold_percentile"] == 90.0
    assert 0.0 <= body["threshold"] <= 1.0


def test_a_heatmap_without_a_query_is_400_because_there_is_nothing_to_explain() -> None:
    response = a_client().get("/pages/a:1/heatmap", query_string={"q": "  "}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "missing_query"


def test_a_url_with_no_q_at_all_is_also_400() -> None:
    response = a_client().get("/pages/a:1/heatmap", headers=AUTH)

    assert response.status_code == 400


def test_the_heatmap_is_never_cached_because_it_depends_on_the_query() -> None:
    response = a_client().get("/pages/a:1/heatmap", query_string={"q": "funnel"}, headers=AUTH)

    assert response.headers["Cache-Control"] == "no-store"


def test_the_heatmap_is_behind_the_token_like_every_other_route() -> None:
    assert a_client().get("/pages/a:1/heatmap", query_string={"q": "funnel"}).status_code == 401
