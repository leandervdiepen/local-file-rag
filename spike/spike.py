"""Day 0 spike: is ColQwen2 on MPS fast enough, and small enough, to build on.

Answers four questions and nothing else:
  1. How long does the model take to load, and how much memory does it hold.
  2. How many seconds does one rendered page take to embed.
  3. How many vectors survive pooling, and what does a page cost on disk.
  4. Does MaxSim pick the right page when the query has no matching words.

Sweeps model and dtype because the answers differ enough between them to
change what ships. Fails loudly rather than degrading, because a soft pass
here costs day 2.
"""

from __future__ import annotations

import argparse
import json
import resource
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import psutil
import pypdfium2 as pdfium
import torch
from PIL import Image, ImageDraw

RENDER_LONG_SIDE = 1024
PAGE_SIZE = (1240, 1754)  # A4 at 150 dpi, portrait
TARGET_PAGE = 2  # the red dialog, findable only by what it looks like

# transformers renamed torch_dtype to dtype. Passing the old name is silently
# ignored, which loads fp32 weights and doubles resident memory.
DTYPES = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}


@dataclass
class Result:
    """Every number the spike is allowed to report, with its units in the name."""

    model: str
    dtype: str
    torch_version: str = torch.__version__
    model_load_s: float = 0.0
    seconds_per_page: list[float] = field(default_factory=list)
    warm_seconds_per_page: float = 0.0
    vectors_per_page: int = 0
    vector_dim: int = 0
    pooled_vectors_per_page: int = 0
    kb_per_page_float16: float = 0.0
    rss_after_load_gb: float = 0.0
    peak_rss_gb: float = 0.0
    query_ms: float = 0.0
    query_tokens: int = 0
    maxsim_winner: int = -1
    maxsim_scores: list[float] = field(default_factory=list)
    speed_gate: bool = False
    pick_gate: bool = False


def to_numpy(v: object) -> np.ndarray:
    """Encoders hand back MPS tensors, which numpy cannot read without a host copy."""
    if isinstance(v, torch.Tensor):
        return v.detach().to("cpu", dtype=torch.float32).numpy()
    return np.asarray(v, dtype=np.float32)


