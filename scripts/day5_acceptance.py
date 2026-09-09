#!/usr/bin/env -S uv run python
"""The day 5 acceptance, run against a live sidecar.

Three claims, all from `docs/PLAN.md`: a PDF dropped into a watched folder is
searchable within five seconds, a folder the user excludes stops returning
results, and the stats match what `ls` counts. Everything here is the shipped
path: the real watcher, the real debounce, the real model, the real tables.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sidecar_client import Sidecar  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CORPUS = Path.home() / "demo-corpus"
TOKEN = "day5-acceptance"
DEADLINE_S = 5.0


def main() -> int:
    watched = Path(tempfile.mkdtemp(prefix="day5-"))
    db = Path(tempfile.mkdtemp(prefix="day5-db-"))
    seed = CORPUS / "decks" / "hiring-plan-2026.pdf"
    shutil.copy(seed, watched / "already-here.pdf")

    process = subprocess.Popen(
        ["uv", "run", "sidecar", "--token", TOKEN, "--db", str(db)],
        cwd=REPO / "sidecar",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert process.stdout is not None
        sidecar = Sidecar(int(process.stdout.readline().split()[1]), TOKEN)
        print(f"sidecar on {sidecar.base_url}, watching {watched}")

        sidecar.call("POST", "/folders", {"path": str(watched)})
        sidecar.call("POST", "/index/rescan")
        sidecar.wait_for_crawl()
        print("first crawl done:", sidecar.call("GET", "/index/stats"))

        dropped_in = _a_dropped_file_is_searchable(sidecar, watched, seed)
        excluded = _excluding_a_folder_hides_it(sidecar)
        counted = _stats_match_ls(sidecar, watched)
        return 0 if dropped_in and excluded and counted else 1
    finally:
        process.terminate()
        process.wait(timeout=15)
        shutil.rmtree(watched, ignore_errors=True)
        shutil.rmtree(db, ignore_errors=True)


def _a_dropped_file_is_searchable(sidecar: Sidecar, watched: Path, seed: Path) -> bool:
    """Drop a file in and time how long until the index has it.

    Timed on `/index/files` rather than on a search, because every search runs
    stage 2 against the model and costs about a second, so polling with one
    would measure the probe rather than the watcher. The search after it is
    what proves the word "searchable".
    """
    target = "zeppelin.pdf"
    dropped_at = time.perf_counter()
    shutil.copy(seed, watched / target)

    indexed_at = None
    while time.perf_counter() - dropped_at < DEADLINE_S * 4:
        names = [Path(row["path"]).name for row in sidecar.call("GET", "/index/files")["files"]]
        if target in names:
            indexed_at = time.perf_counter() - dropped_at
            break
        time.sleep(0.1)

    if indexed_at is None:
        print(f"FAIL: {target} never reached the index")
        return False

    found = target in sidecar.search(target.removesuffix(".pdf"))
    passed = indexed_at <= DEADLINE_S and found
    print(
        f"{_verdict(passed)}: {target} indexed {indexed_at:.2f}s after it was dropped "
        f"against a {DEADLINE_S:.0f}s budget, search finds it: {found}"
    )
    return passed


def _excluding_a_folder_hides_it(sidecar: Sidecar) -> bool:
    """Turn the folder off, and what it holds must stop coming back."""
    folder = sidecar.call("GET", "/folders")["folders"][0]
    sidecar.call("PATCH", f"/folders/{folder['id']}", {"enabled": False})
    while_off = sidecar.search("zeppelin")

    sidecar.call("PATCH", f"/folders/{folder['id']}", {"enabled": True})
    while_on = sidecar.search("zeppelin")

    passed = while_off == [] and "zeppelin.pdf" in while_on
    print(f"{_verdict(passed)}: excluded folder returns {len(while_off)} results, back on returns {len(while_on)}")
    return passed


def _stats_match_ls(sidecar: Sidecar, watched: Path) -> bool:
    """The count on the index screen against the count in the folder."""
    on_disk = sum(1 for entry in watched.rglob("*") if entry.is_file())
    scanned = sidecar.call("GET", "/index/stats")["files_scanned"]
    print(f"{_verdict(scanned == on_disk)}: {scanned} files scanned against {on_disk} files on disk")
    return bool(scanned == on_disk)


def _verdict(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


if __name__ == "__main__":
    sys.exit(main())
