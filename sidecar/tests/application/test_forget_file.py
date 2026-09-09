"""`ForgetFile` over the in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from sidecar.application.forget_file import ForgetFile
from sidecar.domain.entities import FileKind, FileState, IndexedFile, Page
from sidecar.domain.identity import file_id, page_id
from sidecar.domain.vectors import STORED_DTYPE, VECTOR_DIM, PageVectors
from tests.fakes.index_store import FakeIndexStore
from tests.fakes.vector_store import FakeVectorStore

NOW = datetime(2026, 9, 9, tzinfo=UTC)
REPORT = Path("/corpus/passport-scan.pdf")


def a_world() -> tuple[ForgetFile, FakeIndexStore, FakeVectorStore, str]:
    store, vectors = FakeIndexStore(), FakeVectorStore()
    owner = file_id(REPORT)
    store.upsert_file(
        IndexedFile(
            id=owner,
            path=REPORT,
            folder_id="d1",
            content_hash="hash",
            size_bytes=1024,
            mtime=NOW,
            kind=FileKind.PDF,
            state=FileState.TEXT_INDEXED,
            page_count=2,
        )
    )
    store.upsert_pages([Page(id=page_id(owner, n), file_id=owner, page_no=n, text="private") for n in (1, 2)])
    vectors.put_vectors(
        [
            PageVectors(page_id=page_id(owner, n), vectors=np.ones((3, VECTOR_DIM), dtype=STORED_DTYPE), pool_factor=3)
            for n in (1, 2)
        ]
    )
    return ForgetFile(store, vectors), store, vectors, owner


def test_forgetting_a_file_leaves_no_row_and_no_vectors() -> None:
    use_case, store, vectors, owner = a_world()

    use_case.run(owner)

    assert store.get_file(owner) is None
    assert store.get_pages(owner) == []
    assert vectors.count() == 0


def test_a_forgotten_file_is_no_longer_a_search_result() -> None:
    use_case, store, _, owner = a_world()

    use_case.run(owner)

    assert store.search_pages("private", limit=5) == []


def test_forgetting_a_file_that_is_not_there_is_silent() -> None:
    use_case, _, _, _ = a_world()

    use_case.run("nothing")


def test_forgetting_one_file_leaves_the_others_alone() -> None:
    use_case, store, vectors, owner = a_world()
    other = file_id(Path("/corpus/keep.pdf"))
    store.upsert_pages([Page(id=page_id(other, 1), file_id=other, page_no=1)])
    vectors.put_vectors(
        [PageVectors(page_id=page_id(other, 1), vectors=np.ones((3, VECTOR_DIM), dtype=STORED_DTYPE), pool_factor=3)]
    )

    use_case.run(owner)

    assert store.get_pages(other) != []
    assert vectors.count() == 1
