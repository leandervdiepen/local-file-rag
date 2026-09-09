"""What each provider offers, asked of the provider and cached briefly."""

from __future__ import annotations

import pytest

from sidecar.application.list_models import ListModels
from sidecar.application.provider_keys import ProviderKeys
from sidecar.domain.catalogue import OfferedModel
from sidecar.domain.errors import AnswerUnavailableError, NotFoundError
from sidecar.domain.providers import ProviderId
from tests.fakes.model_catalogue import FakeModelCatalogue


class Ticking:
    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds


def a_model(model_id: str, sees: bool | None = True, price: float | None = 1.0) -> OfferedModel:
    return OfferedModel(ProviderId.OPENROUTER, model_id, model_id, sees, price, price)


def a_use_case(
    catalogue: FakeModelCatalogue, keys: ProviderKeys | None = None, clock: Ticking | None = None
) -> tuple[ListModels, ProviderKeys, Ticking]:
    keys = keys or ProviderKeys()
    clock = clock or Ticking()
    return ListModels(keys, {ProviderId.OPENROUTER: catalogue}, clock, cache_seconds=60.0), keys, clock


def test_only_providers_with_a_catalogue_behind_them_are_listed() -> None:
    use_case, _, _ = a_use_case(FakeModelCatalogue())

    assert [row.provider.id for row in use_case.providers()] == [ProviderId.OPENROUTER]


def test_a_provider_says_whether_it_has_a_key_yet() -> None:
    use_case, keys, _ = a_use_case(FakeModelCatalogue())
    assert use_case.providers()[0].has_key is False

    keys.remember(ProviderId.OPENROUTER, "sk-or")

    assert use_case.providers()[0].has_key is True


def test_a_model_that_cannot_see_is_never_offered() -> None:
    """D37: a text-only model answers a question about a chart from the question alone."""
    use_case, _, _ = a_use_case(FakeModelCatalogue([a_model("blind", sees=False), a_model("sighted")]))

    assert [model.id for model in use_case.models_for("openrouter")] == ["sighted"]


def test_a_model_whose_provider_will_not_say_is_still_offered() -> None:
    """Refusing everything a vendor is quiet about leaves OpenAI with an empty list."""
    use_case, _, _ = a_use_case(FakeModelCatalogue([a_model("quiet", sees=None)]))

    assert [model.id for model in use_case.models_for("openrouter")] == ["quiet"]


def test_the_cheapest_known_price_comes_first_and_the_unpriced_come_last() -> None:
    use_case, _, _ = a_use_case(
        FakeModelCatalogue([a_model("unpriced", price=None), a_model("dear", price=9.0), a_model("cheap", price=0.0)])
    )

    assert [model.id for model in use_case.models_for("openrouter")] == ["cheap", "dear", "unpriced"]


def test_asking_twice_in_a_minute_asks_the_provider_once() -> None:
    catalogue = FakeModelCatalogue([a_model("m")])
    use_case, _, clock = a_use_case(catalogue)

    use_case.models_for("openrouter")
    clock.seconds += 30
    use_case.models_for("openrouter")

    assert len(catalogue.asked_with) == 1


def test_the_list_is_asked_for_again_once_it_is_stale() -> None:
    catalogue = FakeModelCatalogue([a_model("m")])
    use_case, _, clock = a_use_case(catalogue)

    use_case.models_for("openrouter")
    clock.seconds += 120
    use_case.models_for("openrouter")

    assert len(catalogue.asked_with) == 2


def test_adding_a_key_shows_what_it_unlocked_without_waiting_for_the_cache() -> None:
    catalogue = FakeModelCatalogue([a_model("m")])
    use_case, keys, _ = a_use_case(catalogue)
    use_case.models_for("openrouter")

    keys.remember(ProviderId.OPENROUTER, "sk-or")
    use_case.models_for("openrouter")

    assert catalogue.asked_with == [None, "sk-or"]


def test_a_provider_this_app_does_not_know_is_not_found() -> None:
    use_case, _, _ = a_use_case(FakeModelCatalogue())

    with pytest.raises(NotFoundError):
        use_case.models_for("hotdog")


def test_a_provider_that_cannot_be_reached_says_so_rather_than_answering_empty() -> None:
    catalogue = FakeModelCatalogue([a_model("m")])
    catalogue.unreachable = True
    use_case, _, _ = a_use_case(catalogue)

    with pytest.raises(AnswerUnavailableError):
        use_case.models_for("openrouter")


def test_pricing_a_finished_answer_never_fails_it() -> None:
    """A provider that went away must not turn an answer the user already has into an error."""
    catalogue = FakeModelCatalogue([a_model("m")])
    catalogue.unreachable = True
    use_case, _, _ = a_use_case(catalogue)

    assert use_case.price_for("openrouter", "m") is None


def test_a_priced_model_can_be_looked_up_after_the_answer() -> None:
    use_case, _, _ = a_use_case(FakeModelCatalogue([a_model("m", price=2.0)]))

    found = use_case.price_for("openrouter", "m")

    assert found is not None
    assert found.usd_per_m_input == 2.0
