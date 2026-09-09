"""The /providers, /models and /secrets routes. A key goes in and never comes back out."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.list_models import ListModels
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.providers import ProviderId
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.settings_routes import build_settings_blueprint
from tests.fakes.model_catalogue import FakeModelCatalogue

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

SEEING = OfferedModel(ProviderId.OPENROUTER, "seer/one", "Seer One", True, 1.0, 2.0, 128_000)
BLIND = OfferedModel(ProviderId.OPENROUTER, "blind/one", "Blind One", False, 0.0, 0.0)
UNPRICED = OfferedModel(ProviderId.OPENROUTER, "quiet/one", "Quiet One", None, None, None)


def _client(models: list[OfferedModel] | None = None) -> tuple[FlaskClient, ProviderKeys, FakeModelCatalogue]:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)
    keys = ProviderKeys()
    catalogue = FakeModelCatalogue(models if models is not None else [SEEING])
    app.register_blueprint(
        build_settings_blueprint(keys, ListModels(keys, {ProviderId.OPENROUTER: catalogue}, cache_seconds=0.0))
    )
    return app.test_client(), keys, catalogue


def test_the_provider_list_says_what_each_one_needs() -> None:
    client, _, _ = _client()

    rows = {row["id"]: row for row in client.get("/providers", headers=AUTH).get_json()["providers"]}

    assert rows["openrouter"]["needs_key"] is True
    assert rows["openrouter"]["has_key"] is False
    assert rows["openrouter"]["runs_locally"] is False


def test_a_provider_reports_the_models_it_is_offering_now() -> None:
    client, _, _ = _client()

    body = client.get("/providers/openrouter/models", headers=AUTH).get_json()

    assert [model["id"] for model in body["models"]] == ["seer/one"]
    assert body["models"][0]["context_tokens"] == 128_000


def test_a_model_that_cannot_see_is_never_offered() -> None:
    client, _, _ = _client([SEEING, BLIND])

    body = client.get("/providers/openrouter/models", headers=AUTH).get_json()

    assert [model["id"] for model in body["models"]] == ["seer/one"]


def test_the_price_is_what_one_question_of_this_shape_costs() -> None:
    client, _, _ = _client()

    model = client.get("/providers/openrouter/models", headers=AUTH).get_json()["models"][0]

    # 4,000 in at $1/M and 300 out at $2/M.
    assert model["usd_per_question"] == (4_000 * 1.0 + 300 * 2.0) / 1_000_000


def test_a_model_the_provider_does_not_price_comes_back_null_rather_than_free() -> None:
    client, _, _ = _client([UNPRICED])

    model = client.get("/providers/openrouter/models", headers=AUTH).get_json()["models"][0]

    assert model["usd_per_question"] is None
    assert model["sees_images"] is None


def test_a_provider_that_cannot_be_reached_says_so() -> None:
    client, _, catalogue = _client()
    catalogue.unreachable = True

    response = client.get("/providers/openrouter/models", headers=AUTH)

    assert response.status_code >= 400
    assert "reached" in response.get_json()["error"]["message"]


def test_a_provider_this_app_does_not_know_is_a_404() -> None:
    client, _, _ = _client()

    assert client.get("/providers/hotdog/models", headers=AUTH).status_code == 404


def test_the_key_itself_never_comes_back() -> None:
    """The settings screen shows a filled field without ever reading the value."""
    client, _, _ = _client()
    client.put("/secrets/openrouter", json={"key": "sk-secret"}, headers=AUTH)

    for path in ("/secrets", "/providers"):
        assert "sk-secret" not in client.get(path, headers=AUTH).get_data(as_text=True)

    assert client.get("/secrets", headers=AUTH).get_json()["providers"]["openrouter"] is True


def test_a_saved_key_is_the_one_the_provider_is_asked_with() -> None:
    client, _, catalogue = _client()

    client.put("/secrets/openrouter", json={"key": "sk-or"}, headers=AUTH)
    client.get("/providers/openrouter/models", headers=AUTH)

    assert catalogue.asked_with[-1] == "sk-or"


def test_a_key_can_be_taken_back() -> None:
    client, keys, _ = _client()
    client.put("/secrets/openrouter", json={"key": "sk-or"}, headers=AUTH)

    assert client.delete("/secrets/openrouter", headers=AUTH).status_code == 204
    assert keys.known() == set()


def test_deleting_a_key_that_is_not_there_is_still_204() -> None:
    client, _, _ = _client()

    assert client.delete("/secrets/anthropic", headers=AUTH).status_code == 204


def test_a_secret_for_a_provider_this_app_does_not_know_is_a_404() -> None:
    client, _, _ = _client()

    assert client.put("/secrets/hotdog", json={"key": "x"}, headers=AUTH).status_code == 404


def test_a_body_with_no_key_in_it_says_what_it_needs() -> None:
    client, _, _ = _client()

    response = client.put("/secrets/openrouter", json={}, headers=AUTH)

    assert response.status_code == 400
    assert "key" in response.get_json()["error"]["message"]


def test_the_settings_routes_need_the_token_like_every_other() -> None:
    client, _, _ = _client()

    assert client.get("/providers").status_code == 401
    assert client.get("/providers/openrouter/models").status_code == 401
    assert client.get("/secrets").status_code == 401
    assert client.put("/secrets/openrouter", json={"key": "x"}).status_code == 401
