"""When the app may spend power on work nobody asked for. Pure rules."""

from __future__ import annotations

from sidecar.domain.idle import Conditions, may_pre_embed, refusal

QUIET = Conditions(on_ac_power=True, idle_seconds=300.0, indexing=False)


def test_a_plugged_in_machine_nobody_is_using_may_pre_embed() -> None:
    assert may_pre_embed(QUIET)
    assert refusal(QUIET) is None


def test_a_machine_on_battery_may_not() -> None:
    """Costing someone their afternoon to make a search they have not run faster."""
    on_battery = Conditions(on_ac_power=False, idle_seconds=300.0, indexing=False)

    assert not may_pre_embed(on_battery)
    assert refusal(on_battery) == "on battery"


def test_a_machine_that_is_crawling_may_not() -> None:
    """Two jobs writing the index at once is the one thing the store cannot take."""
    crawling = Conditions(on_ac_power=True, idle_seconds=300.0, indexing=True)

    assert refusal(crawling) == "a crawl is running"


def test_a_machine_in_use_may_not() -> None:
    in_use = Conditions(on_ac_power=True, idle_seconds=1.0, indexing=False)

    assert refusal(in_use) == "the app is in use"


def test_the_battery_is_the_reason_given_when_more_than_one_applies() -> None:
    """The one the user can act on, and the one that costs them something."""
    everything = Conditions(on_ac_power=False, idle_seconds=0.0, indexing=True)

    assert refusal(everything) == "on battery"


def test_the_idle_threshold_can_be_moved_for_a_test_that_cannot_wait_a_minute() -> None:
    barely_idle = Conditions(on_ac_power=True, idle_seconds=2.0, indexing=False)

    assert not may_pre_embed(barely_idle)
    assert may_pre_embed(barely_idle, idle_after_seconds=1.0)


def test_a_machine_whose_index_is_already_at_its_cap_may_not() -> None:
    """Otherwise pre-embedding and the cap spend the night undoing each other."""
    full = Conditions(on_ac_power=True, idle_seconds=300.0, indexing=False, storage_full=True)

    assert refusal(full) == "the index is at its storage cap"
