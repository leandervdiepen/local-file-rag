"""The /pages/{id}/image route."""

from __future__ import annotations

from flask import Blueprint, Response, request

from sidecar.application.record_page_hit import RecordPageHit
from sidecar.application.render_page import PageImageSize, RenderPage
from sidecar.interface.errors import error_response

# A page id names one page of one file's content, so the picture behind it
# never changes. Anything short of forever makes a scrolled result grid
# re-fetch thumbnails it already holds.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"


def _parse_size(requested: str) -> PageImageSize | None:
    try:
        return PageImageSize(requested)
    except ValueError:
        return None


def _etag(content_hash: str, size: PageImageSize) -> str:
    """The same page at two sizes is two resources, so the size is part of the identity."""
    return f"{content_hash}-{size.value}"


def _cacheable(response: Response, etag: str) -> Response:
    response.set_etag(etag)
    response.headers["Cache-Control"] = IMMUTABLE_CACHE_CONTROL
    return response


def build_page_blueprint(render: RenderPage, record_hit: RecordPageHit) -> Blueprint:
    """Build the page image blueprint bound to one RenderPage use case.

    A full size image is the user opening the page, so it counts as a hit. A
    thumbnail is not: the result grid fetches one for every result, and
    counting those would say the whole result set was wanted equally.
    """
    bp = Blueprint("pages", __name__)

    @bp.get("/pages/<page_id>/image")
    def page_image(page_id: str) -> Response:
        requested = request.args.get("size", PageImageSize.THUMB.value)
        size = _parse_size(requested)
        if size is None:
            return error_response(
                "invalid_size",
                "That size does not exist. Ask for thumb or full.",
                status=400,
                detail={"size": requested},
            )

        etag = _etag(render.content_hash_for(page_id), size)
        if size is PageImageSize.FULL:
            # Before the 304, because a page the browser already holds was
            # still opened, and the cap must not evict it for being cached.
            record_hit.run([page_id])
        if request.if_none_match.contains(etag):
            return _cacheable(Response(status=304), etag)

        return _cacheable(Response(render.run(page_id, size), mimetype="image/png"), etag)

    return bp
