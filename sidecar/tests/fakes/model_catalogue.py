"""A real, in-memory ModelCatalogue. Not a mock.

Tests seed it with what a provider would answer, including a provider that is
unreachable, which is the case the settings screen has to explain.
"""

from __future__ import annotations

from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.domain.providers import Provider


class FakeModelCatalogue:
    def __init__(self, models: list[OfferedModel] | None = None) -> None:
        self.models = list(models or [])
        self.unreachable = False
        self.asked_with: list[str | None] = []

    def models_for(self, provider: Provider, api_key: str | None) -> list[OfferedModel]:
        self.asked_with.append(api_key)
        if self.unreachable:
            raise AnswerUnavailableError("The provider could not be reached.")
        return list(self.models)
