"""The day 5 acceptance, run against a live sidecar.

Three claims, all from `docs/PLAN.md`: a PDF dropped into a watched folder is
searchable within five seconds, a folder the user excludes stops returning
results, and the stats match what `ls` counts. Everything here is the shipped
path: the real watcher, the real debounce, the real model, the real tables.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path("/Users/leandervandiepen/Documents/lndr/diepen/code/diepen/local-file-rag")
CORPUS = Path.home() / "demo-corpus"
TOKEN = "acceptance-token"
DEADLINE_S = 5.0


def call(port: int, method: str, path: str, body: dict | None = None) -> object:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode()
    return json.loads(raw) if raw else None


def drain_progress(port: int) -> None:
    """Read /index/progress until the job publishes its done snapshot."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/index/progress",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        for raw in response:
            line = raw.decode().strip()
            if line.startswith("data:") and json.loads(line[5:]).get("done"):
                return


def search_names(port: int, query: str) -> list[str]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/search?q={query}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    found: list[str] = []
    with urllib.request.urlopen(request, timeout=60) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            payload = json.loads(line[5:])
            for hit in payload.get("hits", []):
                found.append(Path(hit["path"]).name)
            if payload.get("done"):
                break
    return found


def main() -> int:
    watched = Path(tempfile.mkdtemp(prefix="watch-acceptance-"))
    db = Path(tempfile.mkdtemp(prefix="watch-acceptance-db-"))
    seed = CORPUS / "decks" / "hiring-plan-2026.pdf"
    shutil.copy(seed, watched / "already-here.pdf")

    process = subprocess.Popen(
        ["uv", "run", "sidecar", "--token", TOKEN, "--db", str(db)],
        cwd=REPO / "sidecar",
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
    )
    try:
        assert process.stdout is not None
        port = int(process.stdout.readline().split()[1])
        print(f"sidecar on {port}, watching {watched}")

        call(port, "POST", "/folders", {"path": str(watched)})
        call(port, "POST", "/index/rescan")
        drain_progress(port)
        print("first crawl done:", call(port, "GET", "/index/stats"))

        # D49 widens every query with visual candidates, so an empty stage 1
        # still returns pages. The name is what says the new file arrived.
        target = "zeppelin.pdf"
        assert target not in search_names(port, "zeppelin"), "the file is not there yet"

        dropped_at = time.perf_counter()
        shutil.copy(seed, watched / target)

        # Polled on /index/files rather than /search: every search runs stage 2
        # against the model and costs about a second, so polling with it would
        # measure the probe rather than the watcher. The search after it is
        # what proves the word "searchable".
        indexed_at = None
        while time.perf_counter() - dropped_at < DEADLINE_S * 4:
            names = [Path(f["path"]).name for f in call(port, "GET", "/index/files")["files"]]
            if target in names:
                indexed_at = time.perf_counter() - dropped_at
                break
            time.sleep(0.1)

        if indexed_at is None:
            print(f"FAIL: {target} never reached the index")
            return 1

        found = target in search_names(port, target.removesuffix(".pdf"))
        dropped_in = indexed_at <= DEADLINE_S and found
        print(
            f"{_verdict(dropped_in)}: {target} indexed {indexed_at:.2f}s after it was dropped "
            f"against a {DEADLINE_S:.0f}s budget, search finds it: {found}"
        )

        excluded = _excluding_a_folder_hides_it(port, watched, target)
        counted = _stats_match_ls(port, watched)
        return 0 if dropped_in and excluded and counted else 1
    finally:
        process.terminate()
        process.wait(timeout=10)
        shutil.rmtree(watched, ignore_errors=True)
        shutil.rmtree(db, ignore_errors=True)


def _excluding_a_folder_hides_it(port: int, watched: Path, target: str) -> bool:
    """Turn the folder off, and what it holds must stop coming back."""
    folder = call(port, "GET", "/folders")["folders"][0]
    call(port, "PATCH", f"/folders/{folder['id']}", {"enabled": False})
    while_off = search_names(port, target.removesuffix(".pdf"))

    call(port, "PATCH", f"/folders/{folder['id']}", {"enabled": True})
    while_on = search_names(port, target.removesuffix(".pdf"))

    hidden = while_off == []
    back = target in while_on
    print(f"{_verdict(hidden and back)}: excluded folder returns {len(while_off)} results, back on returns {len(while_on)}")
    return hidden and back


def _stats_match_ls(port: int, watched: Path) -> bool:
    """The count on the index screen against the count in the folder."""
    on_disk = sum(1 for entry in watched.rglob("*") if entry.is_file())
    stats = call(port, "GET", "/index/stats")
    scanned = stats["files_scanned"]
    print(f"{_verdict(scanned == on_disk)}: {scanned} files scanned against {on_disk} files on disk")
    return bool(scanned == on_disk)


def _verdict(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


if __name__ == "__main__":
    sys.exit(main())
