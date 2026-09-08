"""Adapter for the `VectorStore` port, backed by the `page_vectors` LanceDB table.

Separate from `lancedb_store.py` because these rows have a different life: they
are the expensive part of the index, they can be thrown away and rebuilt from
the page image, and they are the only thing in the database with a vector index
on it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import lancedb
from lancedb import Table
from lancedb.index import IvfFlat

from sidecar.domain.vectors import PageVectors, QueryVectors
from sidecar.infrastructure import lancedb_schema as schema
from sidecar.infrastructure import lancedb_sql as sql

logger = logging.getLogger(__name__)

# Below this, a brute force scan beats an approximate index and the index costs
# more to build than it saves. Counted in pages, which is what `count_rows`
# reports on a multivector table; each page is a few hundred vectors underneath.
DEFAULT_INDEX_THRESHOLD_ROWS = 2000

# Multivector search in LanceDB supports cosine only.
INDEX_METRIC: Literal["cosine"] = "cosine"
VECTOR_COLUMN = "vectors"


class LanceDBVectors:
    """Page vectors, and the only search that looks at every page rather than a candidate set."""

    def __init__(self, db_path: Path, index_threshold_rows: int = DEFAULT_INDEX_THRESHOLD_ROWS) -> None:
        self._db = lancedb.connect(str(db_path))
        self._index_threshold_rows = index_threshold_rows

    def put_vectors(self, vectors: Sequence[PageVectors]) -> None:
        if not vectors:
            return
        table = self._table_for_write()
        rows = [schema.page_vectors_to_row(item) for item in vectors]
        table.merge_insert("page_id").when_matched_update_all().when_not_matched_insert_all().execute(rows)
        self._index_when_worth_it(table)

    def get_vectors(self, page_ids: Sequence[str]) -> dict[str, PageVectors]:
        rows = self._rows_for(page_ids)
        return {str(row["page_id"]): schema.row_to_page_vectors(row) for row in rows}

    def embedded_ids(self, page_ids: Sequence[str]) -> set[str]:
        return {str(row["page_id"]) for row in self._rows_for(page_ids, columns=["page_id"])}

    def nearest(self, query: QueryVectors, limit: int) -> list[tuple[str, float]]:
        table = self._existing_table()
        if table is None:
            return []
        found = table.search(query.vectors.astype("float32").tolist()).select(["page_id"]).limit(limit).to_list()
        # LanceDB returns `_distance`, where smaller is closer. The port says
        # higher is better, so it is negated rather than rescaled: the value is
        # only ever compared with others from this same call.
        return [(str(row["page_id"]), -float(row["_distance"])) for row in found]

    def count(self) -> int:
        table = self._existing_table()
        return 0 if table is None else table.count_rows()

    def _rows_for(self, page_ids: Sequence[str], columns: list[str] | None = None) -> list[dict[str, Any]]:
        table = self._existing_table()
        # `in ()` with nothing in it is a parse error in lancedb 0.38, not an
        # empty result, so an empty ask never reaches the database.
        if table is None or not page_ids:
            return []
        search = table.search()
        if columns is not None:
            search = search.select(columns)
        rows: list[dict[str, Any]] = search.where(f"page_id in ({sql.in_list(page_ids)})").to_list()
        return rows

    def _table_for_write(self) -> Table:
        existing = self._existing_table()
        if existing is not None:
            return existing
        return self._db.create_table(schema.PAGE_VECTORS_TABLE, schema=schema.PAGE_VECTORS_SCHEMA)

    def _existing_table(self) -> Table | None:
        # `table_exists()` raises NotImplementedError on a local connection in
        # lancedb 0.38, so the table list is the way to ask.
        if schema.PAGE_VECTORS_TABLE not in self._db.list_tables().tables:
            return None
        return self._db.open_table(schema.PAGE_VECTORS_TABLE)

    def _index_when_worth_it(self, table: Table) -> None:
        """Build the vector index once the table is big enough to need one.

        Here rather than in a use case because the threshold is about what
        LanceDB costs to scan, not about anything the product decided.
        """
        if self._has_index(table) or table.count_rows() < self._index_threshold_rows:
            return
        # Flat, not product quantized: PQ needs 256 vectors to train and trades
        # accuracy for memory this store does not need, since a desktop index
        # is thousands of pages rather than millions.
        try:
            table.create_index(VECTOR_COLUMN, config=IvfFlat(distance_type=INDEX_METRIC))
        except (RuntimeError, ValueError):
            # Too little data to train on yet. The next write tries again, and
            # an unindexed table still searches, just by scanning.
            logger.info("page_vectors is not ready for an index yet, still scanning")
            return
        logger.info("indexed page_vectors at %d pages", table.count_rows())

    @staticmethod
    def _has_index(table: Table) -> bool:
        return any(getattr(index, "columns", []) == [VECTOR_COLUMN] for index in table.list_indices())
