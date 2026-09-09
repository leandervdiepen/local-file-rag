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


class FolderUnreadableError(DomainError):
    """A folder exists but this process may not read it.

    Separate from a missing folder because the user can fix this one, and the
    message tells them exactly where in System Settings.
    """

    code = "folder_unreadable"


class UnreadableFileError(DomainError):
    """The bytes will not open as the thing they claim to be."""

    code = "file_unreadable"


class EncryptedFileError(DomainError):
    """The file needs a password this app will never ask for."""

    code = "file_encrypted"


class ModelUnavailableError(DomainError):
    """The retrieval model is not on this machine and could not be fetched.

    First run downloads about four gigabytes, and the two ways that fails are
    no connection and no disk. Both are the user's to fix, so this carries a
    message that says which and leaves the library's own wording out of it.
    """

    code = "model_unavailable"


class IndexBusyError(DomainError):
    """An indexing job is already running and a second would conflict with it."""

    code = "index_busy"


class AnswerUnavailableError(DomainError):
    """The answer provider refused, ran out of quota, or could not be reached.

    Its message reaches the chat panel, so it says what happened and the one
    thing the user can do about it.
    """

    code = "answer_unavailable"
