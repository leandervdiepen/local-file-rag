"""Adapter for the `PageEmbedder` port, backed by ColQwen2 through Sentence Transformers.

This is the only file that knows the retrieval model exists. It converts at
the boundary in both directions: PNG bytes in, numpy out, and no torch tensor
or PIL image ever leaves it.
"""

from __future__ import annotations

import errno
import logging
import os
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
from PIL import Image

from sidecar.domain.errors import ModelUnavailableError, ValidationError
from sidecar.domain.heatmap import PatchGrid
from sidecar.domain.vectors import STORED_DTYPE, PageVectors, QueryVectors
from sidecar.infrastructure.colqwen_tensors import assert_float16, decode, grid_of, to_numpy
from sidecar.infrastructure.lazy_model import LazyModel

# The Xet download backend stalled at 65 MB of a 4.4 GB file and stayed there,
# so first run goes over plain HTTP (D27). Set before anything imports the hub.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "vidore/colqwen2-v1.0-merged"
DEFAULT_POOL_FACTOR = 3
DEFAULT_IDLE_SECONDS = 600.0

# One encode call holds every image in the batch on the GPU at once, and a
# search may ask for thirty pages. Eight keeps the peak flat without paying
# per-call overhead on every page.
EMBED_BATCH_IMAGES = 8


