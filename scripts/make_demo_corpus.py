#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "matplotlib>=3.9",
#   "pillow>=11.0",
#   "reportlab>=4.2",
#   "playwright>=1.47",
# ]
# ///
"""Generates the synthetic demo corpus used to develop and evaluate search.

Everything is invented: company names, people, numbers, screenshots. Never
reads real files. Deterministic for a given --seed except where a library
stamps its own timestamp, which is pinned at the source.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import decks, junk, notes, reports, screenshots  # noqa: E402
from corpus.manifest import Entry, Manifest  # noqa: E402

GROUPS = ["screenshots", "reports", "decks", "notes", "junk"]
DEFAULT_SEED = 20260907


def _reconcile_previous_run(manifest: Manifest, path: Path, only: str | None) -> None:
    """Leave the corpus holding exactly what the next manifest will list.

    Every file a group being regenerated left behind is deleted first, so a
    renamed or dropped file never survives as an orphan the manifest does not
    claim, and its entry is never counted twice.
    """
    data = json.loads(path.read_text())
    for f in data["files"]:
        if only is None or f["group"] == only:
            target = manifest.root / f["path"]
            if target.exists():
                target.unlink()
            continue
        manifest.entries.append(
            Entry(f["path"], f["group"], f["fate"], f.get("reason"), f.get("size", 0))
        )


def _run_group(group: str, seed: int, out: Path, manifest: Manifest, tmp_dir: Path) -> int:
    if group == "screenshots":
        return screenshots.generate(seed, out, manifest)
    if group == "reports":
        return reports.generate(seed, out, manifest, tmp_dir)
    if group == "decks":
        return decks.generate(seed, out, manifest, tmp_dir)
    if group == "notes":
        return notes.generate(seed, out, manifest)
    if group == "junk":
        return junk.generate(seed, out, manifest)
    raise ValueError(group)


def _print_summary(manifest: Manifest) -> None:
    stats = manifest.group_stats()
    width = max(len(g) for g in stats) + 2
    print(f"\n{'group':<{width}}{'files':>8}{'bytes':>16}")
    print("-" * (width + 24))
    total_files = total_bytes = 0
    for group in sorted(stats):
        count, size = stats[group]
        total_files += count
        total_bytes += size
        print(f"{group:<{width}}{count:>8}{size:>16,}")
    print("-" * (width + 24))
    print(f"{'total':<{width}}{total_files:>8}{total_bytes:>16,}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("~/demo-corpus"),
                         help="corpus output directory (default: ~/demo-corpus)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                         help=f"deterministic seed (default: {DEFAULT_SEED})")
    parser.add_argument("--only", choices=GROUPS, default=None,
                         help="regenerate a single group instead of everything")
    args = parser.parse_args()

    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    manifest = Manifest(seed=args.seed, root=out)
    manifest_path = out / "MANIFEST.json"
    if manifest_path.exists():
        _reconcile_previous_run(manifest, manifest_path, args.only)

    groups = GROUPS if args.only is None else [args.only]
    # A fixed path, not tempfile.mkdtemp()'s random suffix: reportlab embeds
    # this path in its PDF object naming, so a random name would break
    # byte-for-byte determinism between runs of the same seed.
    tmp_dir = Path(tempfile.gettempdir()) / "demo-corpus-chart-cache"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True)
    try:
        for group in groups:
            n = _run_group(group, args.seed, out, manifest, tmp_dir)
            print(f"{group}: {n} files")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    manifest.write()
    _print_summary(manifest)
    print(f"\nWrote corpus to {out}")


if __name__ == "__main__":
    main()
