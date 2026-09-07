"""Bearer token authentication, required on every route."""

from __future__ import annotations

import hmac

from flask import Flask, Response, request

from sidecar.interface.errors import error_response

_BEARER_PREFIX = "Bearer "


def _extract_token(header: str | None) -> str | None:
    if header is None or not header.startswith(_BEARER_PREFIX):
        return None
    return header[len(_BEARER_PREFIX) :]


def register_auth(app: Flask, token: str) -> None:
    """Require `Authorization: Bearer <token>` on every route, compared in constant time.

    A missing or wrong token gets 401 with the standard error body. The body
    never explains the auth scheme, so an unauthorized caller learns nothing
    about how to authenticate.
    """

    @app.before_request
    def _check_token() -> Response | None:
        presented = _extract_token(request.headers.get("Authorization"))
        if presented is None or not hmac.compare_digest(presented, token):
            return error_response("unauthorized", "Authentication is required.", status=401)
        return None
