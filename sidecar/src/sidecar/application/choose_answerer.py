"""Picking where one answer comes from, and saying what is missing when it cannot."""

from __future__ import annotations

from collections.abc import Callable

from sidecar.application.ports import Answerer
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.errors import AnswerUnavailableError, ValidationError
from sidecar.domain.providers import PROVIDERS, Provider

BuildAnswerer = Callable[[Provider, str | None], Answerer]

_NEEDS_A_KEY = "{label} needs an API key. Add one in Settings, or pick a model that runs on this Mac."


class ChooseAnswerer:
    """The answerer for a provider, built fresh each time from the key held now.

    By provider rather than by model, because which models exist is the
    provider's answer to give and changes without this app being rebuilt. What
    this decides is where the request goes and what authenticates it.

    Fresh rather than cached, because the settings screen can change a key
    between two questions and a cached adapter would go on using the old one
    until the app restarted.
    """

    def __init__(self, keys: ProviderKeys, build: BuildAnswerer) -> None:
        self._keys = keys
        self._build = build

    def for_provider(self, provider_id: str) -> Answerer:
        """Raises `ValidationError` for a provider that is not in the registry, and
        `AnswerUnavailableError` for one that has no key yet."""
        provider = next((row for row in PROVIDERS if row.id.value == provider_id), None)
        if provider is None:
            raise ValidationError(f"{provider_id} is not a provider this app can use.")
        key = self._keys.key_for(provider.id)
        if provider.needs_key and key is None:
            raise AnswerUnavailableError(_NEEDS_A_KEY.format(label=provider.label))
        return self._build(provider, key)
