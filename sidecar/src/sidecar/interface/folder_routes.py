"""The /folders routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, Response, jsonify, request

from sidecar.application.manage_folders import ManageFolders
from sidecar.domain.entities import Folder
from sidecar.interface.errors import error_response

_BODY_NOT_JSON = "The request body is not JSON. Send a JSON object with a path."
_PATH_MISSING = 'The request needs a path. Send a JSON body like {"path": "/Users/you/Documents"}.'


def _serialize(folder: Folder) -> dict[str, Any]:
    return {
        "id": folder.id,
        "path": str(folder.path),
        "enabled": folder.enabled,
        "added_at": folder.added_at.isoformat(),
    }


def _uncached(response: Response) -> Response:
    """The folder list changes under the client, so a stale one is worse than a slow one."""
    response.headers["Cache-Control"] = "no-store"
    return response


def build_folder_blueprint(manage: ManageFolders) -> Blueprint:
    """Build the /folders blueprint bound to one ManageFolders use case.

    A path the use case rejects leaves this layer as the `ValidationError` it
    raised, which the app's error handlers turn into a 400 carrying its
    message. Which paths are allowed is a product rule, not a wire rule.
    """
    bp = Blueprint("folders", __name__)

    @bp.get("/folders")
    def list_folders() -> Response:
        return _uncached(jsonify({"folders": [_serialize(folder) for folder in manage.list()]}))

    @bp.post("/folders")
    def add_folder() -> Response:
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error_response("invalid_request", _BODY_NOT_JSON, status=400)
        path = body.get("path")
        if not isinstance(path, str):
            return error_response("invalid_request", _PATH_MISSING, status=400)

        response = _uncached(jsonify(_serialize(manage.add(Path(path)))))
        response.status_code = 201
        return response

    @bp.delete("/folders/<folder_id>")
    def remove_folder(folder_id: str) -> Response:
        manage.remove(folder_id)
        return Response(status=204)

    return bp
