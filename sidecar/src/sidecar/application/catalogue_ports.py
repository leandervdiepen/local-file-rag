"""The port that asks a provider what it can do today."""

from __future__ import annotations

from typing import Protocol

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.providers import Provider


class ModelCatalogue(Protocol):
    """Lists the models one provider is offering.

    One implementation per provider API shape. The composition root maps a
    provider to its catalogue, so nothing above this knows that OpenRouter
    publishes prices and OpenAI does not.
    """

    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        """Every model this provider offers now, unfiltered and unsorted.

        Raises `AnswerUnavailableError` when the provider cannot be reached or
        refuses the key, with a message written for the settings screen.
        Returns an empty list for a provider that is reachable and has nothing
        to offer, which for a local server means nothing is pulled yet.
        """
        ...
