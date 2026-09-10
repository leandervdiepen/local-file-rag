"""What an HTTP failure from a provider means, said for the person reading it.

Shared by the streaming POST the answerers make and the plain GET the
catalogues make, because a 401 means the same thing to a user whichever call
found it. Following `docs/conventions/copy.md`: none of these blames the user
and none says "unexpected".
"""

from __future__ import annotations

import json
import urllib.error

SERVER_FAULT = "The provider is having trouble. Wait a moment and ask again."
UNREACHABLE = "The provider could not be reached. Check your connection, or switch to a local model in Settings."
LOCAL_UNREACHABLE = "Nothing is answering there. Start the local server and try again."
TIMED_OUT = "The provider took too long to answer. Ask again, or switch to a local model in Settings."

BY_STATUS = {
    401: "That key was refused. Check it in Settings.",
    403: "That key is not allowed to use this model. Pick another model in Settings.",
    404: "That model does not exist at this provider. Pick another one in Settings.",
    429: "The provider is rate limiting this key. Wait a moment and ask again.",
}


def explain(failure: urllib.error.HTTPError) -> str:
    """The provider's own words when it gave any, otherwise what the status means."""
    known = BY_STATUS.get(failure.code)
    if known is not None:
        return known
    detail = provider_message(failure)
    if failure.code >= 500:
        return SERVER_FAULT if detail is None else f"{SERVER_FAULT} It said: {detail}"
    return f"The provider refused the request. It said: {detail}" if detail else SERVER_FAULT


def provider_message(failure: urllib.error.HTTPError) -> str | None:
    try:
        body = json.loads(failure.read())
    except (ValueError, OSError):
        return None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        return str(message) if message else None
    return str(error) if error else None


def unreachable(url: str) -> str:
    """A local server that is not running is a different problem from a network that is down."""
    return LOCAL_UNREACHABLE if "127.0.0.1" in url or "localhost" in url else UNREACHABLE
