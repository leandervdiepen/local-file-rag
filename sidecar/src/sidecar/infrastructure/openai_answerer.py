"""Adapter for the `Answerer` port over the OpenAI chat completions wire format.

One adapter for five ways to answer. OpenAI, Gemini's compatibility endpoint,
OpenRouter, Ollama and LM Studio all speak this shape, so the difference
between them is data in `domain/providers.py` rather than code here (D36).
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from typing import Any

from sidecar.domain.answers import AnswerChunk, AnswerRequest, PageImage, Usage
from sidecar.domain.prompting import SYSTEM_PROMPT, page_label, question_block
from sidecar.infrastructure.wire_stream import DEFAULT_TIMEOUT_S, post_event_stream

DONE = "[DONE]"


class OpenAIAnswerer:
    """Streams an answer from anything that speaks chat completions."""

    def __init__(self, base_url: str, api_key: str | None = None, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s

    def stream(self, request: AnswerRequest) -> Iterator[AnswerChunk]:
        events = post_event_stream(
            f"{self._base_url}/chat/completions",
            self._headers(),
            self._body(request),
            self._timeout_s,
        )
        for payload in events:
            if payload == DONE:
                return
            chunk = _read(payload)
            if chunk is not None:
                yield chunk

    def _headers(self) -> dict[str, str]:
        # No header rather than an empty one: a server on this machine has
        # nobody to authenticate to, and some reject a blank bearer outright.
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _body(self, request: AnswerRequest) -> dict[str, Any]:
        return {
            "model": request.model_id,
            "max_tokens": request.max_tokens,
            "stream": True,
            # Without this the final chunk carries no usage, and the chat
            # footer would have to invent the number it shows.
            "stream_options": {"include_usage": True},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _content(request)},
            ],
        }


def _content(request: AnswerRequest) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for page in request.pages:
        parts.append({"type": "text", "text": page_label(page)})
        parts.append({"type": "image_url", "image_url": {"url": _data_uri(page)}})
    parts.append({"type": "text", "text": question_block(request.question)})
    return parts


def _data_uri(page: PageImage) -> str:
    return f"data:image/png;base64,{base64.b64encode(page.png).decode('ascii')}"


def _read(payload: str) -> AnswerChunk | None:
    """One streamed chunk, or `None` for one that carries nothing this app wants.

    A delta can have `content` of null while `reasoning` holds text. Measured
    against OpenRouter free models on 2026-09-07: reasoning is not the answer
    and is not yielded, but it is not the end of the stream either, so a null
    content must not be read as one.
    """
    try:
        body = json.loads(payload)
    except ValueError:
        return None

    usage = body.get("usage")
    if usage:
        return AnswerChunk(
            usage=Usage(
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
            )
        )

    choices = body.get("choices") or []
    if not choices:
        return None
    text = (choices[0].get("delta") or {}).get("content")
    return AnswerChunk(text=text) if text else None
