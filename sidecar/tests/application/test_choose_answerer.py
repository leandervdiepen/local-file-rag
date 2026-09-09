"""Which provider one answer comes from, and what it says when it cannot."""

from __future__ import annotations

import pytest

from sidecar.application.choose_answerer import ChooseAnswerer
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.errors import AnswerUnavailableError, ValidationError
from sidecar.domain.providers import DEFAULT_PROVIDER_ID, PROVIDERS, Provider, ProviderId
from tests.fakes.answerer import FakeAnswerer


class Built:
    """Records what the composition root would have been asked to build."""

    def __init__(self) -> None:
        self.calls: list[tuple[Provider, str | None]] = []

    def __call__(self, provider: Provider, api_key: str | None) -> FakeAnswerer:
        self.calls.append((provider, api_key))
        return FakeAnswerer()


def a_provider_needing_a_key() -> ProviderId:
    return next(provider.id for provider in PROVIDERS if provider.needs_key)


def a_local_provider() -> ProviderId:
    return next(provider.id for provider in PROVIDERS if not provider.needs_key)


def test_a_provider_with_a_key_is_built_with_it() -> None:
    keys, built = ProviderKeys(), Built()
    provider = a_provider_needing_a_key()
    keys.remember(provider, "sk-live")

    ChooseAnswerer(keys, built).for_provider(provider.value)

    assert built.calls[0][1] == "sk-live"


def test_a_provider_with_no_key_says_which_one_and_what_to_do() -> None:
    with pytest.raises(AnswerUnavailableError) as raised:
        ChooseAnswerer(ProviderKeys(), Built()).for_provider(a_provider_needing_a_key().value)

    assert "Settings" in raised.value.message
    assert "runs on this Mac" in raised.value.message


def test_a_provider_that_runs_on_this_mac_needs_no_key() -> None:
    built = Built()

    ChooseAnswerer(ProviderKeys(), built).for_provider(a_local_provider().value)

    assert built.calls[0][1] is None


def test_a_provider_that_is_not_in_the_registry_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        ChooseAnswerer(ProviderKeys(), Built()).for_provider("hotdog")


def test_a_key_added_between_two_questions_takes_effect_on_the_second() -> None:
    """A cached adapter would go on using the old key until the app restarted."""
    keys, built = ProviderKeys(), Built()
    provider = a_provider_needing_a_key()
    choose = ChooseAnswerer(keys, built)
    keys.remember(provider, "sk-first")
    choose.for_provider(provider.value)

    keys.remember(provider, "sk-second")
    choose.for_provider(provider.value)

    assert [key for _, key in built.calls] == ["sk-first", "sk-second"]


def test_the_default_provider_still_needs_a_key_and_says_so_upfront() -> None:
    """D38 said the app answers before the user has any key. It does not.

    OpenRouter's free tier is free per token and still authenticated, and
    every day 4 measurement was taken with the key in `.env`. Saying which
    key is missing beats letting the provider answer 401 into the chat panel.
    """
    with pytest.raises(AnswerUnavailableError) as raised:
        ChooseAnswerer(ProviderKeys(), Built()).for_provider(DEFAULT_PROVIDER_ID)

    assert "OpenRouter" in raised.value.message


def test_a_key_is_kept_per_provider() -> None:
    keys = ProviderKeys()

    keys.remember(ProviderId.ANTHROPIC, "sk-ant")
    keys.remember(ProviderId.OPENAI, "sk-oai")

    assert keys.key_for(ProviderId.ANTHROPIC) == "sk-ant"
    assert keys.key_for(ProviderId.OPENAI) == "sk-oai"
    assert keys.key_for(ProviderId.GEMINI) is None


def test_emptying_the_field_forgets_the_key_rather_than_storing_a_blank() -> None:
    """A blank key leaves the app authenticating with nothing and blaming the provider's 401."""
    keys = ProviderKeys()
    keys.remember(ProviderId.ANTHROPIC, "sk-ant")

    keys.remember(ProviderId.ANTHROPIC, "   ")

    assert keys.key_for(ProviderId.ANTHROPIC) is None
    assert keys.known() == set()


def test_a_key_is_stored_without_the_whitespace_a_paste_brings() -> None:
    keys = ProviderKeys()

    keys.remember(ProviderId.ANTHROPIC, "  sk-ant\n")

    assert keys.key_for(ProviderId.ANTHROPIC) == "sk-ant"
