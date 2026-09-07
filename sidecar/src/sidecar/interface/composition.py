"""The composition root. The only file that names both a use case and an adapter."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from sidecar.application.health import ReportHealth
from sidecar.infrastructure.filesystem_health import FilesystemHealthProbe
from sidecar.infrastructure.system_clock import SystemClock
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.health_routes import build_health_blueprint


def build_app(token: str, db_path: Path) -> Flask:
    """Wire adapters into use cases and return a Flask app ready to serve."""
    app = Flask(__name__)

    register_error_handlers(app)
    register_auth(app, token)

    report_health = ReportHealth(clock=SystemClock(), probe=FilesystemHealthProbe(db_path))
    app.register_blueprint(build_health_blueprint(report_health))

    return app
