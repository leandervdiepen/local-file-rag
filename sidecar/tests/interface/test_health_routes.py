from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient

from sidecar.application.health import ReportHealth
from sidecar.domain.version import VERSION
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.health_routes import build_health_blueprint
from tests.fakes.clock import FakeClock
from tests.fakes.health_probe import FakeHealthProbe

TOKEN = "test-token-123"


def _build_client() -> FlaskClient:
    app = Flask(__name__)
    register_error_handlers(app)
    register_auth(app, TOKEN)

    report_health = ReportHealth(
        clock=FakeClock(datetime(2026, 1, 1, tzinfo=UTC)),
        probe=FakeHealthProbe(model_loaded=True, db_path=Path("/tmp/sidecar-db")),
    )
    app.register_blueprint(build_health_blueprint(report_health))

    return app.test_client()


def test_health_returns_200_with_the_right_shape_when_the_token_is_right() -> None:
    client = _build_client()

    response = client.get("/health", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "version": VERSION,
        "model_loaded": True,
        "db_path": "/tmp/sidecar-db",
        "checked_at": "2026-01-01T00:00:00+00:00",
    }


def test_health_returns_401_when_the_token_is_missing() -> None:
    client = _build_client()

    response = client.get("/health")

    assert response.status_code == 401
    assert response.get_json() == {
        "error": {"code": "unauthorized", "message": "Authentication is required.", "detail": {}}
    }


def test_health_returns_401_when_the_token_is_wrong() -> None:
    client = _build_client()

    response = client.get("/health", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"
