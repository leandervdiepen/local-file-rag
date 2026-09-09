"""One GET that returns JSON, with the failures written for a person.

Shared by the catalogue adapters. `wire_stream.py` does the same job for the
streaming POST the answerers make; this is the non-streaming half.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from sidecar.domain.errors import AnswerUnavailableError

DEFAULT_TIMEOUT_S = 20.0

_BY_STATUS = {
    401: "That key was refused, so its models cannot be listed.",
    403: "That key is not allowed to list models.",
    404: "This provider has no model list at that address.",
    429: "The provider is rate limiting this key. Wait a moment and try again.",
}
_UNREACHABLE = "The provider could not be reached."
_LOCAL_UNREACHABLE = "Nothing is answering there. Start the local server and try again."


def get_json(url: str, headers: dict[str, str], timeout_s: float = DEFAULT_TIMEOUT_S) -> Any:
    """GET and parse, raising `AnswerUnavailableError` with an actionable message on any failure."""
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as failure:
        raise AnswerUnavailableError(_BY_STATUS.get(failure.code, _UNREACHABLE)) from failure
    except (TimeoutError, urllib.error.URLError) as failure:
        local = "127.0.0.1" in url or "localhost" in url
        raise AnswerUnavailableError(_LOCAL_UNREACHABLE if local else _UNREACHABLE) from failure
    except ValueError as failure:
        raise AnswerUnavailableError("The provider answered with something that is not a model list.") from failure
