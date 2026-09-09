"""Adapter for `ModelCatalogue` over an Ollama server on this machine.

Ollama lists what the user has actually pulled, which is the only honest
answer for a local provider: offering a model they have not downloaded would
be offering a several gigabyte surprise.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.domain.providers import Provider
from sidecar.infrastructure.wire_json import get_json

logger = logging.getLogger(__name__)

VISION = "vision"


class OllamaCatalogue:
    """The models pulled on this machine, each asked whether it can see."""

    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        root = _server_root(provider.base_url)
        body = get_json(f"{root}/api/tags", {})
        rows = body.get("models") if isinstance(body, dict) else None
        return [_offered(provider, root, row) for row in rows or [] if isinstance(row, dict)]


def _offered(provider: Provider, root: str, row: dict[str, Any]) -> OfferedModel:
    name = str(row.get("model") or row.get("name") or "")
    return OfferedModel(
        provider=provider.id,
        id=name,
        label=name,
        sees_images=_sees_images(root, name),
        # Local inference has no per token price, and that is a fact rather
        # than a missing number, so it is zero and not None.
        usd_per_m_input=0.0,
        usd_per_m_output=0.0,
    )


def _sees_images(root: str, name: str) -> bool | None:
    """Ask the server what this model can do. `None` when it will not say.

    A per model round trip, which is affordable because it is a local socket
    and the list is however many models one person has pulled.
    """
    try:
        shown = get_json(f"{root}/api/show?model={name}", {})
    except AnswerUnavailableError:
        logger.info("ollama would not describe %s, offering it without a modality", name)
        return None
    capabilities = shown.get("capabilities") if isinstance(shown, dict) else None
    if not isinstance(capabilities, list):
        return None
    return VISION in capabilities


def _server_root(base_url: str) -> str:
    """The server itself, not its OpenAI compatible path.

    The registry's base URL ends in `/v1` because that is where answers are
    posted, and `/api/tags` sits beside it rather than under it.
    """
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"
