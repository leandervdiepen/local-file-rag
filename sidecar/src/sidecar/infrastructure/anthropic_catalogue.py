"""Adapter for `ModelCatalogue` over Anthropic's model list.

Anthropic publishes ids and display names and no prices, so every model here
comes back unpriced. Every current Claude model reads images, but the API does
not say so, and `None` is the honest answer to a question nobody asked it.
"""

from __future__ import annotations

from typing import Any

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.providers import Provider
from sidecar.infrastructure.wire_json import get_json

API_VERSION = "2023-06-01"


class AnthropicCatalogue:
    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        headers = {"anthropic-version": API_VERSION}
        if api_key:
            headers["x-api-key"] = api_key
        body = get_json(f"{provider.base_url}/v1/models?limit=100", headers)
        rows = body.get("data") if isinstance(body, dict) else None
        return [_offered(provider, row) for row in rows or [] if isinstance(row, dict)]


def _offered(provider: Provider, row: dict[str, Any]) -> OfferedModel:
    identifier = str(row.get("id", ""))
    return OfferedModel(
        provider=provider.id,
        id=identifier,
        label=str(row.get("display_name") or identifier),
        sees_images=None,
        usd_per_m_input=None,
        usd_per_m_output=None,
    )
