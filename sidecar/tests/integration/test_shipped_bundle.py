"""What the shipped sidecar is allowed to contain.

D40 says Langfuse is a development tool that the shipped sidecar never
imports, "and a packaging test proves it". Until 2026-09-09 no such test
existed and the guarantee was true by accident. This is the proof.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

SOURCE = Path(__file__).resolve().parents[2] / "src" / "sidecar"
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

# Tools that may exist in a developer's environment and must never be reachable
# from the process a user runs, because each one sends somewhere.
NEVER_SHIPPED = ("langfuse", "posthog", "sentry_sdk", "mixpanel", "segment", "opentelemetry")


def python_files() -> list[Path]:
    return [path for path in SOURCE.rglob("*.py") if "__pycache__" not in path.parts]


@pytest.mark.parametrize("package", NEVER_SHIPPED)
def test_the_sidecar_never_imports_a_tool_that_phones_home(package: str) -> None:
    importing = [path for path in python_files() if f"import {package}" in path.read_text()]

    assert not importing, f"{package} is imported by {[str(p) for p in importing]}"


@pytest.mark.parametrize("package", NEVER_SHIPPED)
def test_no_such_tool_is_even_a_dependency(package: str) -> None:
    """A dependency nothing imports today is one somebody imports next week."""
    assert f'"{package}' not in PYPROJECT.read_text()
