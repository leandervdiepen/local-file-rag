"""How far the model is from usable. Pure rules, no model."""

from __future__ import annotations

from sidecar.domain.model_readiness import ModelProgress, ModelState


def test_a_fresh_machine_has_no_model_and_no_bar() -> None:
    fresh = ModelProgress()

    assert fresh.state is ModelState.ABSENT
    assert not fresh.usable
    assert fresh.fraction is None


def test_a_download_whose_size_is_not_known_yet_shows_no_bar() -> None:
    """A bar sitting at zero percent says stuck. The total genuinely is not known at the start."""
    starting = ModelProgress(ModelState.DOWNLOADING, bytes_done=0, bytes_total=0)

    assert starting.fraction is None


def test_a_download_in_flight_reports_how_far_it_is() -> None:
    halfway = ModelProgress(ModelState.DOWNLOADING, bytes_done=2_000, bytes_total=4_000)

    assert halfway.fraction == 0.5


def test_a_download_that_overshoots_its_estimate_still_reads_as_complete() -> None:
    """The hub's totals move as files are discovered, and a bar past 100 percent looks broken."""
    over = ModelProgress(ModelState.DOWNLOADING, bytes_done=5_000, bytes_total=4_000)

    assert over.fraction == 1.0


def test_loading_into_memory_is_not_a_download_and_has_no_bar() -> None:
    loading = ModelProgress(ModelState.LOADING)

    assert loading.fraction is None
    assert not loading.usable


def test_only_a_ready_model_is_usable() -> None:
    assert ModelProgress(ModelState.READY).usable
    assert not ModelProgress(ModelState.DOWNLOADING, 1, 2).usable
