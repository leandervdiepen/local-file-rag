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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sidecar_client import Sidecar  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CORPUS = Path.home() / "demo-corpus"
TOKEN = "background-acceptance"

# Four pages of vectors, so a seven page deck cannot fit and the cap has to
# choose. Measured at about 60 KB a page.
CAP_BYTES = 240 * 1024
LOOP_SECONDS = 30.0


def embedded(sidecar: Sidecar) -> int:
    return int(sidecar.call("GET", "/index/stats")["pages_embedded"])


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
        sidecar = Sidecar(int(process.stdout.readline().split()[1]), TOKEN)

        sidecar.call("POST", "/folders", {"path": str(folder)})
        sidecar.call("POST", "/index/rescan")
        sidecar.wait_for_crawl()
        after_crawl = embedded(sidecar)
        print(f"crawl embedded {after_crawl} pages, cap is {CAP_BYTES // 1024} KB")

        # One page opened, so the cap has something it must not evict.
        page = sidecar.call("GET", "/index/files")["files"][0]
        urllib.request.urlopen(
            urllib.request.Request(
                f"{sidecar.base_url}/pages/{page['id']}:1/image?size=full",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ),
            timeout=60,
        ).read()
        print(f"opened one page: {Path(page['path']).name} page 1")

        print(f"leaving the machine alone for {LOOP_SECONDS * 2:.0f}s so the loop ticks")
        time.sleep(LOOP_SECONDS * 2 + 5)
        after_cap = embedded(sidecar)
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
