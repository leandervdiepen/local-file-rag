"""`LanceDBVectors` against a real database directory, through the port and nothing else."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sidecar.domain.vectors import VECTOR_DIM, PageVectors, QueryVectors
from sidecar.infrastructure.lancedb_vectors import LanceDBVectors
from tests.fakes.page_embedder import feature_vector

pytestmark = pytest.mark.integration

POOL_FACTOR = 3


def a_page(page_id: str, *words: str) -> PageVectors:
    """A page whose patches carry one feature vector per word."""
    rows = np.stack([feature_vector(word) for word in words]).astype(np.float16)
    return PageVectors(page_id=page_id, vectors=rows, pool_factor=POOL_FACTOR)


def a_query(*words: str) -> QueryVectors:
    return QueryVectors(np.stack([feature_vector(word) for word in words]))


def test_a_fresh_directory_is_a_usable_empty_store(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")

    assert store.count() == 0
    assert store.get_vectors(["a:1"]) == {}
    assert store.embedded_ids(["a:1"]) == set()
    assert store.nearest(a_query("funnel"), 5) == []


def test_vectors_round_trip_with_their_shape_dtype_and_pool_factor(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")
    written = a_page("a:1", "funnel", "chart", "revenue")

    store.put_vectors([written])

    read = store.get_vectors(["a:1"])["a:1"]
    assert read.page_id == "a:1"
    assert read.pool_factor == POOL_FACTOR
    assert read.vectors.shape == (3, VECTOR_DIM)
    assert read.vectors.dtype == np.float16
    assert np.allclose(read.vectors, written.vectors)


def test_writing_the_same_page_twice_is_one_row_and_the_second_write_wins(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")

    store.put_vectors([a_page("a:1", "funnel")])
    store.put_vectors([a_page("a:1", "table", "grid")])

    assert store.count() == 1
    assert store.get_vectors(["a:1"])["a:1"].vectors.shape == (2, VECTOR_DIM)


def test_an_empty_write_touches_nothing(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")

    store.put_vectors([])

    assert store.count() == 0


def test_embedded_ids_reports_only_the_pages_that_have_vectors(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")
    store.put_vectors([a_page("a:1", "funnel"), a_page("a:2", "chart")])

    assert store.embedded_ids(["a:1", "a:2", "b:9"]) == {"a:1", "a:2"}
    assert store.embedded_ids([]) == set()
    assert store.embedded_ids(["b:9"]) == set()


def test_nearest_puts_the_page_that_matches_the_query_first(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")
    store.put_vectors([a_page("miss:1", "table", "grid"), a_page("hit:1", "funnel", "chart")])

    ranked = store.nearest(a_query("funnel", "chart"), 5)

    assert [page_id for page_id, _ in ranked] == ["hit:1", "miss:1"]
    assert ranked[0][1] > ranked[1][1], "the port promises higher is better"


def test_nearest_returns_what_there_is_when_the_store_is_smaller_than_the_limit(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db")
    store.put_vectors([a_page("a:1", "funnel")])

    assert len(store.nearest(a_query("funnel"), 20)) == 1


def a_bulk_page(page_id: str, rows: int, seed: int) -> PageVectors:
    """A page of `rows` arbitrary unit vectors, for filling a table to the index threshold."""
    rng = np.random.default_rng(seed)
    vectors = rng.standard_normal((rows, VECTOR_DIM)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return PageVectors(page_id=page_id, vectors=vectors.astype(np.float16), pool_factor=POOL_FACTOR)


def test_the_index_is_built_once_the_table_is_big_enough_and_search_still_works(tmp_path: Path) -> None:
    store = LanceDBVectors(tmp_path / "db", index_threshold_rows=4)
    store.put_vectors([a_bulk_page(f"bulk:{n}", 250, seed=n) for n in range(3)])
    assert store._has_index(store._existing_table()) is False, "three pages is below the threshold of four"

    store.put_vectors([a_page("hit:1", "funnel", "chart")])

    assert store._has_index(store._existing_table()) is True
    assert store.nearest(a_query("funnel", "chart"), 3)[0][0] == "hit:1"
