#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Runs the golden set through a running sidecar and writes one eval run directory.

Exit code 1 when a query that hit at 5 in the previous run misses now, 0 when
nothing regressed, 2 when the run could not complete. A day gate reads the code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_report import render_report  # noqa: E402
from eval_runs import RunDir, latest_run, mark_latest, regressions, run_id_for  # noqa: E402

GOLDEN_FIELDS = ("id", "query", "expected_file", "expected_page", "text_free", "match_channel")
# The same derivation as sidecar/src/sidecar/domain/identity.py: blake2b over the absolute path, 16 bytes.
FILE_ID_BYTES = 16
SCRIPTS_DIR = Path(__file__).resolve().parent


class Sidecar:
    """The three calls this script makes, over urllib so the script carries no dependencies."""

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    def get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(self._request(path)) as response:
            loaded: dict[str, Any] = json.load(response)
            return loaded

    def get_bytes(self, path: str) -> bytes | None:
        try:
            with urllib.request.urlopen(self._request(path)) as response:
                return bytes(response.read())
        except urllib.error.HTTPError:
            return None

    def stream(self, path: str, body: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
        """Named SSE events as (name, payload), in order, until the server closes the stream."""
        request = self._request(path, json.dumps(body).encode("utf-8"))
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request) as response:
            fields: dict[str, str] = {}
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip("\n")
                if line:
                    name, _, value = line.partition(": ")
                    fields[name] = value
                elif fields:
                    yield fields["event"], json.loads(fields["data"])
                    fields = {}

    def _request(self, path: str, data: bytes | None = None) -> urllib.request.Request:
        return urllib.request.Request(self._base_url + path, data=data, headers=self._headers)


def read_golden(path: Path) -> list[dict[str, Any]]:
    """The rows as the wire contract wants them: the six fields, nothing a row carries beyond them."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [{field: row[field] for field in GOLDEN_FIELDS} for row in rows]


def page_id_of(corpus_root: Path, relative_file: str, page_no: int) -> str:
    file_id = hashlib.blake2b(str(corpus_root / relative_file).encode("utf-8"), digest_size=FILE_ID_BYTES).hexdigest()
    return f"{file_id}:{page_no}"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_identity() -> tuple[str, bool]:
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
    return sha, bool(status.strip())


def machine() -> str:
    chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
    return f"{platform.platform()} {chip.stdout.strip()}".strip()


def corpus_identity(corpus_root: Path) -> tuple[int | None, str | None]:
    manifest = corpus_root / "MANIFEST.json"
    if not manifest.exists():
        return None, None
    return json.loads(manifest.read_text()).get("seed"), sha256_of(manifest)


def retrieval_block(health: dict[str, Any]) -> dict[str, Any]:
    """What /health says about retrieval today. The nulls are fields the sidecar does not expose yet."""
    return {
        "sidecar_version": health.get("version"),
        "model_loaded_before_run": health.get("model_loaded"),
        "model_id": None,
        "dtype": None,
        "pool_factor": None,
        "cold_page_cap": None,
    }


def attach_thumbnails(sidecar: Sidecar, run_dir: RunDir, row: dict[str, Any], corpus_root: Path) -> None:
    """On a miss, keep the expected page and the rank 1 page as pictures, because that pair explains most misses."""
    wanted = {"expected": page_id_of(corpus_root, row["expected"]["file"], row["expected"]["page"])}
    if row["top10"]:
        wanted["rank1"] = row["top10"][0]["page_id"]
    thumbnails: dict[str, str | None] = {}
    for role, page_id in wanted.items():
        png = sidecar.get_bytes(f"/pages/{page_id}/image?size=thumb")
        thumbnails[role] = None if png is None else run_dir.write_thumb(page_id, png)
        if png is None:
            run_dir.append_error({"class": "thumbnail_unavailable", "query_id": row["id"], "page_id": page_id, "role": role})
    row["thumbnails"] = thumbnails


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="sidecar base URL, http://127.0.0.1:PORT")
    parser.add_argument("--token", required=True, help="the sidecar's bearer token")
    parser.add_argument("--corpus", type=Path, default=Path("~/demo-corpus"), help="corpus root the index was built from")
    parser.add_argument("--golden", type=Path, default=SCRIPTS_DIR / "golden.jsonl", help="golden set jsonl")
    parser.add_argument("--out", type=Path, default=SCRIPTS_DIR / "eval-runs", help="where run directories go")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_root, out = args.corpus.expanduser().absolute(), args.out.expanduser().absolute()
    sidecar = Sidecar(args.base_url, args.token)
    started_at = datetime.now(UTC)
    git_sha, dirty = git_identity()
    previous = latest_run(out)
    run_dir = RunDir(out / run_id_for(started_at, git_sha))
    run_dir.create()

    health = sidecar.get_json("/health")
    seed, manifest_hash = corpus_identity(corpus_root)
    golden = read_golden(args.golden)
    body = {"corpus_root": str(corpus_root), "queries": golden}

    queries: list[dict[str, Any]] = []
    aggregates: dict[str, Any] | None = None
    try:
        for name, payload in sidecar.stream("/eval/golden/run", body):
            if name == "progress":
                print(f"{payload['done']}/{payload['total']}", file=sys.stderr)
            elif name == "query":
                if not payload["hit5"]:
                    attach_thumbnails(sidecar, run_dir, payload, corpus_root)
                run_dir.write_query(payload)
                queries.append(payload)
            elif name == "done":
                aggregates = payload["aggregates"]
            elif name == "error":
                run_dir.append_error({"class": "stream_error", **payload})
    except urllib.error.HTTPError as error:
        print(f"{error.code} from {error.url}: {error.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 2
    if aggregates is None:
        print("The stream ended without a done event; see errors.jsonl.", file=sys.stderr)
        return 2

    regressed = regressions(previous.read_queries(), queries) if previous else []
    run = {
        "run_id": run_dir.run_id,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "machine": machine(),
        "git_sha": git_sha,
        "dirty": dirty,
        # The runner never clears page_vectors yet, so no run is a cold one on purpose.
        "cold": False,
        "corpus_root": str(corpus_root),
        "corpus_seed": seed,
        "corpus_manifest_hash": manifest_hash,
        "golden_sha": sha256_of(args.golden),
        "retrieval": retrieval_block(health),
        "answer_model": None,
        "judge_model": None,
        "judge_prompt_sha": None,
        "prices_read_on": None,
        "previous_run_id": previous.run_id if previous else None,
        "aggregates": aggregates,
        "regressions": regressed,
    }
    run_dir.write_run(run)
    run_dir.report_html.write_text(render_report(run, queries, previous.read_run() if previous else None, run_dir.root))
    mark_latest(out, run_dir.run_id)

    overall = aggregates["overall"]
    hits = "-" if not overall["count"] else f"{round(overall['hit5'] * overall['count'])}/{overall['count']}"
    print(f"hit@5 {hits}, {len(regressed)} regressions, report at {run_dir.report_html}", file=sys.stderr)
    return 1 if regressed else 0


if __name__ == "__main__":
    sys.exit(main())
