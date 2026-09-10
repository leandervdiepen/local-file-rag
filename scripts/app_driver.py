"""A small CDP driver: evaluate JS in the app window and save screenshots."""

from __future__ import annotations

import base64
import json
import re
import socket
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import cdp

SHOTS = Path("/tmp/shots")
LOG_PATH = "/tmp/app-dbg.log"
DEBUG_PORT = 9222
SHOTS.mkdir(exist_ok=True)


def sidecar_base_url() -> str:
    ports = re.findall(r"serving on 127\.0\.0\.1:(\d+)", Path(LOG_PATH).read_text())
    return f"http://127.0.0.1:{ports[-1]}"


class Page:
    def __init__(self) -> None:
        self.connect()

    def connect(self) -> None:
        targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/list"))
        target = next(t for t in targets if t["type"] == "page")
        url = urlparse(target["webSocketDebuggerUrl"])
        self.sock = socket.create_connection((url.hostname, url.port), timeout=180)
        cdp._handshake(self.sock, url.hostname, url.port, url.path)
        self.ident = 1000

    def call(self, method: str, params: dict) -> dict:
        self.ident += 1
        cdp._send(self.sock, {"id": self.ident, "method": method, "params": params})
        while True:
            message = cdp._recv(self.sock)
            if message.get("id") == self.ident:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def js(self, expression: str) -> object:
        out = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        return out.get("result", {}).get("value")

    def token(self) -> str:
        return str(self.js("window.bridge.sidecar.token"))

    def text(self, limit: int = 400) -> str:
        return str(self.js(f"document.body.innerText.slice(0,{limit})") or "").replace("\n", " | ")

    def shot(self, name: str) -> Path:
        data = self.call("Page.captureScreenshot", {"format": "png"})["data"]
        path = SHOTS / f"{name}.png"
        path.write_bytes(base64.b64decode(data))
        return path

    def api(self, path: str, method: str = "GET", body: dict | None = None) -> dict:
        request = urllib.request.Request(
            sidecar_base_url() + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode()
        return json.loads(raw) if raw else {}
