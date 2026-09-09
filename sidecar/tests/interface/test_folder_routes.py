from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.manage_folders import ManageFolders
from sidecar.domain.identity import file_id
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.folder_routes import build_folder_blueprint
from tests.fakes.clock import FakeClock
from tests.fakes.folder_store import FakeFolderStore

TOKEN = "test-token-123"
ADDED_AT = datetime(2026, 1, 1, tzinfo=UTC)
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _build_client() -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)

    manage = ManageFolders(folders=FakeFolderStore(FakeClock(ADDED_AT)))
    app.register_blueprint(build_folder_blueprint(manage))

    return app.test_client()


def test_folders_is_empty_before_the_first_add() -> None:
    client = _build_client()

    response = client.get("/folders", headers=AUTH)

    assert response.status_code == 200
    assert response.get_json() == {"folders": []}


def test_adding_a_folder_returns_201_with_the_folder(tmp_path: Path) -> None:
    client = _build_client()

    response = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH)

    assert response.status_code == 201
    assert response.get_json() == {
        "id": file_id(tmp_path),
        "path": str(tmp_path),
        "enabled": True,
        "added_at": "2026-01-01T00:00:00+00:00",
    }


def test_adding_the_same_folder_twice_is_still_201_with_one_folder(tmp_path: Path) -> None:
    client = _build_client()

    first = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH)
    second = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH)

    assert second.status_code == 201
    assert second.get_json() == first.get_json()
    assert client.get("/folders", headers=AUTH).get_json() == {"folders": [first.get_json()]}


def test_an_added_folder_is_in_the_list(tmp_path: Path) -> None:
    client = _build_client()
    added = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH).get_json()

    response = client.get("/folders", headers=AUTH)

    assert response.get_json() == {"folders": [added]}


def test_both_folder_bodies_are_uncached(tmp_path: Path) -> None:
    client = _build_client()

    created = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH)
    listed = client.get("/folders", headers=AUTH)

    assert created.headers["Cache-Control"] == "no-store"
    assert listed.headers["Cache-Control"] == "no-store"


def test_a_body_that_is_not_json_is_400(tmp_path: Path) -> None:
    client = _build_client()

    response = client.post("/folders", data=str(tmp_path), content_type="text/plain", headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_broken_json_is_400() -> None:
    client = _build_client()

    response = client.post("/folders", data='{"path":', content_type="application/json", headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_a_body_without_a_path_is_400() -> None:
    client = _build_client()

    response = client.post("/folders", json={}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_a_path_that_is_not_text_is_400() -> None:
    client = _build_client()

    response = client.post("/folders", json={"path": 12}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_a_path_the_use_case_rejects_is_400_naming_the_path(tmp_path: Path) -> None:
    client = _build_client()
    missing = tmp_path / "gone"

    response = client.post("/folders", json={"path": str(missing)}, headers=AUTH)

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "invalid_request"
    assert str(missing) in error["message"]
    assert client.get("/folders", headers=AUTH).get_json() == {"folders": []}


def test_a_relative_path_is_400() -> None:
    client = _build_client()

    response = client.post("/folders", json={"path": "Documents/reports"}, headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_deleting_a_folder_is_204_with_no_body(tmp_path: Path) -> None:
    client = _build_client()
    folder_id = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH).get_json()["id"]

    response = client.delete(f"/folders/{folder_id}", headers=AUTH)

    assert response.status_code == 204
    assert response.data == b""
    assert client.get("/folders", headers=AUTH).get_json() == {"folders": []}


def test_deleting_an_id_that_is_not_there_is_still_204() -> None:
    client = _build_client()

    response = client.delete("/folders/not-an-id", headers=AUTH)

    assert response.status_code == 204
    assert response.data == b""


def test_folders_needs_the_token() -> None:
    client = _build_client()

    assert client.get("/folders").status_code == 401
    assert client.post("/folders", json={"path": "/tmp"}).status_code == 401
    assert client.delete("/folders/not-an-id").status_code == 401


def test_a_folder_can_be_turned_off_and_back_on(tmp_path: Path) -> None:
    client = _build_client()
    folder_id = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH).get_json()["id"]

    off = client.patch(f"/folders/{folder_id}", json={"enabled": False}, headers=AUTH)
    assert off.status_code == 200
    assert off.get_json()["enabled"] is False

    on = client.patch(f"/folders/{folder_id}", json={"enabled": True}, headers=AUTH)
    assert on.get_json()["enabled"] is True


def test_a_toggle_without_a_flag_says_what_the_body_needs(tmp_path: Path) -> None:
    client = _build_client()
    folder_id = client.post("/folders", json={"path": str(tmp_path)}, headers=AUTH).get_json()["id"]

    response = client.patch(f"/folders/{folder_id}", json={}, headers=AUTH)

    assert response.status_code == 400
    assert "enabled" in response.get_json()["error"]["message"]


def test_toggling_a_folder_that_is_not_there_is_a_404() -> None:
    """Unlike remove: the caller is asking for a state no row can hold."""
    client = _build_client()

    assert client.patch("/folders/not-an-id", json={"enabled": False}, headers=AUTH).status_code == 404


def test_toggling_a_folder_needs_the_token(tmp_path: Path) -> None:
    client = _build_client()

    assert client.patch("/folders/not-an-id", json={"enabled": False}).status_code == 401
