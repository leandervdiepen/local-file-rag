"""The /health route."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify

from sidecar.application.health import ReportHealth


def build_health_blueprint(report_health: ReportHealth) -> Blueprint:
    """Build the /health blueprint bound to one ReportHealth use case."""
    bp = Blueprint("health", __name__)

    @bp.get("/health")
    def health() -> Response:
        report = report_health.run()
        return jsonify(
            {
                "status": report.status,
                "version": report.version,
                "model_loaded": report.model_loaded,
                "db_path": report.db_path,
                "checked_at": report.checked_at,
            }
        )

    return bp
