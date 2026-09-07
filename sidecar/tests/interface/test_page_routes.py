"""`/pages/{id}/image` through the Flask test client with fake ports. This test is the contract."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.render_page import FULL_LONG_SIDE_PX, THUMB_LONG_SIDE_PX
from sidecar.domain.entities import FileKind
from sidecar.domain.identity import file_id, page_id
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.page_routes import build_page_blueprint
from tests.application.test_render_page import CONTENT_HASH, MISSING, REPORT, CountingPageSource, a_png, a_render_page

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
PAGE = page_id(file_id(REPORT), 2)
IMAGE_URL = f"/pages/{PAGE}/image"


def a_client(
    file_kind: FileKind = FileKind.PDF,
    served_kinds: tuple[FileKind, ...] = (FileKind.PDF,),
) -> tuple[FlaskClient, dict[FileKind, CountingPageSource]]:
    render, sources = a_render_page(file_kind, served_kinds)

    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    app.register_blueprint(build_page_blueprint(render))

    return app.test_client(), sources


def test_a_thumb_comes_back_as_png_under_an_etag_the_client_may_keep_forever() -> None:
    client, _ = a_client()

    response = client.get(f"{IMAGE_URL}?size=thumb", headers=AUTH)

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == a_png(THUMB_LONG_SIDE_PX, 2)
    assert response.headers["ETag"] == f'"{CONTENT_HASH}-thumb"'
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_a_request_without_a_size_gets_the_thumb() -> None:
    client, sources = a_client()

    response = client.get(IMAGE_URL, headers=AUTH)

    assert response.status_code == 200
    assert sources[FileKind.PDF].renders == [(REPORT, 2, THUMB_LONG_SIDE_PX)]


def test_full_renders_the_bigger_picture_under_its_own_etag() -> None:
    client, sources = a_client()

    response = client.get(f"{IMAGE_URL}?size=full", headers=AUTH)

    assert response.data == a_png(FULL_LONG_SIDE_PX, 2)
    assert sources[FileKind.PDF].renders == [(REPORT, 2, FULL_LONG_SIDE_PX)]
    assert response.headers["ETag"] == f'"{CONTENT_HASH}-full"'


def test_a_matching_etag_is_304_with_no_body_and_nothing_rendered() -> None:
    client, sources = a_client()
    first = client.get(IMAGE_URL, headers=AUTH)
    assert sources[FileKind.PDF].renders == [(REPORT, 2, THUMB_LONG_SIDE_PX)]

    again = client.get(IMAGE_URL, headers={**AUTH, "If-None-Match": first.headers["ETag"]})

    assert again.status_code == 304
    assert again.data == b""
    assert again.headers["ETag"] == first.headers["ETag"]
    assert again.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert sources[FileKind.PDF].renders == [(REPORT, 2, THUMB_LONG_SIDE_PX)]


def test_the_thumb_etag_does_not_answer_for_the_full_size() -> None:
    client, _ = a_client()
    thumb = client.get(f"{IMAGE_URL}?size=thumb", headers=AUTH)

    full = client.get(f"{IMAGE_URL}?size=full", headers={**AUTH, "If-None-Match": thumb.headers["ETag"]})

    assert full.status_code == 200
    assert full.data == a_png(FULL_LONG_SIDE_PX, 2)


def test_an_etag_from_an_older_version_of_the_file_renders_again() -> None:
    client, _ = a_client()

    response = client.get(IMAGE_URL, headers={**AUTH, "If-None-Match": '"an-older-hash-thumb"'})

    assert response.status_code == 200
    assert response.data == a_png(THUMB_LONG_SIDE_PX, 2)


def test_a_size_that_does_not_exist_is_400_and_renders_nothing() -> None:
    client, sources = a_client()

    response = client.get(f"{IMAGE_URL}?size=huge", headers=AUTH)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": {
            "code": "invalid_size",
            "message": "That size does not exist. Ask for thumb or full.",
            "detail": {"size": "huge"},
        }
    }
    assert sources[FileKind.PDF].renders == []


def test_a_malformed_page_id_is_400() -> None:
    client, _ = a_client()

    response = client.get("/pages/not-a-page-id/image", headers=AUTH)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_a_well_formed_page_id_that_is_not_indexed_is_404() -> None:
    client, _ = a_client()

    response = client.get(f"/pages/{page_id(file_id(MISSING), 1)}/image", headers=AUTH)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_a_file_whose_kind_this_build_cannot_render_is_404() -> None:
    client, _ = a_client(file_kind=FileKind.UNKNOWN)

    response = client.get(IMAGE_URL, headers=AUTH)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_the_route_needs_the_token_like_every_other() -> None:
    client, _ = a_client()

    response = client.get(IMAGE_URL)

    assert response.status_code == 401
