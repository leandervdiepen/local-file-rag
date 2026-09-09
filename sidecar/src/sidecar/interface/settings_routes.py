"""The /providers, /models and /secrets routes.

What a provider offers is asked of the provider, not written down here, so a
price the settings screen shows is the price that provider is charging today.
A key arrives here and is never written down or handed back.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from sidecar.application.list_models import ListModels, ProviderSummary
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.catalogue import OfferedModel, cost_usd
from sidecar.domain.providers import ProviderId, runs_locally
from sidecar.interface.errors import error_response

_KEY_MISSING = 'The request needs a key. Send a JSON body like {"key": "sk-..."}.'
_UNKNOWN_PROVIDER = "That provider is not one this app can use."

# What one question of this app's shape costs: five page images in, a short
# answer out. The only form of a price a person choosing a model can compare.
_SAMPLE_INPUT_TOKENS = 4_000
_SAMPLE_OUTPUT_TOKENS = 300


def _provider_body(summary: ProviderSummary) -> dict[str, Any]:
    provider = summary.provider
    return {
        "id": provider.id.value,
        "label": provider.label,
        "needs_key": provider.needs_key,
        "has_key": summary.has_key,
        "runs_locally": runs_locally(provider),
    }


def _model_body(model: OfferedModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "label": model.label,
        "provider": model.provider.value,
        # Null when the provider publishes no price. The screen prints that as
        # unchecked, never as free.
        "usd_per_question": cost_usd(model, _SAMPLE_INPUT_TOKENS, _SAMPLE_OUTPUT_TOKENS),
        # Null when the provider does not say whether it reads images.
        "sees_images": model.sees_images,
        "context_tokens": model.context_tokens,
    }


def build_settings_blueprint(keys: ProviderKeys, list_models: ListModels) -> Blueprint:
    """Build the /providers, /models and /secrets blueprint."""
    bp = Blueprint("settings", __name__)

    @bp.get("/providers")
    def providers() -> Response:
        return _uncached(jsonify({"providers": [_provider_body(row) for row in list_models.providers()]}))

    @bp.get("/providers/<provider_id>/models")
    def models(provider_id: str) -> Response:
        offered = list_models.models_for(provider_id)
        return _uncached(jsonify({"models": [_model_body(model) for model in offered]}))

    @bp.get("/secrets")
    def secrets() -> Response:
        keyed = keys.known()
        return _uncached(jsonify({"providers": {provider.value: provider in keyed for provider in ProviderId}}))

    @bp.put("/secrets/<provider_id>")
    def put_secret(provider_id: str) -> Response:
        provider = _parse_provider(provider_id)
        if provider is None:
            return error_response("unknown_provider", _UNKNOWN_PROVIDER, status=404, detail={"provider": provider_id})
        body = request.get_json(silent=True)
        key = body.get("key") if isinstance(body, dict) else None
        if not isinstance(key, str):
            return error_response("invalid_request", _KEY_MISSING, status=400)

        keys.remember(provider, key)
        return Response(status=204)

    @bp.delete("/secrets/<provider_id>")
    def delete_secret(provider_id: str) -> Response:
        provider = _parse_provider(provider_id)
        if provider is not None:
            keys.forget(provider)
        return Response(status=204)

    return bp


def _uncached(response: Response) -> Response:
    """These change when a key is added, so a stale one is worse than a slow one."""
    response.headers["Cache-Control"] = "no-store"
    return response


def _parse_provider(provider_id: str) -> ProviderId | None:
    try:
        return ProviderId(provider_id)
    except ValueError:
        return None
