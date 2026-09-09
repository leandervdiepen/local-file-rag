"""What a provider says it can offer. Pure rules, no provider."""

from __future__ import annotations

from sidecar.domain.catalogue import OfferedModel, can_answer, cost_usd, offerable
from sidecar.domain.providers import ProviderId


def a_model(
    model_id: str, sees: bool | None = True, price_in: float | None = 1.0, price_out: float | None = 1.0
) -> OfferedModel:
    return OfferedModel(ProviderId.OPENROUTER, model_id, model_id, sees, price_in, price_out)


def test_a_model_that_cannot_see_may_not_be_offered() -> None:
    """D37: a text-only model answers a question about a chart from the question alone."""
    assert not can_answer(a_model("blind", sees=False))


def test_a_model_whose_provider_will_not_say_is_still_offered() -> None:
    """Refusing everything a vendor is quiet about leaves OpenAI with an empty list."""
    assert can_answer(a_model("quiet", sees=None))


def test_a_price_nobody_published_is_not_a_price_of_zero() -> None:
    unpriced = a_model("m", price_in=None, price_out=None)

    assert not unpriced.price_known
    assert not unpriced.is_free
    assert cost_usd(unpriced, 1_000_000, 1_000_000) is None


def test_a_model_that_charges_nothing_says_so_and_costs_nothing() -> None:
    free = a_model("m", price_in=0.0, price_out=0.0)

    assert free.price_known
    assert free.is_free
    assert cost_usd(free, 1_000_000, 1_000_000) == 0.0


def test_a_price_is_per_million_tokens_of_each_kind() -> None:
    model = a_model("m", price_in=2.0, price_out=10.0)

    assert cost_usd(model, 1_000_000, 0) == 2.0
    assert cost_usd(model, 0, 1_000_000) == 10.0


def test_the_cheapest_comes_first_and_the_unpriced_come_last() -> None:
    ordered = offerable(
        [a_model("unpriced", price_in=None), a_model("dear", price_in=9.0), a_model("cheap", price_in=0.0)]
    )

    assert [model.id for model in ordered] == ["cheap", "dear", "unpriced"]


def test_the_blind_are_dropped_rather_than_sorted() -> None:
    ordered = offerable([a_model("blind", sees=False, price_in=0.0), a_model("seer", price_in=5.0)])

    assert [model.id for model in ordered] == ["seer"]


def test_two_models_at_the_same_price_keep_a_stable_order() -> None:
    ordered = offerable([a_model("b", price_in=1.0), a_model("a", price_in=1.0)])

    assert [model.id for model in ordered] == ["a", "b"]
