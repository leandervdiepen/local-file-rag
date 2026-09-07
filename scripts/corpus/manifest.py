"""Collects every generated file's fate for MANIFEST.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from corpus.rng import mtime_for


@dataclass
class Entry:
    path: str
    group: str
    fate: str  # "indexed" or "skipped"
    reason: str | None = None
    size: int = 0


@dataclass
class Manifest:
    seed: int
    root: Path
    entries: list[Entry] = field(default_factory=list)

    def add_indexed(self, path: Path, group: str) -> None:
        self._stamp(path, group)
        self.entries.append(
            Entry(self._rel(path), group, "indexed", size=self._size(path))
        )

    def add_skipped(self, path: Path, group: str, reason: str) -> None:
        self._stamp(path, group)
        self.entries.append(
            Entry(self._rel(path), group, "skipped", reason, self._size(path))
        )

    def _rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    def _size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return 0

    def _stamp(self, path: Path, group: str) -> None:
        if not path.exists():
            return
        ts = mtime_for(self.seed, self._rel(path))
        os.utime(path, (ts, ts))

    def group_stats(self) -> dict[str, tuple[int, int]]:
        stats: dict[str, tuple[int, int]] = {}
        for e in self.entries:
            count, total = stats.get(e.group, (0, 0))
            stats[e.group] = (count + 1, total + e.size)
        return stats

    def write(self) -> Path:
        """Write MANIFEST.json, listing itself as the one file it knows the crawler will refuse.

        The manifest sits inside the corpus, so a crawl sees it like any other
        .json and skips it as unsupported. Leaving it out would make every
        reconciliation report one unexplained file. Its own size is only known
        after writing, so the entry is written twice: once to learn the size,
        once with it.
        """
        out = self.root / "MANIFEST.json"
        own = Entry(out.name, "corpus", "skipped", "unsupported_type", 0)
        others = [e for e in self.entries if e.path != out.name]
        self.entries = [*others, own]
        self._write_payload(out)
        own.size = out.stat().st_size
        return self._write_payload(out)

    def _write_payload(self, out: Path) -> Path:
        payload = {
            "seed": self.seed,
            "file_count": len(self.entries),
            "files": [
                {
                    "path": e.path,
                    "group": e.group,
                    "fate": e.fate,
                    "reason": e.reason,
                    "size": e.size,
                }
                for e in sorted(self.entries, key=lambda e: e.path)
            ],
        }
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return out
