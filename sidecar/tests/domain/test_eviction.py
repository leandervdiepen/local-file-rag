"""Which vectors go when the index outgrows its cap. Pure rules, no store."""

from __future__ import annotations

from datetime import UTC, datetime

from sidecar.domain.eviction import PageHeat, coldest_first, pages_to_evict

JANUARY = datetime(2026, 1, 1, tzinfo=UTC)
JUNE = datetime(2026, 6, 1, tzinfo=UTC)
CAP = 1000


def heat(page_id: str, last_hit_at: datetime | None = None, hit_count: int = 0) -> PageHeat:
    return PageHeat(page_id=page_id, last_hit_at=last_hit_at, hit_count=hit_count)


def test_a_store_that_fits_loses_nothing() -> None:
    pages = [heat("p1"), heat("p2")]

    assert pages_to_evict(pages, bytes_on_disk=CAP, cap_bytes=CAP) == []


def test_an_empty_store_loses_nothing_however_the_cap_is_read() -> None:
    assert pages_to_evict([], bytes_on_disk=99_999, cap_bytes=CAP) == []


def test_the_page_nobody_opened_goes_before_the_one_somebody_did() -> None:
    pages = [heat("opened", JUNE), heat("untouched")]

    assert pages_to_evict(pages, bytes_on_disk=1200, cap_bytes=CAP) == ["untouched"]


def test_the_least_recently_hit_goes_first() -> None:
    pages = [heat("recent", JUNE, 1), heat("stale", JANUARY, 1)]

    assert pages_to_evict(pages, bytes_on_disk=1200, cap_bytes=CAP) == ["stale"]


def test_enough_pages_go_to_get_under_the_cap_with_room_to_spare() -> None:
    """Evicting exactly to the line leaves the store one page over it again."""
    pages = [heat(f"p{n}", JANUARY, n) for n in range(10)]

    evicted = pages_to_evict(pages, bytes_on_disk=2000, cap_bytes=CAP)

    per_page = 2000 / 10
    assert (2000 - len(evicted) * per_page) <= CAP * 0.9


def test_two_runs_over_the_same_store_evict_the_same_pages() -> None:
    pages = [heat("b"), heat("a"), heat("c")]

    assert pages_to_evict(pages, 1400, CAP) == pages_to_evict(list(reversed(pages)), 1400, CAP)


def test_fewer_hits_breaks_a_tie_on_the_same_moment() -> None:
    ordered = coldest_first([heat("often", JUNE, 9), heat("once", JUNE, 1)])

    assert [page.page_id for page in ordered] == ["once", "often"]


def test_nothing_is_evicted_that_would_empty_a_store_already_under_its_cap() -> None:
    pages = [heat(f"p{n}") for n in range(100)]

    assert pages_to_evict(pages, bytes_on_disk=CAP - 1, cap_bytes=CAP) == []
