"""Maps errors to the standard wire body so a client never sees a stack trace."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

from sidecar.domain.errors import (
    DomainError,
    IndexBusyError,
    NotFoundError,
    UnreadableFileError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ValidationError: 400,
    IndexBusyError: 409,
    # A stored page whose file will not open now was readable when it was
    # indexed, so the file has changed or gone since. To the caller that is a
    # page that is not there, not a server fault.
    UnreadableFileError: 404,
}


def error_response(code: str, message: str, status: int, detail: dict[str, Any] | None = None) -> Response:
    """Build the standard `{"error": {...}}` body as a ready-to-return Flask response."""
    body = {"error": {"code": code, "message": message, "detail": detail or {}}}
    response = jsonify(body)
    response.status_code = status
    return response


def register_error_handlers(app: Flask) -> None:
    """Register handlers so every error path, known or not, returns the standard body."""

    @app.errorhandler(DomainError)
    def _handle_domain_error(exc: DomainError) -> Response:
        status = _STATUS_BY_ERROR.get(type(exc), 500)
        return error_response(exc.code, exc.message, status)

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException) -> Response:
        code = (exc.name or "http_error").lower().replace(" ", "_")
        return error_response(code, exc.description or "Request failed.", exc.code or 500)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception) -> Response:
        logger.exception("unhandled exception")
        return error_response("internal_error", "Something went wrong on this device.", 500)
