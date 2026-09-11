"""What the shipped sidecar is allowed to contain.

D40 says Langfuse is a development tool that the shipped sidecar never
imports, "and a packaging test proves it". Until 2026-09-09 no such test
existed and the guarantee was true by accident. This is the proof.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

SOURCE = Path(__file__).resolve().parents[2] / "src" / "sidecar"
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
APP = Path(__file__).resolve().parents[3] / "app"

# Tools that may exist in a developer's environment and must never be reachable
# from the process a user runs, because each one sends somewhere.
NEVER_SHIPPED = ("langfuse", "posthog", "sentry_sdk", "mixpanel", "segment", "opentelemetry")

# The same rule for the other process. README.md and SECURITY.md both claim
# there is no analytics and no crash reporting in the app, and until now only
# half the app was held to it: the Python side had this test and the Electron
# side had nobody checking. A claim about two processes needs two tests.
NEVER_SHIPPED_JS = (
    "@sentry/",
    "posthog-js",
    "posthog-node",
    "mixpanel",
    "@amplitude/",
    "analytics-node",
    "@segment/",
    "bugsnag",
    "rollbar",
    "electron-updater",
)


def python_files() -> list[Path]:
    return [path for path in SOURCE.rglob("*.py") if "__pycache__" not in path.parts]


@pytest.mark.parametrize("package", NEVER_SHIPPED)
def test_the_sidecar_never_imports_a_tool_that_phones_home(package: str) -> None:
    """Both import forms. Checking only `import x` misses `from x import y`, which is the one people write."""
    importing = [
        path
        for path in python_files()
        if re.search(rf"^\s*(?:import {package}\b|from {package}[.\s])", path.read_text(), re.M)
    ]

    assert not importing, f"{package} is imported by {[str(p) for p in importing]}"


@pytest.mark.parametrize("package", NEVER_SHIPPED)
def test_no_such_tool_is_even_a_dependency(package: str) -> None:
    """A dependency nothing imports today is one somebody imports next week."""
    assert f'"{package}' not in PYPROJECT.read_text()


def app_sources() -> list[Path]:
    source = APP / "src"
    return [path for path in source.rglob("*.ts") if path.is_file()] + [
        path for path in source.rglob("*.tsx") if path.is_file()
    ]


@pytest.mark.parametrize("package", NEVER_SHIPPED_JS)
def test_the_app_never_imports_a_tool_that_phones_home(package: str) -> None:
    """`electron-updater` is in here because an auto updater is a call home on every launch."""
    importing = [path for path in app_sources() if re.search(rf"""['\"]{re.escape(package)}""", path.read_text())]

    assert not importing, f"{package} is imported by {[str(p) for p in importing]}"


@pytest.mark.parametrize("package", NEVER_SHIPPED_JS)
def test_no_such_tool_is_even_an_app_dependency(package: str) -> None:
    assert f'"{package}' not in (APP / "package.json").read_text()
