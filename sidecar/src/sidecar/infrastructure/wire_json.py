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
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as failure:
        raise AnswerUnavailableError(explain(failure)) from failure
    except (TimeoutError, urllib.error.URLError) as failure:
        raise AnswerUnavailableError(unreachable(url)) from failure
    except ValueError as failure:
        raise AnswerUnavailableError("The provider answered with something that is not a model list.") from failure
