from __future__ import annotations

import json

from sidecar.interface.sse import encode_event


def _parse(encoded: str) -> tuple[str, dict[str, object]]:
    lines = encoded.split("\n")
    assert lines[0].startswith("event: ")
    assert lines[1].startswith("data: ")
    assert lines[2] == ""
    assert lines[3] == ""
    assert len(lines) == 4
    name = lines[0].removeprefix("event: ")
    payload = json.loads(lines[1].removeprefix("data: "))
    return name, payload


def test_encodes_one_event_with_its_payload() -> None:
    encoded = encode_event("results", {"count": 3})

    name, payload = _parse(encoded)
    assert name == "results"
    assert payload == {"count": 3}


def test_round_trips_a_string_value_with_an_embedded_newline() -> None:
    encoded = encode_event("progress", {"message": "line one\nline two"})

    assert encoded[-2:] == "\n\n"
    name, payload = _parse(encoded)
    assert name == "progress"
    assert payload == {"message": "line one\nline two"}


def test_round_trips_a_unicode_value() -> None:
    encoded = encode_event("citation", {"text": "café résumé 日本語"})

    name, payload = _parse(encoded)
    assert name == "citation"
    assert payload == {"text": "café résumé 日本語"}
    # ensure_ascii=False: the raw characters appear in the wire text, not \uXXXX escapes.
    assert "日本語" in encoded
