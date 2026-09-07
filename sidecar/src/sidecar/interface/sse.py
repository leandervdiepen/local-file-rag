"""Server-sent event encoding, shared by every streaming route.

There is no anonymous `data:` event in this API: every event carries a name
and a JSON object payload, so a field can be added later without breaking
whatever is parsing the stream.
"""

from __future__ import annotations

import json
from typing import Any


def encode_event(name: str, payload: dict[str, Any]) -> str:
    """Encode one named SSE event carrying a JSON-serializable payload.

    `ensure_ascii=False` keeps unicode text as unicode rather than `\\uXXXX`
    escapes, since SSE data is transported as UTF-8 text either way. A real
    newline inside a string value is escaped to the two characters `\\n` by
    `json.dumps` itself, so the event this returns is always exactly one
    `data:` line regardless of what the payload contains.
    """
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {name}\ndata: {data}\n\n"
