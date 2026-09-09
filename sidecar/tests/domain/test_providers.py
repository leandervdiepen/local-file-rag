"""Where answers can come from. The places, not the models."""

from __future__ import annotations

from sidecar.domain.providers import (
    DEFAULT_PROVIDER_ID,
    PROVIDERS,
    ProviderId,
    runs_locally,
)


def test_every_provider_has_a_place_to_send_a_request() -> None:
    for provider in PROVIDERS:
        assert provider.base_url or provider.id is ProviderId.CUSTOM


def test_the_default_provider_is_one_that_exists() -> None:
    assert any(provider.id.value == DEFAULT_PROVIDER_ID for provider in PROVIDERS)


def test_the_default_provider_still_needs_a_key() -> None:
    """Free per token is not the same as open. D38's second half was wrong about this."""
    default = next(provider for provider in PROVIDERS if provider.id.value == DEFAULT_PROVIDER_ID)

    assert default.needs_key


def test_only_a_local_provider_keeps_everything_on_the_machine() -> None:
    ollama = next(p for p in PROVIDERS if p.id is ProviderId.OLLAMA)
    anthropic = next(p for p in PROVIDERS if p.id is ProviderId.ANTHROPIC)

    assert runs_locally(ollama)
    assert not runs_locally(anthropic)
    assert not ollama.needs_key, "a server on this machine has nobody to authenticate to"


def test_one_wire_format_serves_every_provider_but_anthropic() -> None:
    """D36: the difference between vendors is a row here, not another adapter."""
    wires = {provider.wire for provider in PROVIDERS}

    assert wires == {"anthropic", "openai"}


def test_no_two_providers_share_an_id() -> None:
    assert len({provider.id for provider in PROVIDERS}) == len(PROVIDERS)
