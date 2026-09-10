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
from sidecar.infrastructure.wire_errors import TIMED_OUT, explain, unreachable

DEFAULT_TIMEOUT_S = 120.0


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
        raise AnswerUnavailableError(explain(failure)) from failure
    except TimeoutError as failure:
        raise AnswerUnavailableError(TIMED_OUT) from failure
    except urllib.error.URLError as failure:
        raise AnswerUnavailableError(unreachable(url)) from failure

    try:
        for raw in response:
            line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            if line.startswith("data:"):
                yield line[5:].lstrip()
    finally:
        response.close()
