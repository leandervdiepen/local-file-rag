"""Binds the socket, announces readiness, then serves.

This is the handshake the Electron main process depends on: stdout carries
`READY <port>` and nothing else, ever.
"""

from __future__ import annotations

import logging
import socket

from flask import Flask
from waitress.server import create_server

logger = logging.getLogger(__name__)


def serve(app: Flask, host: str, port: int) -> None:
    """Bind host:port, print the READY handshake, then serve until the process exits.

    Binding and listening happen before READY is printed, so a client that
    connects the instant it reads READY is queued by the kernel, never refused.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen()
    actual_port = sock.getsockname()[1]

    print(f"READY {actual_port}", flush=True)
    logger.info("serving on %s:%d", host, actual_port)

    server = create_server(app, sockets=[sock])
    server.run()
