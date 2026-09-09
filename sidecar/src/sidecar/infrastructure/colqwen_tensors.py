"""Converting between what the model speaks and what the domain stores.

Kept apart from the adapter so that file is the contract and this one is the
plumbing: torch tensors, PIL images and the processor's grid arithmetic all
stop here.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

from sidecar.domain.errors import UnreadableFileError
from sidecar.domain.heatmap import PatchGrid
from sidecar.domain.vectors import VECTOR_DIM


def assert_float16(model: Any) -> None:
    """Fail loudly if the weights did not load in the dtype that was asked for.

    The failure this guards is silent: the wrong keyword loads fp32, the model
    still works, and the only symptom is memory and speed. Better an error at
    startup than a mystery on a small machine.
    """
    loaded = next((p.dtype for p in model.parameters() if p.is_floating_point()), None)
    if loaded not in (torch.float16, None):
        raise RuntimeError(f"The model loaded as {loaded}, not float16. Check the dtype keyword.")


def grid_of(transformer: Any, features: Any) -> PatchGrid:
    """Rows and columns of patches after the processor's spatial merge.

    `image_grid_thw` counts patches before the merge, and Qwen2-VL merges a
    2x2 block into one token, so the grid the vectors lie on is half each way.
    """
    _, height, width = (int(n) for n in features["image_grid_thw"][0].tolist())
    merge = int(transformer.processor.image_processor.merge_size)
    return PatchGrid(rows=height // merge, cols=width // merge)


def decode(page_id: str, png: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(png)) as image:
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableFileError(f"The image for page {page_id} would not decode.") from exc


def to_numpy(value: Any, dtype: Any) -> np.ndarray:
    """A host copy in the dtype the domain stores.

    Encoders hand back tensors on the accelerator, and numpy cannot read those
    without an explicit copy to the CPU.
    """
    tensor = value if isinstance(value, torch.Tensor) else torch.as_tensor(value)
    rows: np.ndarray = tensor.detach().to("cpu", dtype=torch.float32).numpy().astype(dtype)
    if rows.ndim != 2 or rows.shape[1] != VECTOR_DIM:
        raise RuntimeError(f"The model returned {rows.shape}, which is not a matrix of {VECTOR_DIM}-wide rows.")
    return rows
