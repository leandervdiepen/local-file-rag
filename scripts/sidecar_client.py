"""Talking to a running sidecar from an acceptance script.

Shared by the acceptance scripts so the two cannot drift, which they already
had: the same helper carried a 600 second timeout in one and 900 in the other.
No dependencies, because these scripts run outside both projects.
"""

from __future__ import annotations

import json
import urllib.parse
import re
import urllib.request
from pathlib import Path
from typing import Any

# A crawl of a real folder embeds every page, so this is minutes, not seconds.
CRAWL_TIMEOUT_S = 900


class Sidecar:
    """The handful of calls an acceptance script makes."""

    def __init__(self, port: int, token: str) -> None:
        self.base_url = f"http://127.0.0.1:{port}"
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=self._headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode()
        return json.loads(raw) if raw else {}

    def events(self, path: str, timeout_s: float = CRAWL_TIMEOUT_S) -> Any:
        """Yield each `data:` payload of an SSE stream until the caller stops reading."""
        request = urllib.request.Request(self.base_url + path, headers=self._headers)
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            for raw in response:
                line = raw.decode().strip()
                if line.startswith("data:"):
                    yield json.loads(line[5:])

    def wait_for_crawl(self) -> None:
        """Return once the indexing job publishes its done snapshot."""
        for payload in self.events("/index/progress"):
            if payload.get("done"):
                return

    def search(self, query: str) -> list[str]:
        """The filenames one search returns, once its stream has closed."""
        found: list[str] = []
        for payload in self.events(f"/search?q={urllib.parse.quote(query)}"):
            for hit in payload.get("hits", []):
                found.append(Path(hit["path"]).name)
            if payload.get("done"):
                break
        return found


def port_from(log: Path) -> int:
    """The port the sidecar bound, read from the line it logs on startup."""
    ports = re.findall(r"serving on 127\\.0\\.0\\.1:(\\d+)", log.read_text())
    if not ports:
        raise SystemExit(f"{log} has no sidecar port in it yet")
    return int(ports[-1])
