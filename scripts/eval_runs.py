"""The on-disk shape of one eval run, what run.json records about it, and how the run before it is read back.

    scripts/eval-runs/<UTC timestamp>_<short sha>/
      run.json           identity, config, aggregates, regressions
      queries/<id>.json  one per golden query, the wire payload plus thumbnail paths on a miss
      thumbs/<page>.png  thumbnails of the expected and rank 1 pages, misses only
      errors.jsonl       attempts that produced no scorable output, one object per line
      report.html        self-contained
    scripts/eval-runs/LATEST  the newest run id

Disk is canonical. Everything the report shows is read back from these files,
so a run can be re-rendered or diffed without the sidecar that produced it.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LATEST_FILE = "LATEST"
SHORT_SHA_LENGTH = 7


def run_id_for(started_at: datetime, git_sha: str) -> str:
    return f"{started_at:%Y%m%dT%H%M%SZ}_{git_sha[:SHORT_SHA_LENGTH]}"


@dataclass(frozen=True)
class RunDir:
    """One run's directory. Paths are properties so the layout is written down once."""

    root: Path

    @property
    def run_id(self) -> str:
        return self.root.name

    @property
    def run_json(self) -> Path:
        return self.root / "run.json"

    @property
    def queries_dir(self) -> Path:
        return self.root / "queries"

    @property
    def thumbs_dir(self) -> Path:
        return self.root / "thumbs"

    @property
    def errors_jsonl(self) -> Path:
        return self.root / "errors.jsonl"

    @property
    def report_html(self) -> Path:
        return self.root / "report.html"

    def create(self) -> None:
        self.queries_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(exist_ok=True)
        # An empty errors file says "nothing failed", a missing one says "nobody looked".
        self.errors_jsonl.touch()

    def write_run(self, run: dict[str, Any]) -> None:
        self.run_json.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n")

    def write_query(self, row: dict[str, Any]) -> Path:
        path = self.queries_dir / f"{row['id']}.json"
        path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
        return path

    def write_thumb(self, page_id: str, png: bytes) -> str:
        """Store one thumbnail and return its path relative to the run root, which is what the query file records."""
        # A page id is `<hex>:<page_no>`, and a colon in a filename is a bad day on macOS.
        path = self.thumbs_dir / f"{page_id.replace(':', '_')}.png"
        path.write_bytes(png)
        return str(path.relative_to(self.root))

    def append_error(self, error: dict[str, Any]) -> None:
        with self.errors_jsonl.open("a") as handle:
            handle.write(json.dumps(error, sort_keys=True) + "\n")

    def read_run(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.run_json.read_text())
        return loaded

    def read_queries(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [json.loads(path.read_text()) for path in self.queries_dir.glob("*.json")]
        return sorted(rows, key=lambda row: str(row["id"]))


def latest_run(out: Path) -> RunDir | None:
    """The run LATEST names, or `None` when there is no earlier run or its directory is gone."""
    marker = out / LATEST_FILE
    if not marker.exists():
        return None
    candidate = RunDir(out / marker.read_text().strip())
    return candidate if candidate.run_json.exists() else None


def mark_latest(out: Path, run_id: str) -> None:
    (out / LATEST_FILE).write_text(run_id + "\n")


def regressions(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[str]:
    """Query ids that hit at 5 in the previous run and miss now. The only blocking retrieval check, per D47."""
    hit_before = {row["id"]: bool(row["hit5"]) for row in previous}
    return sorted(row["id"] for row in current if not row["hit5"] and hit_before.get(row["id"], False))


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


def run_record(
    run_id: str,
    started_at: datetime,
    git_sha: str,
    dirty: bool,
    corpus_root: Path,
    golden_path: Path,
    health: dict[str, Any],
    previous_run_id: str | None,
    aggregates: dict[str, Any],
    regressed: list[str],
) -> dict[str, Any]:
    """run.json for one finished run.

    `git_sha` and `dirty` come from the caller because the run directory is
    named after the sha and creating it would otherwise dirty the checkout
    this field is reporting on.
    """
    seed, manifest_hash = corpus_identity(corpus_root)
    return {
        "run_id": run_id,
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
        "golden_sha": sha256_of(golden_path),
        "retrieval": retrieval_block(health),
        "answer_model": None,
        "judge_model": None,
        "judge_prompt_sha": None,
        "prices_read_on": None,
        "previous_run_id": previous_run_id,
        "aggregates": aggregates,
        "regressions": regressed,
    }
