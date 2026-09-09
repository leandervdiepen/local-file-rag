"""Day 5 acceptance: drop a PDF into a watched folder and find it within five seconds.

Runs the real sidecar as a subprocess against a real temporary folder, so the
watcher, the debounce, the crawl and the FTS index are all the shipped ones.
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
        verdict = "PASS" if found and indexed_at <= DEADLINE_S else "FAIL"
        print(f"{verdict}: {target} indexed {indexed_at:.2f}s after it was dropped, search finds it: {found}")
        return 0 if verdict == "PASS" else 1
    finally:
        process.terminate()
        process.wait(timeout=10)
        shutil.rmtree(watched, ignore_errors=True)
        shutil.rmtree(db, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
