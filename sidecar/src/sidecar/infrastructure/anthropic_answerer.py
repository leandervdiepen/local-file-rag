"""Adapter for the `Answerer` port over the Anthropic messages wire format.

By hand rather than through the SDK: the sidecar already speaks this kind of
HTTP elsewhere, the streaming shape is documented and stable, and one fewer
dependency matters in a bundle that has to fit in a DMG.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from typing import Any

from sidecar.domain.answers import AnswerChunk, AnswerRequest, PageImage, Usage
from sidecar.domain.prompting import SYSTEM_PROMPT, page_label, question_block
from sidecar.infrastructure.wire_stream import DEFAULT_TIMEOUT_S, post_event_stream

API_VERSION = "2023-06-01"


class AnthropicAnswerer:
    """Streams an answer from the Anthropic messages API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def stream(self, request: AnswerRequest) -> Iterator[AnswerChunk]:
        """Text as it arrives, then usage once.

        Input and output counts come in different events, so they are held and
        emitted together at the end. Two partial Usage objects would make the
        chat footer show a total that was briefly wrong.
        """
        events = post_event_stream(
            f"{self._base_url}/v1/messages",
            {"x-api-key": self._api_key, "anthropic-version": API_VERSION},
            self._body(request),
            self._timeout_s,
        )
        counted = Usage()
        for payload in events:
            text, counted = _read(payload, counted)
            if text:
                yield AnswerChunk(text=text)
        yield AnswerChunk(usage=counted)

    def _body(self, request: AnswerRequest) -> dict[str, Any]:
        return {
            "model": request.model_id,
            "max_tokens": request.max_tokens,
            "stream": True,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": _content(request)}],
        }


def _content(request: AnswerRequest) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for page in request.pages:
        blocks.append({"type": "text", "text": page_label(page)})
        blocks.append({"type": "image", "source": _source(page)})
    blocks.append({"type": "text", "text": question_block(request.question)})
    return blocks


def _source(page: PageImage) -> dict[str, str]:
    return {
        "type": "base64",
        "media_type": "image/png",
        "data": base64.b64encode(page.png).decode("ascii"),
    }


def _read(payload: str, counted: Usage) -> tuple[str, Usage]:
    """The text in one event and the running usage after it.

    Event types this does not need are ignored rather than refused, because
    the wire gains events over time and a new one is not a failure.
    """
    try:
        body = json.loads(payload)
    except ValueError:
        return "", counted

    kind = body.get("type")
    if kind == "content_block_delta":
        delta = body.get("delta") or {}
        return (delta.get("text") or "" if delta.get("type") == "text_delta" else ""), counted
    if kind == "message_start":
        usage = (body.get("message") or {}).get("usage") or {}
        return "", Usage(input_tokens=int(usage.get("input_tokens", 0)), output_tokens=counted.output_tokens)
    if kind == "message_delta":
        usage = body.get("usage") or {}
        return "", Usage(input_tokens=counted.input_tokens, output_tokens=int(usage.get("output_tokens", 0)))
    return "", counted
