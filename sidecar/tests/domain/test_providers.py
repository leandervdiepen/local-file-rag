"""The model registry: what may be offered, what it costs, and what stays on the machine."""

from __future__ import annotations

import pytest

from sidecar.domain.providers import (
    DEFAULT_MODEL_ID,
    MODELS,
    PRICES_READ_ON,
    PROVIDERS,
    AnswerModel,
    ProviderId,
    cost_usd,
    find_model,
    provider_for,
    runs_locally,
    selectable_models,
)


def test_every_model_names_a_provider_that_exists() -> None:
    for model in MODELS:
        assert provider_for(model) is not None


def test_a_model_that_cannot_see_is_never_offered() -> None:
    """D37: a text-only model answers a question about a chart from the question alone."""
    blind = AnswerModel(ProviderId.OPENAI, "text-only", "Text only", False, 1.0, 1.0, 100)

    assert blind not in selectable_models()
    assert all(model.sees_images for model in selectable_models())


def test_the_default_model_is_one_that_can_be_chosen() -> None:
    default = find_model(DEFAULT_MODEL_ID)

    assert default is not None
    assert default in selectable_models()


def test_a_model_that_is_not_configured_is_none_rather_than_a_guess() -> None:
    assert find_model("something/made-up") is None


def test_cost_is_per_million_tokens_of_each_kind() -> None:
    model = AnswerModel(ProviderId.OPENAI, "m", "M", True, usd_per_m_input=2.0, usd_per_m_output=10.0, context_tokens=1)

    assert cost_usd(model, 1_000_000, 0) == pytest.approx(2.0)
    assert cost_usd(model, 0, 1_000_000) == pytest.approx(10.0)
    assert cost_usd(model, 500_000, 100_000) == pytest.approx(2.0)


def test_a_free_model_costs_nothing_and_says_so() -> None:
    free = find_model(DEFAULT_MODEL_ID)

    assert free is not None
    assert free.is_free
    assert cost_usd(free, 10_000, 5_000) == 0.0


def test_only_a_local_provider_keeps_everything_on_the_machine() -> None:
    ollama = next(p for p in PROVIDERS if p.id is ProviderId.OLLAMA)
    anthropic = next(p for p in PROVIDERS if p.id is ProviderId.ANTHROPIC)

    assert runs_locally(ollama)
    assert not runs_locally(anthropic)
    assert not ollama.needs_key, "a server on this machine has nobody to authenticate to"


def test_the_prices_carry_the_date_they_were_read() -> None:
    """A stale price in the chat footer is a number the app invented."""
    assert PRICES_READ_ON.count("-") == 2