class ColQwenEmbedder:
    """Turns page images and queries into the vectors MaxSim scores.

    The model loads on the first page anyone asks for and is released after
    ten idle minutes, so a session that never searches never pays for it.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        pool_factor: int = DEFAULT_POOL_FACTOR,
        idle_seconds: float = DEFAULT_IDLE_SECONDS,
        device: str = "mps",
    ) -> None:
        self.model_id = model_id
        self._pool_factor = pool_factor
        self._device = device
        self._model = LazyModel(self._load, self._release, idle_seconds)

    def embed_pages(self, page_ids: Sequence[str], images_png: Sequence[bytes]) -> list[PageVectors]:
        if len(page_ids) != len(images_png):
            raise ValidationError(f"{len(page_ids)} page ids for {len(images_png)} images.")
        if not page_ids:
            return []

        images = [decode(page_id, png) for page_id, png in zip(page_ids, images_png, strict=True)]
        pooled: list[np.ndarray] = []
        for start in range(0, len(images), EMBED_BATCH_IMAGES):
            pooled.extend(self._encode_batch(images[start : start + EMBED_BATCH_IMAGES]))
        return [
            PageVectors(page_id=page_id, vectors=rows, pool_factor=self._pool_factor)
            for page_id, rows in zip(page_ids, pooled, strict=True)
        ]

    def embed_query(self, text: str) -> QueryVectors:
        """Every row the model scores with, including the tokens it adds itself.

        ColQwen2 appends augmentation tokens to a query and uses them in the
        MaxSim sum, so they are returned rather than trimmed: dropping them
        here would silently change the ranking away from what the model was
        trained to produce.
        """
        if not text.strip():
            raise ValidationError("A query has words in it.")
        rows = self._model.use(
            lambda model: to_numpy(model.encode_query([text], show_progress_bar=False)[0], np.float32)
        )
        return QueryVectors(rows)

    def explain_page(self, image_png: bytes) -> tuple[PageVectors, PatchGrid]:
        """The page's patch vectors with no pooling, and where each one sits on the page.

        Pooling merges neighbouring patches, so a stored page has no position
        left to point at and the heatmap has to re-encode. The rows that are
        image patches are picked out by the image token id rather than by a
        fixed offset: the document prompt wraps them in four tokens before and
        seven after, and either could change with the model.
        """
        image = decode("explain", image_png)
        return self._model.use(lambda model: self._explain(model, image))

    def query_tokens(self, text: str) -> tuple[QueryVectors, tuple[str, ...]]:
        """The rows for the words the user typed, with a readable label for each.

        ColQwen2 wraps a query in a "Query:" prefix and pads it with ten more
        tokens, and all sixteen rows go into the ranking. None of them is a
        word anyone typed, so the token picker would offer a list mostly made
        of things the user cannot recognise. Rows and labels are trimmed
        together, so they stay aligned with each other.
        """
        if not text.strip():
            raise ValidationError("A query has words in it.")
        return self._model.use(lambda model: self._query_tokens(model, text))

    def is_loaded(self) -> bool:
        return self._model.is_loaded()

    def unload(self) -> None:
        self._model.unload()

    def _encode_batch(self, images: list[Image.Image]) -> list[np.ndarray]:
        return self._model.use(lambda model: self._encode_pooled(model, images))

    def _encode_pooled(self, model: Any, images: list[Image.Image]) -> list[np.ndarray]:
        from sentence_transformers.multi_vector_encoder.modules.token_pooling import HierarchicalTokenPooling

        pooling = HierarchicalTokenPooling(pool_factor=self._pool_factor)
        # No progress bar: stderr is the sidecar's log, and a bar per page
        # would drown the lines a person is actually meant to read.
        encoded = model.encode_document(images, show_progress_bar=False)
        return [to_numpy(pooling.pool_one(torch.as_tensor(page)), STORED_DTYPE) for page in encoded]

    def _explain(self, model: Any, image: Image.Image) -> tuple[PageVectors, PatchGrid]:
        transformer = model[0]
        features = transformer.preprocess([{"image": image}])
        grid = grid_of(transformer, features)
        rows = to_numpy(model.encode_document([image], show_progress_bar=False)[0], STORED_DTYPE)

        image_token_id = transformer.processor.image_token_id
        is_patch = [token == image_token_id for token in features["input_ids"][0].tolist()]
        patches = rows[np.asarray(is_patch)]
        if patches.shape[0] != grid.patch_count:
            raise RuntimeError(f"{patches.shape[0]} image rows for a {grid.rows}x{grid.cols} grid.")
        return PageVectors(page_id="", vectors=patches, pool_factor=1), grid

    def _query_tokens(self, model: Any, text: str) -> tuple[QueryVectors, tuple[str, ...]]:
        transformer = model[0]
        tokenizer = transformer.processor.tokenizer
        scored_ids = transformer.preprocess([{"text": text}], task="query")["input_ids"][0].tolist()

        rows = to_numpy(model.encode_query([text], show_progress_bar=False)[0], np.float32)
        if len(scored_ids) != rows.shape[0]:
            raise RuntimeError(f"{len(scored_ids)} query tokens for {rows.shape[0]} rows.")

        keep = _typed_positions(tokenizer, scored_ids, text)
        labels = tuple(_readable(tokenizer.convert_ids_to_tokens([scored_ids[i] for i in keep])))
        return QueryVectors(rows[np.asarray(keep)]), labels

    def _load(self) -> Any:
        from sentence_transformers import MultiVectorEncoder

        logger.info("loading %s on %s", self.model_id, self._device)
        try:
            # `dtype`, not `torch_dtype`: transformers 5 renamed it and silently
            # ignores the old name, which loads fp32 and doubles resident memory
            # with no error anywhere (D34).
            model = MultiVectorEncoder(self.model_id, device=self._device, model_kwargs={"dtype": torch.float16})
        except (OSError, ValueError, RuntimeError) as failure:
            raise ModelUnavailableError(_why_the_model_is_missing(failure)) from failure
        assert_float16(model)
        return model

    def _release(self, model: Any) -> None:
        del model
        if self._device == "mps":
            torch.mps.empty_cache()


def _typed_positions(tokenizer: Any, scored_ids: list[int], text: str) -> list[int]:
    """Where the user's own words sit inside the sequence the model scores.

    ColQwen2 wraps a query as "Query: <text>" and pads it, so the rows are the
    prefix, the words, then padding. The span is found by decoding rather than
    by counting tokens off the front: the same word tokenizes differently at
    the start of a string and after a space, so matching ids against a plain
    tokenization of the same text finds nothing.

    Falls back to every non-special row if the template ever stops containing
    the text verbatim, because a heatmap over too many tokens is recoverable
    and one over the wrong tokens is not.
    """
    special = set(tokenizer.all_special_ids)
    kept = [index for index, token_id in enumerate(scored_ids) if token_id not in special]
    wanted = text.strip()
    for start in range(len(kept)):
        span = kept[start:]
        if tokenizer.decode([scored_ids[i] for i in span]).strip() == wanted:
            return span
    return kept


def _readable(tokens: list[str]) -> list[str]:
    """Tokenizer pieces as the words they came from. The leading marker is a space, not a letter."""
    return [token.replace("\u0120", " ").strip() or token for token in tokens]


# First run fetches about four gigabytes, and the two ways that fails are the
# two the user can act on. Anything else keeps the library's own words, because
# inventing a cause would send them to fix the wrong thing.
_NO_SPACE = "There is not enough disk space for the search model. It needs about 5 GB free. Free some up and try again."
_NO_NETWORK = (
    "The search model could not be downloaded. Check your connection and try again. "
    "It is about 4 GB and is downloaded once."
)


def _why_the_model_is_missing(failure: Exception) -> str:
    if isinstance(failure, OSError) and failure.errno == errno.ENOSPC:
        return _NO_SPACE
    words = str(failure).lower()
    if any(mark in words for mark in ("no space", "disk full", "quota exceeded")):
        return _NO_SPACE
    if any(mark in words for mark in ("connection", "network", "timed out", "resolve", "offline", "unreachable")):
        return _NO_NETWORK
    return f"The search model would not load. {failure}"
