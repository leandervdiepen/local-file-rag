"""Domain error types.

Domain and application code raise these instead of building error strings.
`interface/errors.py` owns turning one into an HTTP status code and a wire body.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for every error the domain and application layers raise.

    `code` is a stable snake_case identifier that the interface layer maps to
    a status code and that the renderer switches on. It does not change once
    shipped, even if the message text does.
    """

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """The requested resource does not exist."""

    code = "not_found"


class ValidationError(DomainError):
    """The caller's input fails a domain invariant."""

    code = "invalid_request"
