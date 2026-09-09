"""Adapter for `ModelCatalogue` over the OpenAI style `/models` list.

Serves OpenAI, Gemini's compatibility endpoint and any custom endpoint. They
return ids and nothing else useful: no price, no modality. Both come back as
`None`, which the settings screen shows as unchecked rather than inventing.
"""

from __future__ import annotations

from typing import Any

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.providers import Provider
from sidecar.infrastructure.wire_json import get_json


class OpenAICompatibleCatalogue:
    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        body = get_json(f"{provider.base_url}/models", headers)
        rows = body.get("data") if isinstance(body, dict) else None
        return [_offered(provider, row) for row in rows or [] if isinstance(row, dict)]


def _offered(provider: Provider, row: dict[str, Any]) -> OfferedModel:
    identifier = str(row.get("id", ""))
    return OfferedModel(
        provider=provider.id,
        id=identifier,
        label=identifier,
        sees_images=None,
        usd_per_m_input=None,
        usd_per_m_output=None,
    )
