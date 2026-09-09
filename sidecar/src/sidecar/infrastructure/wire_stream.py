"""Talking to an answer provider over HTTP, and reading its event stream.

Shared by the two answer adapters because both speak server-sent events over
POST and both have to turn a failure into something a person can act on. What
goes in the body and what the events mean stays in each adapter: this file
knows about HTTP and nothing about either vendor.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from sidecar.domain.errors import AnswerUnavailableError

DEFAULT_TIMEOUT_S = 120.0

# Written for the person reading the chat panel: what happened, and the one
# thing that changes it. Following docs/conventions/copy.md, none of these
# blames the user and none of them says "unexpected".
_BY_STATUS = {
    401: "That key was refused. Check it in Settings.",
    403: "That key is not allowed to use this model. Pick another model in Settings.",
    404: "That model does not exist at this provider. Pick another one in Settings.",
    429: "The provider is rate limiting this key. Wait a moment and ask again.",
}
_SERVER_FAULT = "The provider is having trouble. Wait a moment and ask again."
_UNREACHABLE = "The provider could not be reached. Check your connection, or switch to a local model in Settings."
_TIMED_OUT = "The provider took too long to answer. Ask again, or switch to a local model in Settings."


def post_event_stream(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Iterator[str]:
    """POST and yield each `data:` payload, closing the response when the caller stops.

    The `finally` is what stops a user who closed the chat panel from paying
    for the rest of an answer: closing the generator closes the connection,
    and the provider stops billing at the point it notices.

    Raises `AnswerUnavailableError` for every failure, with a message written
    for the chat panel rather than a status code.
    """
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        response = urllib.request.urlopen(request, timeout=timeout_s)
    except urllib.error.HTTPError as failure:
        raise AnswerUnavailableError(_explain(failure)) from failure
    except TimeoutError as failure:
        raise AnswerUnavailableError(_TIMED_OUT) from failure
    except urllib.error.URLError as failure:
        raise AnswerUnavailableError(_UNREACHABLE) from failure

    try:
        for raw in response:
            line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            if line.startswith("data:"):
                yield line[5:].lstrip()
    finally:
        response.close()


def _explain(failure: urllib.error.HTTPError) -> str:
    """The provider's own words when it gave any, otherwise what the status means."""
    known = _BY_STATUS.get(failure.code)
    if known is not None:
        return known
    detail = _provider_message(failure)
    if failure.code >= 500:
        return _SERVER_FAULT if detail is None else f"{_SERVER_FAULT} It said: {detail}"
    return f"The provider refused the request. It said: {detail}" if detail else _SERVER_FAULT


def _provider_message(failure: urllib.error.HTTPError) -> str | None:
    try:
        body = json.loads(failure.read())
    except (ValueError, OSError):
        return None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        return str(message) if message else None
    return str(error) if error else None
