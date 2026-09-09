"""Reading OpenRouter's model list, against rows shaped like the live ones."""

from __future__ import annotations

import pytest

from sidecar.domain.providers import PROVIDERS, ProviderId
from sidecar.infrastructure.openrouter_catalogue import _offered

pytestmark = pytest.mark.integration

OPENROUTER = next(p for p in PROVIDERS if p.id is ProviderId.OPENROUTER)


def a_row(**over: object) -> dict:
    row = {
        "id": "vendor/model",
        "name": "Vendor: Model",
        "context_length": 128_000,
        "pricing": {"prompt": "0.00000075", "completion": "0.00000375"},
        "architecture": {"input_modalities": ["text", "image"]},
    }
    row.update(over)
    return row


def test_a_price_per_token_becomes_a_price_per_million() -> None:
    model = _offered(OPENROUTER, a_row())

    assert model.usd_per_m_input == pytest.approx(0.75)
    assert model.usd_per_m_output == pytest.approx(3.75)


def test_a_model_that_takes_images_says_so() -> None:
    assert _offered(OPENROUTER, a_row()).sees_images is True


def test_a_text_only_model_says_so_rather_than_leaving_it_open() -> None:
    model = _offered(OPENROUTER, a_row(architecture={"input_modalities": ["text"]}))

    assert model.sees_images is False


def test_a_router_whose_price_varies_reads_as_unknown_not_as_minus_a_million() -> None:
    """`openrouter/auto` reports -1 per token. Measured against the live API 2026-09-09."""
    model = _offered(OPENROUTER, a_row(pricing={"prompt": "-1", "completion": "-1"}))

    assert not model.price_known
    assert not model.is_free


def test_a_free_model_is_free_rather_than_unknown() -> None:
    model = _offered(OPENROUTER, a_row(pricing={"prompt": "0", "completion": "0"}))

    assert model.is_free


def test_a_row_missing_its_price_is_unknown() -> None:
    model = _offered(OPENROUTER, a_row(pricing={}))

    assert not model.price_known


def test_a_row_missing_its_architecture_leaves_the_modality_unstated() -> None:
    model = _offered(OPENROUTER, a_row(architecture={}))

    assert model.sees_images is False, "an empty modality list is a claim that it takes no images"


def test_the_display_name_is_preferred_over_the_id() -> None:
    assert _offered(OPENROUTER, a_row()).label == "Vendor: Model"
