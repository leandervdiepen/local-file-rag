"""Adapter for the `FolderStore` port, backed by the `folders` LanceDB table.

The table is created on the first add, so an untouched directory is a valid
database and listing it is empty rather than an error. `folders` carries no
text column, so unlike `files` and `pages` it gets no FTS index.

Separate from `lancedb_store.py` because folders are a different table with a
different lifetime: a few rows the user edits, not the index the crawler
rewrites.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import lancedb
from lancedb import Table

from sidecar.application.ports import Clock
from sidecar.domain.entities import Folder
from sidecar.domain.errors import NotFoundError
from sidecar.domain.identity import file_id
from sidecar.infrastructure import lancedb_schema as schema
from sidecar.infrastructure import lancedb_sql as sql


class LanceDBFolders:
    """The folders the user chose to index, backed by the `folders` LanceDB table."""

    def __init__(self, db_path: Path, clock: Clock) -> None:
        self._db = lancedb.connect(str(db_path))
        self._clock = clock

    def add(self, path: Path) -> Folder:
        existing = self._find(file_id(path))
        if existing is not None:
            return existing
        folder = Folder.at(path=path, added_at=self._clock.now())
        self._write(folder)
        return folder

    def list(self) -> list[Folder]:
        table = self._existing_table()
        if table is None:
            return []
        folders = [schema.row_to_folder(row) for row in table.search().to_list()]
        return sorted(folders, key=lambda folder: str(folder.path))

    def remove(self, folder_id: str) -> None:
        table = self._existing_table()
        if table is not None:
            table.delete(f"id = {sql.literal(folder_id)}")

    def set_enabled(self, folder_id: str, enabled: bool) -> None:
        current = self._find(folder_id)
        if current is None:
            raise NotFoundError(f"No indexed folder has the id {folder_id}.")
        self._write(replace(current, enabled=enabled))

    def _find(self, folder_id: str) -> Folder | None:
        table = self._existing_table()
        if table is None:
            return None
        rows = table.search().where(f"id = {sql.literal(folder_id)}").to_list()
        return schema.row_to_folder(rows[0]) if rows else None

    def _write(self, folder: Folder) -> None:
        table = self._existing_table()
        if table is None:
            table = self._db.create_table(schema.FOLDERS_TABLE, schema=schema.FOLDERS_SCHEMA)
        table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(
            [schema.folder_to_row(folder)]
        )

    def _existing_table(self) -> Table | None:
        if schema.FOLDERS_TABLE not in self._db.list_tables().tables:
            return None
        return self._db.open_table(schema.FOLDERS_TABLE)
