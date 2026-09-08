"""Adapter for the `PageEmbedder` port, backed by ColQwen2 through Sentence Transformers.

This is the only file that knows the retrieval model exists. It converts at
the boundary in both directions: PNG bytes in, numpy out, and no torch tensor
or PIL image ever leaves it.
"""

from __future__ import annotations

import io
import logging
import os
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

from sidecar.domain.errors import UnreadableFileError, ValidationError
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors, QueryVectors
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

        images = [_decode(page_id, png) for page_id, png in zip(page_ids, images_png, strict=True)]
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
        rows = self._model.use(lambda model: _to_numpy(model.encode_query([text])[0], np.float32))
        return QueryVectors(rows)

    def is_loaded(self) -> bool:
        return self._model.is_loaded()

    def unload(self) -> None:
        self._model.unload()

    def _encode_batch(self, images: list[Image.Image]) -> list[np.ndarray]:
        return self._model.use(lambda model: self._encode_pooled(model, images))

    def _encode_pooled(self, model: Any, images: list[Image.Image]) -> list[np.ndarray]:
        from sentence_transformers.multi_vector_encoder.modules.token_pooling import HierarchicalTokenPooling

        pooling = HierarchicalTokenPooling(pool_factor=self._pool_factor)
        encoded = model.encode_document(images)
        return [_to_numpy(pooling.pool_one(_as_tensor(page)), STORED_DTYPE) for page in encoded]

    def _load(self) -> Any:
        from sentence_transformers import MultiVectorEncoder

        logger.info("loading %s on %s", self.model_id, self._device)
        # `dtype`, not `torch_dtype`: transformers 5 renamed it and silently
        # ignores the old name, which loads fp32 and doubles resident memory
        # with no error anywhere (D34).
        model = MultiVectorEncoder(self.model_id, device=self._device, model_kwargs={"dtype": torch.float16})
        _assert_float16(model)
        return model

    def _release(self, model: Any) -> None:
        del model
        if self._device == "mps":
            torch.mps.empty_cache()


def _assert_float16(model: Any) -> None:
    """Fail loudly if the weights did not load in the dtype that was asked for.

    The failure this guards is silent: the wrong keyword loads fp32, the model
    still works, and the only symptom is memory and speed. Better a startup
    error than a mystery on a small machine.
    """
    loaded = next((p.dtype for p in model.parameters() if p.is_floating_point()), None)
    if loaded not in (torch.float16, None):
        raise RuntimeError(f"{DEFAULT_MODEL_ID} loaded as {loaded}, not float16. Check the dtype keyword.")


def _decode(page_id: str, png: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(png)) as image:
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableFileError(f"The image for page {page_id} would not decode.") from exc


def _as_tensor(value: Any) -> torch.Tensor:
    return value if isinstance(value, torch.Tensor) else torch.as_tensor(value)


def _to_numpy(value: Any, dtype: Any) -> np.ndarray:
    """A host copy in the dtype the domain stores.

    Encoders hand back tensors on the accelerator, and numpy cannot read those
    without an explicit copy to the CPU.
    """
    tensor = _as_tensor(value).detach().to("cpu", dtype=torch.float32)
    rows: np.ndarray = tensor.numpy().astype(dtype)
    if rows.ndim != 2 or rows.shape[1] != VECTOR_DIM:
        raise RuntimeError(f"The model returned {rows.shape}, which is not a matrix of {VECTOR_DIM}-wide rows.")
    return rows
