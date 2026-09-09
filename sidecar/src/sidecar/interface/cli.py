"""Command-line entry point for the sidecar process."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sidecar.application.search import VISUAL_CANDIDATE_LIMIT
from sidecar.domain.eviction import DEFAULT_CAP_BYTES
from sidecar.infrastructure.colqwen_embedder import DEFAULT_POOL_FACTOR
from sidecar.interface.composition import build_app
from sidecar.interface.serve import serve

DEFAULT_DB_PATH = Path.home() / "Library" / "Application Support" / "local-file-rag" / "db"


def _configure_logging() -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sidecar", description="Local file search sidecar")
    parser.add_argument("--port", type=int, default=0, help="Port to bind, 0 picks a free one")
    parser.add_argument("--token", type=str, required=True, help="Bearer token every request must present")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Directory the index database lives in")
    parser.add_argument(
        "--pool-factor",
        type=int,
        default=DEFAULT_POOL_FACTOR,
        help="How hard a page's patch vectors are pooled before storage. Changing it needs a re-index",
    )
    parser.add_argument(
        "--visual-candidates",
        type=int,
        default=VISUAL_CANDIDATE_LIMIT,
        help="How many pages the vector search adds to every query's candidate set",
    )
    parser.add_argument(
        "--cap-bytes",
        type=int,
        default=DEFAULT_CAP_BYTES,
        help="Disk the page vectors may use before the least recently opened are evicted",
    )
    return parser.parse_args(argv)


def main() -> None:
    _configure_logging()
    args = parse_args()
    app = build_app(
        token=args.token,
        db_path=args.db,
        cap_bytes=args.cap_bytes,
        visual_candidates=args.visual_candidates,
        pool_factor=args.pool_factor,
    )
    serve(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
