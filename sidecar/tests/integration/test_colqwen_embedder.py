"""`ColQwenEmbedder` against the real model. Slow: it loads about 4 GB of weights.

Marked slow and integration, so `make check` and `make check-int` both skip it.
Run it with: uv --directory sidecar run pytest -m slow -q -s
"""

from __future__ import annotations

import io
import time

import numpy as np
import pytest
from PIL import Image, ImageDraw

from sidecar.domain.errors import UnreadableFileError, ValidationError
from sidecar.domain.rerank import maxsim
from sidecar.domain.vectors import VECTOR_DIM
from sidecar.infrastructure.colqwen_embedder import ColQwenEmbedder

pytestmark = [pytest.mark.slow, pytest.mark.integration]

PAGE_SIZE = (1024, 1448)


def a_page_png(lines: list[str], red_box: bool = False) -> bytes:
    """A page drawn at the resolution the indexer embeds at."""
    page = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(page)
    if red_box:
        draw.rectangle([120, 400, 900, 800], outline="#c0392b", width=10)
        draw.rectangle([120, 400, 900, 470], fill="#c0392b")
    for index, line in enumerate(lines):
        draw.text((140, 520 + index * 40), line, fill="black")
    buffer = io.BytesIO()
    page.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(scope="module")
def embedder() -> ColQwenEmbedder:
    return ColQwenEmbedder()


def test_a_page_embeds_to_pooled_float16_patch_vectors(embedder: ColQwenEmbedder) -> None:
    started = time.perf_counter()
    [page] = embedder.embed_pages(["a:1"], [a_page_png(["Quarterly revenue by region"])])
    load_and_first_page = time.perf_counter() - started

    assert page.page_id == "a:1"
    assert page.vectors.dtype == np.float16
    assert page.vectors.shape[1] == VECTOR_DIM
    assert page.row_count > 10
    assert page.pool_factor == 3
    print(f"\nload plus first page: {load_and_first_page:.1f}s, {page.row_count} pooled rows")


def test_a_warm_page_costs_what_the_plan_budgeted(embedder: ColQwenEmbedder) -> None:
    embedder.embed_pages(["warm:0"], [a_page_png(["warm up"])])

    started = time.perf_counter()
    embedder.embed_pages(["warm:1"], [a_page_png(["Onboarding checklist"])])
    seconds = time.perf_counter() - started

    print(f"\nwarm seconds per page: {seconds:.2f}")
    assert seconds < 3.0, "the day 0 gate was three seconds a page"


def test_a_batch_comes_back_in_the_order_it_was_given(embedder: ColQwenEmbedder) -> None:
    ids = [f"batch:{n}" for n in range(3)]

    pages = embedder.embed_pages(ids, [a_page_png([f"page {n}"]) for n in range(3)])

    assert [page.page_id for page in pages] == ids


def test_a_query_embeds_to_float32_rows(embedder: ColQwenEmbedder) -> None:
    started = time.perf_counter()
    query = embedder.embed_query("the screenshot of the red error dialog")
    ms = (time.perf_counter() - started) * 1000

    assert query.vectors.dtype == np.float32
    assert query.vectors.shape[1] == VECTOR_DIM
    assert query.token_count > 1
    print(f"\nquery encode: {ms:.0f} ms, {query.token_count} rows")


def test_maxsim_picks_the_page_that_looks_right_when_no_word_matches(embedder: ColQwenEmbedder) -> None:
    """The whole product in one assertion: retrieval by what a page looks like."""
    decoy = a_page_png(["Quarterly revenue by region", "No error occurred this period."])
    target = a_page_png(["Webhook delivery failed", "POST /v1/webhooks returned 500"], red_box=True)
    checklist = a_page_png([f"Step {n}: configure the workspace" for n in range(1, 8)])

    pages = embedder.embed_pages(["decoy:1", "target:1", "checklist:1"], [decoy, target, checklist])
    query = embedder.embed_query("the screenshot of the red error dialog")

    scores = {page.page_id: maxsim(query, page) for page in pages}
    print(f"\nmaxsim: {scores}")
    assert max(scores, key=lambda page_id: scores[page_id]) == "target:1"


def test_an_empty_ask_never_loads_the_model() -> None:
    cold = ColQwenEmbedder()

    assert cold.embed_pages([], []) == []
    assert not cold.is_loaded()


def test_a_blank_query_is_refused_before_the_model_is_touched() -> None:
    cold = ColQwenEmbedder()

    with pytest.raises(ValidationError):
        cold.embed_query("   ")
    assert not cold.is_loaded()


def test_mismatched_inputs_are_refused(embedder: ColQwenEmbedder) -> None:
    with pytest.raises(ValidationError):
        embedder.embed_pages(["a:1", "a:2"], [a_page_png(["one"])])


def test_bytes_that_are_not_an_image_name_the_page_that_failed(embedder: ColQwenEmbedder) -> None:
    with pytest.raises(UnreadableFileError, match="bad:1"):
        embedder.embed_pages(["bad:1"], [b"this is not a png"])


def test_the_model_loads_on_demand_and_lets_go_when_told(embedder: ColQwenEmbedder) -> None:
    embedder.embed_pages(["cycle:1"], [a_page_png(["anything"])])
    assert embedder.is_loaded()

    embedder.unload()
    assert not embedder.is_loaded()

    embedder.unload()
    assert embedder.embed_query("still works after a release").token_count > 1
