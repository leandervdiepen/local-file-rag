"""One GET that returns JSON, with the failures written for a person.

Shared by the catalogue adapters. `wire_stream.py` does the same job for the
streaming POST the answerers make, and both turn a failure into a sentence
through `wire_errors.py`, because a 401 means the same thing whichever call
found it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from sidecar.domain.errors import AnswerUnavailableError
from sidecar.infrastructure.wire_errors import explain, unreachable

DEFAULT_TIMEOUT_S = 20.0


def get_json(url: str, headers: dict[str, str], timeout_s: float = DEFAULT_TIMEOUT_S) -> Any:
    """GET and parse, raising `AnswerUnavailableError` with an actionable message on any failure."""
    return _json(urllib.request.Request(url, headers=headers, method="GET"), url, timeout_s)


def post_json(url: str, headers: dict[str, str], body: Any, timeout_s: float = DEFAULT_TIMEOUT_S) -> Any:
    """POST and parse. Ollama describes a model only over POST, so listing needs both verbs."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    return _json(request, url, timeout_s)


def _json(request: urllib.request.Request, url: str, timeout_s: float) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as failure:
        raise AnswerUnavailableError(explain(failure)) from failure
    except (TimeoutError, urllib.error.URLError) as failure:
        raise AnswerUnavailableError(unreachable(url)) from failure
    except ValueError as failure:
        raise AnswerUnavailableError("The provider answered with something that is not a model list.") from failure
