"""A minimal CDP client over raw sockets, so the renderer can be inspected with no dependency."""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import sys
import urllib.request
from urllib.parse import urlparse


def _handshake(sock: socket.socket, host: str, port: int, path: str) -> None:
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
    )
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        buffer += sock.recv(4096)


def _send(sock: socket.socket, payload: dict) -> None:
    body = json.dumps(payload).encode()
    mask = os.urandom(4)
    header = bytearray([0x81])
    length = len(body)
    if length < 126:
        header.append(0x80 | length)
    elif length < 1 << 16:
        header.append(0x80 | 126)
        header += struct.pack(">H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", length)
    header += mask
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(body)))


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks = b""
    while len(chunks) < count:
        chunk = sock.recv(count - len(chunks))
        if not chunk:
            raise ConnectionError("the debugger closed the connection")
        chunks += chunk
    return chunks


def _recv(sock: socket.socket) -> dict:
    first, second = _recv_exact(sock, 2)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack(">H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _recv_exact(sock, 8))[0]
    return json.loads(_recv_exact(sock, length))


def evaluate(expression: str, port: int = 9222) -> object:
    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
    page = next(target for target in targets if target["type"] == "page")
    url = urlparse(page["webSocketDebuggerUrl"])
    sock = socket.create_connection((url.hostname, url.port), timeout=20)
    _handshake(sock, url.hostname or "", url.port or port, url.path)
    _send(sock, {"id": 1, "method": "Runtime.evaluate", "params": {"expression": expression, "returnByValue": True}})
    while True:
        message = _recv(sock)
        if message.get("id") == 1:
            sock.close()
            return message["result"]["result"].get("value")


if __name__ == "__main__":
    print(evaluate(sys.argv[1]))
