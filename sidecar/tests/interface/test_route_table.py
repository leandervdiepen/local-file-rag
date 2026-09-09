"""The route table in ARCHITECTURE.md, checked against the app's own URL map.

`docs/conventions/http-api.md` calls that table the source of truth for what
exists. It had drifted into naming six routes that were never built and
missing three that were, which is how a document stops being read. This is the
only thing that can keep it honest.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sidecar.interface.composition import build_app

pytestmark = pytest.mark.integration

ARCHITECTURE = Path(__file__).resolve().parents[3] / "docs" / "ARCHITECTURE.md"

# Flask's own, not this app's.
NOT_OURS = {"/static/<path:filename>"}


def anonymous(path: str) -> str:
    """A path with its parameter names removed, so the table may name them readably.

    `/folders/{id}` in the doc and `/folders/<folder_id>` in the code are the
    same route, and the doc is allowed to be the more readable of the two.
    """
    return re.sub(r"\{[^{}]*\}", "{}", path)


def documented() -> set[tuple[str, str]]:
    """Every method and path named in the table, as `("GET", "/health")` pairs."""
    table = ARCHITECTURE.read_text().split("| Route | Purpose |")[1].split("\n\n")[0]
    found: set[tuple[str, str]] = set()
    for cell in re.findall(r"^\|([^|]+)\|", table, re.M):
        for method, path in re.findall(r"`(GET|POST|PUT|PATCH|DELETE) ([^`?\s]+)", cell):
            found.add((method, anonymous(path.replace("\\|", "|").strip())))
    return found


def served(tmp_path: Path) -> set[tuple[str, str]]:
    """Every method and path the app actually registers, in the table's `{id}` shape."""
    app = build_app(token="t", db_path=tmp_path / "db")
    found: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        if rule.rule in NOT_OURS:
            continue
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        for method in rule.methods or set():
            if method not in {"HEAD", "OPTIONS"}:
                found.add((method, anonymous(path)))
    return found


def test_every_route_the_app_serves_has_a_row_in_the_table(tmp_path: Path) -> None:
    undocumented = served(tmp_path) - documented()

    assert not undocumented, f"these routes exist and the table does not mention them: {sorted(undocumented)}"


def test_every_row_in_the_table_is_a_route_the_app_serves(tmp_path: Path) -> None:
    imaginary = documented() - served(tmp_path)

    assert not imaginary, f"the table promises these and nothing serves them: {sorted(imaginary)}"
