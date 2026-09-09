"""The renderer is a page, so without this the app cannot call its own sidecar."""

from __future__ import annotations

from flask import Flask, Response, jsonify
from flask.testing import FlaskClient

from sidecar.interface.auth import register_auth
from sidecar.interface.cors import register_cors
from sidecar.interface.errors import register_error_handlers

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
DEV_ORIGIN = "http://localhost:5173"
# A packaged renderer is a file:// page, and a file:// page's origin is this.
PACKAGED_ORIGIN = "null"


def _client() -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_cors(app)
    register_auth(app, TOKEN)

    @app.get("/thing")
    def thing() -> Response:
        return jsonify({"ok": True})

    return app.test_client()


def test_the_dev_server_origin_is_allowed_back() -> None:
    response = _client().get("/thing", headers={**AUTH, "Origin": DEV_ORIGIN})

    assert response.headers["Access-Control-Allow-Origin"] == DEV_ORIGIN


def test_a_packaged_file_page_is_allowed_back() -> None:
    """The shipped renderer loads from disk, so its origin is the string null."""
    response = _client().get("/thing", headers={**AUTH, "Origin": PACKAGED_ORIGIN})

    assert response.headers["Access-Control-Allow-Origin"] == PACKAGED_ORIGIN


def test_a_cached_response_is_not_handed_to_another_origin() -> None:
    response = _client().get("/thing", headers={**AUTH, "Origin": DEV_ORIGIN})

    assert response.headers["Vary"] == "Origin"


def test_a_preflight_is_answered_without_a_token() -> None:
    """A preflight cannot carry the header it is asking permission to send."""
    response = _client().options(
        "/thing",
        headers={"Origin": DEV_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


def test_answering_a_preflight_does_not_answer_the_request_behind_it() -> None:
    """The only thing a preflight buys is the right to try with a token."""
    response = _client().get("/thing", headers={"Origin": DEV_ORIGIN})

    assert response.status_code == 401


def test_every_method_the_app_uses_is_allowed() -> None:
    allowed = _client().options("/thing", headers={"Origin": DEV_ORIGIN}).headers["Access-Control-Allow-Methods"]

    assert all(method in allowed for method in ("GET", "POST", "PATCH", "DELETE"))
