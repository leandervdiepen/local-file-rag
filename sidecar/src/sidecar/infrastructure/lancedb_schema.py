"""pyarrow schemas and row conversions for the LanceDB tables the adapters use.

Split out from `lancedb_store.py` so neither file grows past the line budget.
Every function here is a pure conversion between a domain type and a plain
`dict` row; no `lancedb.connect` call, and no query, lives in this file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa

from sidecar.domain.entities import FileKind, FileState, Folder, IndexedFile, Page
from sidecar.domain.search import PageHit
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors

FILES_TABLE = "files"
PAGES_TABLE = "pages"
FOLDERS_TABLE = "folders"
PAGE_VECTORS_TABLE = "page_vectors"

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

FOLDERS_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("path", pa.string()),
        pa.field("enabled", pa.bool_()),
        pa.field("added_at", pa.string()),
    ]
)

# A multivector column: one page is a list of patch vectors, each a fixed width
# row of float16. LanceDB scores this natively with MaxSim, and the width has
# to be fixed for it to index the column at all.
PAGE_VECTORS_SCHEMA = pa.schema(
    [
        pa.field("page_id", pa.string()),
        pa.field("vectors", pa.list_(pa.list_(pa.float16(), VECTOR_DIM))),
        pa.field("pool_factor", pa.int64()),
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


def folder_to_row(folder: Folder) -> dict[str, Any]:
    return {
        "id": folder.id,
        "path": str(folder.path),
        "enabled": folder.enabled,
        "added_at": folder.added_at.isoformat(),
    }


def row_to_folder(row: dict[str, Any]) -> Folder:
    return Folder(
        id=row["id"],
        path=Path(row["path"]),
        enabled=row["enabled"],
        added_at=datetime.fromisoformat(row["added_at"]),
    )


def row_to_hit(
    page_row: dict[str, Any],
    file_row: dict[str, Any],
    score: float,
    stage: str,
    snippet: str = "",
) -> PageHit:
    """One hit from a `pages` row and the `files` row that owns it, which carries the path and kind."""
    return PageHit(
        page_id=page_row["id"],
        file_id=page_row["file_id"],
        path=Path(file_row["path"]),
        page_no=page_row["page_no"],
        kind=FileKind(file_row["kind"]),
        score=score,
        stage=stage,
        snippet=snippet,
    )


def page_vectors_to_row(vectors: PageVectors) -> dict[str, Any]:
    return {
        "page_id": vectors.page_id,
        "vectors": vectors.vectors.astype(STORED_DTYPE).tolist(),
        "pool_factor": vectors.pool_factor,
    }


def row_to_page_vectors(row: dict[str, Any]) -> PageVectors:
    return PageVectors(
        page_id=row["page_id"],
        vectors=np.asarray(row["vectors"], dtype=STORED_DTYPE),
        pool_factor=int(row["pool_factor"]),
    )
