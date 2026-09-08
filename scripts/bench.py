"""Day 2 numbers: what embedding costs, what a page costs to keep, what reranking costs.

Runs against the real model and a real LanceDB directory, because every number
in STATUS.md comes from a run on this machine. Recall belongs to the golden
set runner (D45), not here: this script measures speed and size only.

    uv --directory sidecar run python ../scripts/bench.py --pages 20
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from sidecar.application.search import COLD_PAGE_CAP, STAGE_ONE_CANDIDATE_LIMIT
from sidecar.domain.rerank import rank_by_maxsim
from sidecar.domain.vectors import VECTOR_DIM, PageVectors, QueryVectors
from sidecar.infrastructure.colqwen_embedder import ColQwenEmbedder
from sidecar.infrastructure.image_pages import ImagePageSource
from sidecar.infrastructure.lancedb_vectors import LanceDBVectors
from sidecar.infrastructure.pdfium_pages import PdfiumPageSource

EMBED_LONG_SIDE_PX = 1024
RERANK_PAGES = STAGE_ONE_CANDIDATE_LIMIT
ROWS_PER_PAGE_GUESS = 250


@dataclass
class Bench:
    """Every number this script is allowed to report, with its units in the name."""

    machine: str
    chip: str
    model: str
    dtype: str
    pages: int = 0
    model_load_s: float = 0.0
    seconds_per_page: list[float] = field(default_factory=list)
    warm_seconds_per_page: float = 0.0
    pages_per_second: float = 0.0
    rows_per_page: int = 0
    kb_per_page: float = 0.0
    mb_on_disk_per_1000_pages: float = 0.0
    query_encode_ms: float = 0.0
    rerank_ms_300_pages: float = 0.0
    cold_page_cap_seconds: float = 0.0


def _chip() -> str:
    out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def _corpus_pages(root: Path, wanted: int) -> list[bytes]:
    """Real pages from the demo corpus, rendered the way the indexer renders them."""
    pdfs = PdfiumPageSource()
    images = ImagePageSource()
    out: list[bytes] = []
    for path in sorted(root.rglob("*")):
        if len(out) >= wanted:
            break
        try:
            if path.suffix.lower() == ".pdf":
                for page_no in range(1, min(pdfs.page_count(path), wanted - len(out)) + 1):
                    out.append(pdfs.render(path, page_no, EMBED_LONG_SIDE_PX))
            elif path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                out.append(images.render(path, 1, EMBED_LONG_SIDE_PX))
        except Exception:
            continue
    return out[:wanted]


def _rerank_cost(query_rows: int, pages: int, rows_per_page: int) -> float:
    """Milliseconds to score a full candidate set, on synthetic vectors of the measured shape."""
    rng = np.random.default_rng(0)
    query = QueryVectors(rng.standard_normal((query_rows, VECTOR_DIM)).astype(np.float32))
    corpus = [
        PageVectors(f"p{i}", rng.standard_normal((rows_per_page, VECTOR_DIM)).astype(np.float16), pool_factor=3)
        for i in range(pages)
    ]
    started = time.perf_counter()
    rank_by_maxsim(query, corpus)
    return (time.perf_counter() - started) * 1000


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=Path("~/demo-corpus").expanduser())
    ap.add_argument("--pages", type=int, default=20, help="pages to embed for the speed number")
    ap.add_argument("--out", type=Path, default=None, help="write the numbers as JSON here as well")
    args = ap.parse_args()

    embedder = ColQwenEmbedder()
    bench = Bench(machine=platform.platform(), chip=_chip(), model=embedder.model_id, dtype="float16")

    images = _corpus_pages(args.corpus.expanduser(), args.pages)
    if not images:
        raise SystemExit(f"No renderable pages under {args.corpus}. Run `make corpus` first.")
    bench.pages = len(images)

    started = time.perf_counter()
    first = embedder.embed_pages(["p0"], images[:1])
    bench.model_load_s = time.perf_counter() - started
    bench.seconds_per_page.append(round(bench.model_load_s, 3))

    for index, png in enumerate(images[1:], start=1):
        t0 = time.perf_counter()
        embedder.embed_pages([f"p{index}"], [png])
        bench.seconds_per_page.append(round(time.perf_counter() - t0, 3))

    # The first page pays for the model load and lazy kernel compilation, so it
    # is not the number that transfers to a running index.
    warm = bench.seconds_per_page[1:] or bench.seconds_per_page
    bench.warm_seconds_per_page = round(statistics.median(warm), 3)
    bench.pages_per_second = round(1 / bench.warm_seconds_per_page, 2)
    bench.cold_page_cap_seconds = round(bench.warm_seconds_per_page * COLD_PAGE_CAP, 1)

    bench.rows_per_page = first[0].row_count
    bench.kb_per_page = round(bench.rows_per_page * VECTOR_DIM * 2 / 1024, 1)

    t0 = time.perf_counter()
    query = embedder.embed_query("the slide with the funnel chart")
    bench.query_encode_ms = round((time.perf_counter() - t0) * 1000, 1)

    with tempfile.TemporaryDirectory() as tmp:
        store = LanceDBVectors(Path(tmp))
        store.put_vectors(first)
        size = sum(f.stat().st_size for f in Path(tmp).rglob("*") if f.is_file())
        bench.mb_on_disk_per_1000_pages = round(size * 1000 / 1024 / 1024, 1)

    bench.rerank_ms_300_pages = round(_rerank_cost(query.token_count, RERANK_PAGES, bench.rows_per_page), 1)

    for field_name, value in asdict(bench).items():
        if field_name != "seconds_per_page":
            print(f"{field_name:32} {value}")
    if args.out:
        args.out.write_text(json.dumps(asdict(bench), indent=2) + "\n")


if __name__ == "__main__":
    main()
