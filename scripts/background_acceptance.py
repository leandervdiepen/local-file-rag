"""Day 5 acceptance: the storage cap evicts, and idle pre-embedding puts it back.

Runs the real sidecar against a real folder with a cap small enough to bite,
then leaves the machine alone and watches the two background jobs do their
work. Everything here is the shipped code path: the timer, pmset, the LanceDB
tables and the real model.
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

REPO = Path(__file__).resolve().parent.parent
CORPUS = Path.home() / "demo-corpus"
TOKEN = "background-acceptance"

# Four pages of vectors, so a seven page deck cannot fit and the cap has to
# choose. Measured at about 60 KB a page.
CAP_BYTES = 240 * 1024
LOOP_SECONDS = 30.0


def call(port: int, method: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode()
    return json.loads(raw) if raw else {}


def drain_progress(port: int) -> None:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/index/progress",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        for raw in response:
            line = raw.decode().strip()
            if line.startswith("data:") and json.loads(line[5:]).get("done"):
                return


def embedded(port: int) -> int:
    return int(call(port, "GET", "/index/stats")["pages_embedded"])


def main() -> int:
    folder = Path(tempfile.mkdtemp(prefix="background-acceptance-"))
    db = Path(tempfile.mkdtemp(prefix="background-acceptance-db-"))
    for deck in sorted((CORPUS / "decks").glob("*.pdf"))[:2]:
        shutil.copy(deck, folder / deck.name)

    process = subprocess.Popen(
        ["uv", "run", "sidecar", "--token", TOKEN, "--db", str(db), "--cap-bytes", str(CAP_BYTES)],
        cwd=REPO / "sidecar",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert process.stdout is not None
        port = int(process.stdout.readline().split()[1])

        call(port, "POST", "/folders", {"path": str(folder)})
        call(port, "POST", "/index/rescan")
        drain_progress(port)
        after_crawl = embedded(port)
        print(f"crawl embedded {after_crawl} pages, cap is {CAP_BYTES // 1024} KB")

        # One page opened, so the cap has something it must not evict.
        page = call(port, "GET", "/index/files")["files"][0]
        urllib.request.urlopen(
            urllib.request.Request(
                f"http://127.0.0.1:{port}/pages/{page['id']}:1/image?size=full",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ),
            timeout=60,
        ).read()
        print(f"opened one page: {Path(page['path']).name} page 1")

        print(f"leaving the machine alone for {LOOP_SECONDS * 2:.0f}s so the loop ticks")
        time.sleep(LOOP_SECONDS * 2 + 5)
        after_cap = embedded(port)
        print(f"after the loop ran: {after_cap} pages embedded")

        # The cap has to bite and then stop. Emptying the store is the failure
        # this check exists for: it is what an eviction loop that cannot see
        # its own effect does.
        evicted = 0 < after_cap < after_crawl
        under_cap = _vectors_bytes(db) <= CAP_BYTES
        verdict = "PASS" if evicted and under_cap else "FAIL"
        print(
            f"{verdict}: {after_crawl - after_cap} of {after_crawl} pages evicted, "
            f"{after_cap} kept, vectors now {_vectors_bytes(db) // 1024} KB against a {CAP_BYTES // 1024} KB cap"
        )
        return 0 if verdict == "PASS" else 1
    finally:
        process.terminate()
        process.wait(timeout=15)
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(db, ignore_errors=True)


def _vectors_bytes(db: Path) -> int:
    """What the vector table costs on disk, read the same way the cap reads it."""
    table = db / "page_vectors.lance"
    if not table.exists():
        return 0
    return sum(entry.stat().st_size for entry in table.rglob("*") if entry.is_file())


if __name__ == "__main__":
    sys.exit(main())
