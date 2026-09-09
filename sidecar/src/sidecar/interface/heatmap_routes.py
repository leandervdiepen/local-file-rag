"""The /pages/{id}/heatmap route."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from sidecar.application.explain_page import ExplainPage
from sidecar.domain.heatmap import DEFAULT_THRESHOLD_PERCENTILE, Heatmap, threshold_at
from sidecar.interface.errors import error_response

_MISSING_QUERY_MESSAGE = "A heatmap needs a q parameter naming the query to explain."


def build_heatmap_blueprint(explain: ExplainPage) -> Blueprint:
    """Build the heatmap blueprint bound to one ExplainPage use case.

    The grid goes over the wire as plain numbers rather than an image, so the
    renderer can redraw it at any threshold and for any token without asking
    again. That is what makes the slider feel instant.
    """
    bp = Blueprint("heatmap", __name__)

    @bp.get("/pages/<page_id>/heatmap")
    def page_heatmap(page_id: str) -> Response:
        query = request.args.get("q")
        if query is None or not query.strip():
            return error_response("missing_query", _MISSING_QUERY_MESSAGE, status=400)

        heatmap = explain.run(page_id, query)
        response = jsonify(_body(heatmap))
        # The page image is immutable but this is not: it depends on the query
        # and on a model that may be a different build tomorrow.
        response.headers["Cache-Control"] = "no-store"
        return response

    return bp


def _body(heatmap: Heatmap) -> dict[str, Any]:
    return {
        "rows": heatmap.grid.rows,
        "cols": heatmap.grid.cols,
        "combined": heatmap.combined.tolist(),
        "threshold": threshold_at(heatmap.combined, DEFAULT_THRESHOLD_PERCENTILE),
        "threshold_percentile": DEFAULT_THRESHOLD_PERCENTILE,
        "tokens": [{"token": token.token, "values": token.values.tolist()} for token in heatmap.tokens],
    }
