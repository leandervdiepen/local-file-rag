"""What each provider can offer, asked of the provider and cached briefly."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from sidecar.application.catalogue_ports import ModelCatalogue
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.catalogue import OfferedModel, offerable
from sidecar.domain.errors import NotFoundError
from sidecar.domain.providers import PROVIDERS, Provider, ProviderId

logger = logging.getLogger(__name__)

# Long enough that opening the settings screen twice costs one round trip, and
# short enough that pulling a model in Ollama shows up without a restart.
CACHE_SECONDS = 60.0


@dataclass(frozen=True)
class ProviderSummary:
    """One row of the provider list, before anyone has asked what it offers."""

    provider: Provider
    has_key: bool


class ListModels:
    """Lists providers, and lists what one provider is offering right now.

    Cached for a minute per provider, because the settings screen asks on
    every open and a provider's list does not change between two clicks. The
    cache is keyed by provider and dropped when its key changes, so adding a
    key shows the models it unlocked immediately.
    """

    def __init__(
        self,
        keys: ProviderKeys,
        catalogues: dict[ProviderId, ModelCatalogue],
        clock: Callable[[], float] = time.monotonic,
        cache_seconds: float = CACHE_SECONDS,
    ) -> None:
        self._keys = keys
        self._catalogues = catalogues
        self._clock = clock
        self._cache_seconds = cache_seconds
        self._lock = threading.Lock()
        self._cached: dict[ProviderId, tuple[float, str | None, list[OfferedModel]]] = {}

    def providers(self) -> list[ProviderSummary]:
        """Every provider that has a catalogue behind it, in registry order."""
        keyed = self._keys.known()
        return [
            ProviderSummary(provider, provider.id in keyed) for provider in PROVIDERS if provider.id in self._catalogues
        ]

    def models_for(self, provider_id: str) -> list[OfferedModel]:
        """What this provider offers, filtered to what may answer and cheapest first.

        Raises `NotFoundError` for a provider this app does not know, and
        `AnswerUnavailableError` when the provider cannot be reached, so the
        settings screen can say which of the two happened.
        """
        provider = self._provider(provider_id)
        key = self._keys.key_for(provider.id)
        cached = self._fresh(provider.id, key)
        if cached is not None:
            return offerable(cached)

        models = self._catalogues[provider.id].models_for(provider, key)
        with self._lock:
            self._cached[provider.id] = (self._clock(), key, models)
        logger.info("%s offers %d models, %d of them usable", provider.label, len(models), len(offerable(models)))
        return offerable(models)

    def price_for(self, provider_id: str, model_id: str) -> OfferedModel | None:
        """What this provider says that model costs, or `None` when it cannot be asked.

        Used to price an answer after it arrives, so a provider that has gone
        away since must not turn a finished answer into an error. Every
        failure is simply an unknown price.
        """
        try:
            return next((model for model in self.models_for(provider_id) if model.id == model_id), None)
        except Exception:
            logger.info("could not price %s on %s", model_id, provider_id)
            return None

    def _fresh(self, provider_id: ProviderId, key: str | None) -> list[OfferedModel] | None:
        with self._lock:
            entry = self._cached.get(provider_id)
        if entry is None:
            return None
        taken_at, taken_with, models = entry
        if taken_with != key or self._clock() - taken_at > self._cache_seconds:
            return None
        return models

    def _provider(self, provider_id: str) -> Provider:
        for provider in PROVIDERS:
            if provider.id.value == provider_id and provider.id in self._catalogues:
                return provider
        raise NotFoundError(f"{provider_id} is not a provider this app can use.")
