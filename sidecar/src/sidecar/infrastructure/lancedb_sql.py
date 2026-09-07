"""The SQL fragments the LanceDB adapters build.

lancedb takes a filter as a SQL string, so every id that reaches one is
quoted here rather than once per adapter. An id can arrive from the HTTP API,
so escaping is the difference between a filter and an injection.
"""

from __future__ import annotations

from collections.abc import Iterable


def literal(value: str) -> str:
    """`value` as a SQL string literal, with any quote inside it doubled."""
    return "'" + value.replace("'", "''") + "'"


def in_list(values: Iterable[str]) -> str:
    """The body of an `in (...)` clause: every value as a literal, comma separated."""
    return ", ".join(literal(value) for value in values)
