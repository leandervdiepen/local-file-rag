"""pyarrow schemas and row conversions for the LanceDB tables `LanceDBStore` uses.

Split out from `lancedb_store.py` so neither file grows past the line budget.
Every function here is a pure conversion between a domain type and a plain
`dict` row; no `lancedb.connect` call, and no query, lives in this file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa

from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page

FILES_TABLE = "files"
PAGES_TABLE = "pages"

# `text` on `files` carries the filename, not file content: `IndexedFile` never
# carries raw text, so the filename is the only thing there is to index for a
# files-table FTS match. See `lancedb_store._filename_hits`.
FILES_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("path", pa.string()),
        pa.field("folder_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("size_bytes", pa.int64()),
        pa.field("mtime", pa.string()),
        pa.field("kind", pa.string()),
        pa.field("state", pa.string()),
        pa.field("skip_reason", pa.string()),
        pa.field("page_count", pa.int64()),
        pa.field("last_used", pa.string()),
        pa.field("truncated_pages", pa.bool_()),
        pa.field("text", pa.string()),
    ]
)

PAGES_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("file_id", pa.string()),
        pa.field("page_no", pa.int64()),
        pa.field("text", pa.string()),
        pa.field("embedded_at", pa.string()),
        pa.field("last_hit_at", pa.string()),
        pa.field("hit_count", pa.int64()),
    ]
)


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def file_to_row(file: IndexedFile) -> dict[str, Any]:
    """The row `upsert_file` writes."""
    return {
        "id": file.id,
        "path": str(file.path),
        "folder_id": file.folder_id,
        "content_hash": file.content_hash,
        "size_bytes": file.size_bytes,
        "mtime": file.mtime.isoformat(),
        "kind": file.kind.value,
        "state": file.state.value,
        "skip_reason": file.skip_reason,
        "page_count": file.page_count,
        "last_used": _to_iso(file.last_used),
        "truncated_pages": file.truncated_pages,
        "text": file.path.name,
    }


def row_to_file(row: dict[str, Any]) -> IndexedFile:
    """Rebuilds the `IndexedFile` `upsert_file` wrote. `text` never comes back: it is a write-only projection."""
    return IndexedFile(
        id=row["id"],
        path=Path(row["path"]),
        folder_id=row["folder_id"],
        content_hash=row["content_hash"],
        size_bytes=row["size_bytes"],
        mtime=datetime.fromisoformat(row["mtime"]),
        kind=FileKind(row["kind"]),
        state=FileState(row["state"]),
        skip_reason=row["skip_reason"],
        page_count=row["page_count"],
        last_used=_from_iso(row["last_used"]),
        truncated_pages=row["truncated_pages"],
    )


def page_to_row(page: Page) -> dict[str, Any]:
    return {
        "id": page.id,
        "file_id": page.file_id,
        "page_no": page.page_no,
        "text": page.text,
        "embedded_at": _to_iso(page.embedded_at),
        "last_hit_at": _to_iso(page.last_hit_at),
        "hit_count": page.hit_count,
    }


def row_to_page(row: dict[str, Any]) -> Page:
    return Page(
        id=row["id"],
        file_id=row["file_id"],
        page_no=row["page_no"],
        text=row["text"],
        embedded_at=_from_iso(row["embedded_at"]),
        last_hit_at=_from_iso(row["last_hit_at"]),
        hit_count=row["hit_count"],
    )