def peak_rss_gb() -> float:
    """macOS reports ru_maxrss in bytes, unlike Linux which reports kilobytes."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3


def rss_gb() -> float:
    return psutil.Process().memory_info().rss / 1024**3


def draw_pages(out: Path) -> Path:
    """Three visually distinct pages, saved as a real PDF so pypdfium2 renders them.

    Page 2 is the target: a red error dialog whose meaning is entirely visual.
    The word "error" appears on page 1 as a decoy so a text match cannot win by accident.
    """
    pages = []

    p1 = Image.new("RGB", PAGE_SIZE, "white")
    d = ImageDraw.Draw(p1)
    d.text((90, 120), "Quarterly revenue by region", fill="black")
    d.text((90, 170), "No error occurred during the reporting period.", fill="black")
    for i, h in enumerate([300, 520, 410, 680, 250]):
        d.rectangle([120 + i * 190, 1200 - h, 260 + i * 190, 1200], fill="black")
    pages.append(p1)

    p2 = Image.new("RGB", PAGE_SIZE, "white")
    d = ImageDraw.Draw(p2)
    d.rectangle([180, 600, 1060, 1100], outline="#c0392b", width=8)
    d.rectangle([180, 600, 1060, 700], fill="#c0392b")
    d.text((220, 800), "Webhook delivery failed", fill="#c0392b")
    d.text((220, 860), "POST /v1/webhooks/stripe returned 500", fill="black")
    pages.append(p2)

    p3 = Image.new("RGB", PAGE_SIZE, "white")
    d = ImageDraw.Draw(p3)
    d.text((90, 120), "Onboarding checklist", fill="black")
    for i in range(18):
        d.text((90, 220 + i * 46), f"Step {i + 1}: configure the workspace", fill="black")
    pages.append(p3)

    pdf_path = out / "spike.pdf"
    pages[0].save(pdf_path, save_all=True, append_images=pages[1:], resolution=150.0)
    return pdf_path


def render(pdf_path: Path) -> list[Image.Image]:
    """Render at the resolution the real indexer will use, so the timing transfers."""
    doc = pdfium.PdfDocument(pdf_path)
    out = []
    for page in doc:
        scale = RENDER_LONG_SIDE / max(page.get_size())
        out.append(page.render(scale=scale).to_pil().convert("RGB"))
    return out


def measure(model_id: str, dtype_name: str, images: list[Image.Image], query: str, pool_factor: int) -> Result:
    from sentence_transformers import MultiVectorEncoder
    from sentence_transformers.multi_vector_encoder.modules.token_pooling import HierarchicalTokenPooling

    r = Result(model=model_id, dtype=dtype_name)

    t0 = time.perf_counter()
    model = MultiVectorEncoder(model_id, device="mps", model_kwargs={"dtype": DTYPES[dtype_name]})
    r.model_load_s = time.perf_counter() - t0
    r.rss_after_load_gb = rss_gb()

    doc_vecs = []
    for img in images:
        t0 = time.perf_counter()
        v = model.encode_document([img])[0]
        r.seconds_per_page.append(round(time.perf_counter() - t0, 3))
        doc_vecs.append(to_numpy(v))

    # The first page pays for lazy kernel compilation, so it is not the number that transfers.
    warm = r.seconds_per_page[1:]
    r.warm_seconds_per_page = sum(warm) / len(warm)
    r.vectors_per_page, r.vector_dim = (int(x) for x in doc_vecs[0].shape)

    # Pooling is a pipeline module rather than an encode kwarg, so the real embedder
    # will hold two configurations: pooled for storage, unpooled for heatmaps.
    pooled = HierarchicalTokenPooling(pool_factor=pool_factor).pool_one(torch.from_numpy(doc_vecs[0]))
    r.pooled_vectors_per_page = int(to_numpy(pooled).shape[0])
    r.kb_per_page_float16 = r.pooled_vectors_per_page * r.vector_dim * 2 / 1024

    t0 = time.perf_counter()
    q = to_numpy(model.encode_query([query])[0])
    r.query_ms = (time.perf_counter() - t0) * 1000
    r.query_tokens = int(q.shape[0])

    # MaxSim: for every query token take its best matching page patch, then sum.
    r.maxsim_scores = [round(float((d @ q.T).max(axis=0).sum()), 2) for d in doc_vecs]
    r.maxsim_winner = int(np.argmax(r.maxsim_scores)) + 1
    r.peak_rss_gb = peak_rss_gb()
    r.speed_gate = r.warm_seconds_per_page < 3.0
    r.pick_gate = r.maxsim_winner == TARGET_PAGE

    del model
    torch.mps.empty_cache()
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out", help="where to write pages and results")
    ap.add_argument("--model", action="append", help="repeatable, defaults to the adapter build")
    ap.add_argument("--dtype", action="append", choices=list(DTYPES), help="repeatable, defaults to float32")
    ap.add_argument("--pool-factor", type=int, default=3, help="hierarchical token pooling factor, per D09")
    ap.add_argument("--query", default="the screenshot of the red error dialog", help="a query with no words on the target page")
    args = ap.parse_args()

    models = args.model or ["vidore/colqwen2-v1.0"]
    dtypes = args.dtype or ["float32"]

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"torch {torch.__version__}  mps={torch.backends.mps.is_available()}")
    if not torch.backends.mps.is_available():
        raise SystemExit("MPS not available. The whole plan assumes it.")

    images = render(draw_pages(args.out))
    print(f"rendered {len(images)} pages at {images[0].size}\n")

    results = []
    for model_id in models:
        for dtype_name in dtypes:
            print(f"---- {model_id}  {dtype_name} ----", flush=True)
            r = measure(model_id, dtype_name, images, args.query, args.pool_factor)
            results.append(r)
            print(
                f"  load {r.model_load_s:.1f}s   warm {r.warm_seconds_per_page:.2f}s/page   "
                f"rss {r.rss_after_load_gb:.1f}GB   peak {r.peak_rss_gb:.1f}GB"
            )
            print(
                f"  {r.vectors_per_page}x{r.vector_dim} -> {r.pooled_vectors_per_page} pooled, "
                f"{r.kb_per_page_float16:.0f} KB   scores {r.maxsim_scores} winner {r.maxsim_winner}",
                flush=True,
            )

    (args.out / "spike.json").write_text(json.dumps([asdict(r) for r in results], indent=2))

    print(f"\n{'model':36} {'dtype':9} {'s/page':>7} {'rss GB':>7} {'KB/pg':>6}  gates")
    for r in results:
        gates = "PASS" if (r.speed_gate and r.pick_gate) else "FAIL"
        print(
            f"{r.model:36} {r.dtype:9} {r.warm_seconds_per_page:7.2f} {r.rss_after_load_gb:7.1f} "
            f"{r.kb_per_page_float16:6.0f}  {gates}"
        )

    raise SystemExit(0 if all(r.speed_gate and r.pick_gate for r in results) else 1)


if __name__ == "__main__":
    main()
