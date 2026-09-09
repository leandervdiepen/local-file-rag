"""Adapter for `ModelCatalogue` over OpenRouter's model list.

The only provider that publishes both prices and modalities, so this is the
one place the app can say what a question will cost without anybody typing a
number into a source file.
"""

from __future__ import annotations

from typing import Any

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.providers import Provider
from sidecar.infrastructure.wire_json import get_json

PER_MILLION = 1_000_000


class OpenRouterCatalogue:
    """Every model OpenRouter lists, with the price and modality it reports."""

    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        body = get_json(f"{provider.base_url}/models", headers)
        rows = body.get("data") if isinstance(body, dict) else None
        return [_offered(provider, row) for row in rows or [] if isinstance(row, dict)]


def _offered(provider: Provider, row: dict[str, Any]) -> OfferedModel:
    pricing = row.get("pricing") or {}
    architecture = row.get("architecture") or {}
    modalities = architecture.get("input_modalities") or []
    return OfferedModel(
        provider=provider.id,
        id=str(row.get("id", "")),
        label=str(row.get("name") or row.get("id", "")),
        # Reported per model, so this is a fact rather than the guess D37 warns about.
        sees_images="image" in modalities,
        usd_per_m_input=_per_million(pricing.get("prompt")),
        usd_per_m_output=_per_million(pricing.get("completion")),
        context_tokens=_whole(row.get("context_length")),
    )


def _per_million(value: object) -> float | None:
    """OpenRouter quotes dollars per token, as a string. A missing one is unknown, not free.

    A negative rate is the router's way of saying the price varies with
    whichever model it picks, which `openrouter/auto` reports as -1. Read
    literally that is minus a million dollars a million tokens, so it is
    unknown. Measured against the live API 2026-09-09.
    """
    if not isinstance(value, str | int | float):
        return None
    try:
        per_token = float(value)
    except ValueError:
        return None
    return None if per_token < 0 else per_token * PER_MILLION


def _whole(value: object) -> int | None:
    if not isinstance(value, str | int | float):
        return None
    try:
        return int(value)
    except ValueError:
        return None
