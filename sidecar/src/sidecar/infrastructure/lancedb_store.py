"""Adapter for the `IndexStore` port, backed by a LanceDB database directory.

Tables are created lazily, on first write, so an untouched directory is a
valid database. Each table gets its BM25 index at creation time, before any
row exists: lancedb 0.38.0 raises `ValueError` from a search against a table
that has never had `create_index` called on it, so waiting for the first row
would leave a window where `search_pages` breaks.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import lancedb
from lancedb import Table
from lancedb.index import FTS

from sidecar.domain.entities import FileState, IndexedFile, Page
from sidecar.domain.search import IndexStats, PageHit
from sidecar.infrastructure import lancedb_schema as schema
from sidecar.infrastructure import lancedb_sql as sql

_FILENAME_CANDIDATE_LIMIT = 200
_FILENAME_SCORE = 1.0
_SNIPPET_LENGTH = 200


class LanceDBStore:
    """The one place index state lives, backed by the `files` and `pages` LanceDB tables."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db = lancedb.connect(str(db_path))

    def upsert_file(self, file: IndexedFile) -> None:
        table = self._table_for_write(schema.FILES_TABLE, schema.FILES_SCHEMA)
        table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(
            [schema.file_to_row(file)]
        )

    def upsert_pages(self, pages: Sequence[Page]) -> None:
        if not pages:
            return
        table = self._table_for_write(schema.PAGES_TABLE, schema.PAGES_SCHEMA)
        rows = [schema.page_to_row(page) for page in pages]
        table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows)

    def forget_file(self, file_id: str) -> None:
        files_table = self._existing_table(schema.FILES_TABLE)
        if files_table is not None:
            files_table.delete(f"id = {sql.literal(file_id)}")
        pages_table = self._existing_table(schema.PAGES_TABLE)
        if pages_table is not None:
            pages_table.delete(f"file_id = {sql.literal(file_id)}")

    def get_file(self, file_id: str) -> IndexedFile | None:
        rows = self._rows_where(schema.FILES_TABLE, f"id = {sql.literal(file_id)}")
        return schema.row_to_file(rows[0]) if rows else None

    def get_pages(self, file_id: str) -> list[Page]:
        rows = self._rows_where(schema.PAGES_TABLE, f"file_id = {sql.literal(file_id)}")
        return sorted((schema.row_to_page(row) for row in rows), key=lambda page: page.page_no)

    def content_hash_of(self, file_id: str) -> str | None:
        rows = self._rows_where(schema.FILES_TABLE, f"id = {sql.literal(file_id)}", columns=["content_hash"])
        return str(rows[0]["content_hash"]) if rows else None

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        stripped = query.strip()
        if not stripped:
            return []
        pages_table = self._existing_table(schema.PAGES_TABLE)
        if pages_table is None:
            return []
        hits: list[PageHit] = []
        seen: set[str] = set()
        for hit in self._filename_hits(stripped, pages_table) + self._content_hits(stripped, pages_table, limit):
            if hit.page_id not in seen:
                seen.add(hit.page_id)
                hits.append(hit)
        return hits[:limit]

    def stats(self) -> IndexStats:
        files_scanned = files_text_indexed = files_skipped = 0
        skips_by_reason: tuple[tuple[str, int], ...] = ()
        files_table = self._existing_table(schema.FILES_TABLE)
        if files_table is not None:
            files_scanned = files_table.count_rows()
            files_text_indexed = files_table.count_rows(f"state = '{FileState.TEXT_INDEXED.value}'")
            files_skipped = files_table.count_rows(f"state = '{FileState.SKIPPED.value}'")
            reasons = files_table.search().select(["skip_reason"]).where("skip_reason IS NOT NULL").to_list()
            reason_counts: dict[str, int] = {}
            for row in reasons:
                reason_counts[row["skip_reason"]] = reason_counts.get(row["skip_reason"], 0) + 1
            skips_by_reason = tuple(sorted(reason_counts.items()))
        pages_total = pages_embedded = 0
        pages_table = self._existing_table(schema.PAGES_TABLE)
        if pages_table is not None:
            pages_total = pages_table.count_rows()
            pages_embedded = pages_table.count_rows("embedded_at IS NOT NULL")
        return IndexStats(
            files_scanned=files_scanned,
            files_text_indexed=files_text_indexed,
            files_skipped=files_skipped,
            pages_total=pages_total,
            pages_embedded=pages_embedded,
            bytes_on_disk=_directory_size(self._db_path),
            skips_by_reason=skips_by_reason,
        )

    def _rows_where(self, name: str, predicate: str, columns: list[str] | None = None) -> list[dict[str, Any]]:
        table = self._existing_table(name)
        if table is None:
            return []
        search = table.search()
        if columns is not None:
            search = search.select(columns)
        rows: list[dict[str, Any]] = search.where(predicate).to_list()
        return rows

    def _table_for_write(self, name: str, table_schema: Any) -> Table:
        existing = self._existing_table(name)
        if existing is not None:
            return existing
        table = self._db.create_table(name, schema=table_schema)
        table.create_index("text", config=FTS())
        return table

    def _existing_table(self, name: str) -> Table | None:
        if name not in self._db.list_tables().tables:
            return None
        return self._db.open_table(name)

    def _filename_hits(self, query: str, pages_table: Table) -> list[PageHit]:
        """A query equal to a file's name, with or without extension, ranks that file's pages first.

        Explicit rather than left to BM25: the `files` FTS index only narrows candidates,
        an exact case-insensitive comparison against each candidate's name decides the boost.
        """
        files_table = self._existing_table(schema.FILES_TABLE)
        if files_table is None:
            return []
        try:
            # A search box takes whatever was typed. lancedb 0.38.0 does not raise on the
            # malformed FTS queries this was tested against, but the query parser is not
            # part of the contract, so this stays defensive rather than an exact except.
            # `_score` is unused here and asked for anyway: lance warns on every
            # search whose projection leaves it out, and that warning would land
            # in the app log on every keystroke.
            candidates = (
                files_table.search(query, query_type="fts")
                .select(["id", "path", "kind", "_score"])
                .limit(_FILENAME_CANDIDATE_LIMIT)
                .to_list()
            )
        except Exception:
            return []
        target = query.lower()
        matched = {row["id"]: row for row in candidates if _matches_name(row["path"], target)}
        if not matched:
            return []
        rows = pages_table.search().where(f"file_id in ({sql.in_list(matched.keys())})").to_list()
        rows.sort(key=lambda row: (row["file_id"], row["page_no"]))
        return [schema.row_to_hit(row, matched[row["file_id"]], _FILENAME_SCORE, "filename") for row in rows]

    def _content_hits(self, query: str, pages_table: Table, limit: int) -> list[PageHit]:
        try:
            rows = pages_table.search(query, query_type="fts").limit(limit).to_list()
        except Exception:  # see the comment in `_filename_hits`
            return []
        if not rows:
            return []
        file_ids = {row["file_id"] for row in rows}
        files_table = self._existing_table(schema.FILES_TABLE)
        file_by_id: dict[str, Any] = {}
        if files_table is not None:
            found = files_table.search().select(["id", "path", "kind"]).where(f"id in ({sql.in_list(file_ids)})")
            file_by_id = {row["id"]: row for row in found.to_list()}
        hits = []
        for row in rows:
            file_row = file_by_id.get(row["file_id"])
            if file_row is not None:
                snippet = row["text"][:_SNIPPET_LENGTH]
                hits.append(schema.row_to_hit(row, file_row, row["_score"], "content", snippet))
        return hits


def _directory_size(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(entry.stat().st_size for entry in root.rglob("*") if entry.is_file())


def _matches_name(path_str: str, target_lower: str) -> bool:
    path = Path(path_str)
    return path.name.lower() == target_lower or path.stem.lower() == target_lower
