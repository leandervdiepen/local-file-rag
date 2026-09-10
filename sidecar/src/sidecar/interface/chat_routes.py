"""The /chat route: retrieval, then the answer as it is written."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from flask import Blueprint, Response, request

from sidecar.application.answer_question import AnswerEvent, AnswerQuestion
from sidecar.application.search import Search
from sidecar.domain.errors import AnswerUnavailableError
from sidecar.domain.providers import DEFAULT_PROVIDER_ID
from sidecar.interface.errors import error_response
from sidecar.interface.sse import encode_event

logger = logging.getLogger(__name__)

_MISSING_QUESTION = "A question is needed. Send one in the body as question."
_MISSING_MODEL = "A provider and a model are needed. Pick one in Settings."

_STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


def build_chat_blueprint(search: Search, answer: AnswerQuestion) -> Blueprint:
    """Build the /chat blueprint bound to one search and one answer use case.

    The stream is `retrieval`, then zero or more `token` and `citation`, then
    exactly one terminal event. A provider that refuses after the stream has
    opened cannot become a status code, so that terminal event is `error`
    rather than `done`, which is the second half of the rule in http-api.md
    that every stream ends in exactly one of the two.
    """
    bp = Blueprint("chat", __name__)

    @bp.post("/chat")
    def chat() -> Response:
        body = request.get_json(silent=True) or {}
        question = body.get("question")
        if not isinstance(question, str) or not question.strip():
            return error_response("missing_question", _MISSING_QUESTION, status=400)

        # Which models exist is the provider's answer to give, so nothing here
        # checks the id against a list. A provider that does not have it says
        # so, and that message reaches the panel as an error event.
        provider_id = body.get("provider") or DEFAULT_PROVIDER_ID
        model_id = body.get("model_id")
        if not isinstance(provider_id, str) or not isinstance(model_id, str) or not model_id.strip():
            return error_response("missing_model", _MISSING_MODEL, status=400)

        return Response(
            _events(search, answer, question, provider_id, model_id),
            mimetype="text/event-stream",
            headers=_STREAM_HEADERS,
        )

    return bp


def _events(search: Search, answer: AnswerQuestion, question: str, provider_id: str, model_id: str) -> Iterator[str]:
    """Retrieve, then answer, converting each step into one named event.

    Retrieval runs before the answer and inside the stream, because it is the
    slow part that has something to show: the pages appear while the model is
    still reading them.
    """
    try:
        hits = search.stage_two(question, search.stage_one(question))
    except Exception:
        logger.exception("retrieval failed for %r", question)
        yield encode_event("error", {"code": "search_failed", "message": "The search behind this answer failed."})
        return

    try:
        for event in answer.run(question, hits, provider_id, model_id):
            yield _encode(event, model_id)
    except AnswerUnavailableError as unavailable:
        yield encode_event("error", {"code": unavailable.code, "message": unavailable.message})
    except Exception:
        # `http-api.md` says every stream ends in exactly one terminal event.
        # Anything that is not an `AnswerUnavailableError` used to escape the
        # generator, ending the response with no terminal event at all, and
        # the panel sat on a spinner with nothing coming.
        logger.exception("answering %r failed", question)
        yield encode_event(
            "error",
            {"code": "answer_failed", "message": "The answer stopped part way. Ask again, or pick another model."},
        )


def _encode(event: AnswerEvent, model_id: str) -> str:
    if event.retrieval is not None:
        return encode_event("retrieval", {"pages": [_page(page) for page in event.retrieval]})
    if event.citation is not None:
        return encode_event("citation", {"index": event.citation.index, "page_id": event.citation.page_id})
    if event.done is not None:
        return encode_event(
            "done",
            {
                "usage": {
                    "input_tokens": event.done.input_tokens,
                    "output_tokens": event.done.output_tokens,
                },
                "cost_usd": event.cost_usd,
                "model_id": model_id,
            },
        )
    return encode_event("token", {"text": event.text})


def _page(page: Any) -> dict[str, Any]:
    return {"index": page.index, "page_id": page.page_id, "path": page.path, "page_no": page.page_no}
