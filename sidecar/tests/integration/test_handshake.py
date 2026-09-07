"""The contract the Electron main process depends on: spawn, READY, authenticated /health, clean exit."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

TOKEN = "handshake-test-token"


def _sidecar_executable() -> str:
    venv_candidate = Path(sys.executable).parent / "sidecar"
    if venv_candidate.exists():
        return str(venv_candidate)
    found = shutil.which("sidecar")
    if found is None:
        raise RuntimeError("sidecar console script not found; run `uv sync` first")
    return found


def _get(url: str, token: str) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_handshake_then_authenticated_health_then_clean_exit(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [_sidecar_executable(), "--port", "0", "--token", TOKEN, "--db", str(tmp_path / "db")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        ready_line = process.stdout.readline().strip()
        assert ready_line.startswith("READY "), f"expected READY line, got: {ready_line!r}"
        port = int(ready_line.removeprefix("READY "))

        base_url = f"http://127.0.0.1:{port}"

        status, body = _get(f"{base_url}/health", TOKEN)
        assert status == 200
        assert body["status"] == "ok"

        status, body = _get(f"{base_url}/health", "wrong-token")
        assert status == 401
        assert body["error"]["code"] == "unauthorized"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise AssertionError("sidecar did not exit within five seconds of SIGTERM") from None
