"""A real, in-memory stand-in for `ChooseAnswerer`. Not a mock.

Hands back one answerer whatever provider is asked for, and keeps the provider
ids it was asked about so a test can assert the question reached the right one.
"""

from __future__ import annotations

from sidecar.application.ports import Answerer


class FakeAnswererChoice:
    def __init__(self, answerer: Answerer) -> None:
        self.answerer = answerer
        self.asked_for: list[str] = []

    def for_provider(self, provider_id: str) -> Answerer:
        self.asked_for.append(provider_id)
        return self.answerer
