"""Letting the app's own window talk to the sidecar, and nothing else usefully.

The renderer is a page, so every call it makes is a cross origin request that
a browser blocks unless this says otherwise. In development the page is served
from the Vite dev server; in the packaged app it is a `file://` page, whose
origin is the string "null". Neither can reach the sidecar without this, so
without it the app is a white window in dev and a broken one when shipped.

This grants nothing on its own. Every route still requires the bearer token,
which is 32 random bytes generated per launch and handed to the renderer
through the preload bridge. A page in the user's browser can be told by this
policy that it may ask, and still cannot answer the question that matters.
"""

from __future__ import annotations

from flask import Flask, Response, request

ALLOWED_HEADERS = "Authorization, Content-Type"
ALLOWED_METHODS = "GET, POST, PATCH, DELETE, OPTIONS"

# Long enough that a session stops paying for preflights, short enough that a
# policy change takes effect without asking anyone to restart anything.
PREFLIGHT_MAX_AGE = "600"


def register_cors(app: Flask) -> None:
    """Answer preflights, and echo the caller's origin back on every response.

    Echoed rather than `*` because a wildcard cannot carry credentials if this
    ever needs them, and because `Vary: Origin` keeps a cache from handing one
    origin's response to another.
    """

    @app.after_request
    def _allow_the_window(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
        response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
        response.headers["Access-Control-Max-Age"] = PREFLIGHT_MAX_AGE
        return response
