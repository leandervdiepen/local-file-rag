"""`OpenAIAnswerer` against a local HTTP server. Never the internet."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from sidecar.domain.answers import AnswerRequest, PageImage
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.infrastructure.openai_answerer import OpenAIAnswerer

pytestmark = pytest.mark.integration

RECEIVED: list[dict[str, Any]] = []
SCRIPT: dict[str, Any] = {"status": 200, "lines": []}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        RECEIVED.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": json.loads(self.rfile.read(length) or b"{}"),
            }
        )
        status = int(SCRIPT["status"])
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream" if status == 200 else "application/json")
        self.end_headers()
        if status != 200:
            self.wfile.write(json.dumps({"error": {"message": "the provider said no"}}).encode())
            return
        for line in SCRIPT["lines"]:
            self.wfile.write(f"data: {line}\n\n".encode())
            self.wfile.flush()

    def log_message(self, *_: Any) -> None:
        """Quiet. The test output is the assertions, not an access log."""


@pytest.fixture
def provider() -> Iterator[str]:
    RECEIVED.clear()
    SCRIPT.update(status=200, lines=[])
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def a_request(pages: int = 2) -> AnswerRequest:
    return AnswerRequest(
        question="what did egress cost",
        pages=tuple(PageImage(page_id=f"p{n}:1", index=n, png=f"png{n}".encode()) for n in range(1, pages + 1)),
        model_id="some/model",
    )


def delta(text: str | None = None, reasoning: str | None = None) -> str:
    return json.dumps({"choices": [{"delta": {"content": text, "reasoning": reasoning}}]})


def test_the_text_arrives_in_the_order_the_provider_sent_it(provider: str) -> None:
    SCRIPT["lines"] = [delta("Egress "), delta("was "), delta("18.4 TB."), "[DONE]"]

    chunks = list(OpenAIAnswerer(provider).stream(a_request()))

    assert "".join(chunk.text for chunk in chunks) == "Egress was 18.4 TB."


def test_usage_comes_back_from_the_final_chunk(provider: str) -> None:
    SCRIPT["lines"] = [
        delta("hi"),
        json.dumps({"choices": [], "usage": {"prompt_tokens": 9000, "completion_tokens": 120}}),
        "[DONE]",
    ]

    [usage] = [chunk.usage for chunk in OpenAIAnswerer(provider).stream(a_request()) if chunk.usage]

    assert (usage.input_tokens, usage.output_tokens) == (9000, 120)


def test_a_reasoning_chunk_is_not_the_answer_and_is_not_the_end_of_it(provider: str) -> None:
    """Measured against OpenRouter free models: content is null while reasoning carries text."""
    SCRIPT["lines"] = [delta(reasoning="let me look at page 1"), delta("Egress was 18.4 TB."), "[DONE]"]

    chunks = list(OpenAIAnswerer(provider).stream(a_request()))

    assert "".join(chunk.text for chunk in chunks) == "Egress was 18.4 TB."


def test_the_pages_are_sent_as_data_uris_in_order_with_the_question_last(provider: str) -> None:
    SCRIPT["lines"] = ["[DONE]"]

    list(OpenAIAnswerer(provider).stream(a_request(pages=2)))

    content = RECEIVED[0]["body"]["messages"][1]["content"]
    assert [part["type"] for part in content] == ["text", "image_url", "text", "image_url", "text"]
    assert content[0]["text"] == "Page [1]"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[2]["text"] == "Page [2]"
    assert content[-1]["text"] == "Question: what did egress cost"


def test_the_system_prompt_is_the_one_the_domain_wrote(provider: str) -> None:
    from sidecar.domain.prompting import SYSTEM_PROMPT

    SCRIPT["lines"] = ["[DONE]"]

    list(OpenAIAnswerer(provider).stream(a_request()))

    assert RECEIVED[0]["body"]["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}


def test_usage_is_asked_for_so_the_footer_never_has_to_invent_it(provider: str) -> None:
    SCRIPT["lines"] = ["[DONE]"]

    list(OpenAIAnswerer(provider).stream(a_request()))

    assert RECEIVED[0]["body"]["stream_options"] == {"include_usage": True}


def test_a_local_provider_is_sent_no_authorization_header(provider: str) -> None:
    """A server on this machine has nobody to authenticate to, and some reject a blank bearer."""
    SCRIPT["lines"] = ["[DONE]"]

    list(OpenAIAnswerer(provider, api_key=None).stream(a_request()))

    assert "Authorization" not in RECEIVED[0]["headers"]


def test_a_key_is_sent_when_there_is_one(provider: str) -> None:
    SCRIPT["lines"] = ["[DONE]"]

    list(OpenAIAnswerer(provider, api_key="sk-test").stream(a_request()))

    assert RECEIVED[0]["headers"]["Authorization"] == "Bearer sk-test"


@pytest.mark.parametrize(("status", "expected"), [(401, "refused"), (429, "rate limiting"), (503, "trouble")])
def test_a_refusal_says_what_happened_and_what_fixes_it(provider: str, status: int, expected: str) -> None:
    SCRIPT["status"] = status

    with pytest.raises(AnswerUnavailableError) as refused:
        list(OpenAIAnswerer(provider).stream(a_request()))

    assert expected in str(refused.value)


def test_a_local_server_that_is_not_running_says_to_start_it() -> None:
    """Telling someone to check their connection when Ollama is not running is the wrong advice."""
    nothing_there = OpenAIAnswerer("http://127.0.0.1:1", timeout_s=2.0)

    with pytest.raises(AnswerUnavailableError, match="Start the local server"):
        list(nothing_there.stream(a_request()))


def test_a_hosted_provider_that_cannot_be_reached_points_at_the_connection() -> None:
    nothing_there = OpenAIAnswerer("http://does-not-resolve.invalid/v1", timeout_s=2.0)

    with pytest.raises(AnswerUnavailableError, match="could not be reached"):
        list(nothing_there.stream(a_request()))
