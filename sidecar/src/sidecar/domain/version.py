"""The sidecar's own version, as reported through /health.

Read from package metadata so the version has one source of truth: the
`version` field in `pyproject.toml`, not a second copy hardcoded here.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    VERSION = version("sidecar")
except PackageNotFoundError:
    VERSION = "0.0.0-dev"
