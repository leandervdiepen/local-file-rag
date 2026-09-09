"""A real, in-memory IndexStore. Not a mock.

Implements the same `IndexStore` contract as `LanceDBStore`: idempotent
upserts keyed by id, a silent `forget_file` for an id that is not there, an
empty list for a blank query, and an explicit filename boost so a query that
is a file's name ranks that file's pages first. Full-text matching here is
naive case-insensitive substring search rather than BM25, so ranking quality
differs from the real adapter, but every other observable behavior matches,
which is what lets other agents write unit tests against this fake with the
same expectations they would bring to the real store.
"""

from __future__ import annotations

from collections.abc import Sequence

from sidecar.domain.entities import FileState, IndexedFile, Page
from sidecar.domain.search import IndexStats, PageHit


class FakeIndexStore:
    def __init__(self) -> None:
        self._files: dict[str, IndexedFile] = {}
        self._pages: dict[str, Page] = {}

    def upsert_file(self, file: IndexedFile) -> None:
        self._files[file.id] = file

    def upsert_pages(self, pages: Sequence[Page]) -> None:
        for page in pages:
            self._pages[page.id] = page

    def forget_file(self, file_id: str) -> None:
        self._files.pop(file_id, None)
        for page_id in [pid for pid, page in self._pages.items() if page.file_id == file_id]:
            del self._pages[page_id]

    def forget_pages(self, page_ids: Sequence[str]) -> None:
        for page_id in page_ids:
            self._pages.pop(page_id, None)

    def get_file(self, file_id: str) -> IndexedFile | None:
        return self._files.get(file_id)

    def get_pages(self, file_id: str) -> list[Page]:
        return sorted((p for p in self._pages.values() if p.file_id == file_id), key=lambda page: page.page_no)

    def content_hash_of(self, file_id: str) -> str | None:
        file = self._files.get(file_id)
        return file.content_hash if file is not None else None

    def files_in_state(self, state: FileState, after_path: str | None, limit: int) -> list[IndexedFile]:
        matching = (f for f in self._files.values() if f.state is state)
        after = (f for f in matching if after_path is None or str(f.path) > after_path)
        return sorted(after, key=lambda file: str(file.path))[:limit]

    def indexed_files(self) -> list[IndexedFile]:
        indexed = (f for f in self._files.values() if f.state is FileState.TEXT_INDEXED)
        return sorted(indexed, key=lambda file: str(file.path))

    def search_pages(self, query: str, limit: int) -> list[PageHit]:
        target = query.strip().lower()
        if not target:
            return []
        seen: set[str] = set()
        hits = self._filename_hits(target, seen) + self._content_hits(target, seen)
        return hits[:limit]

    def _filename_hits(self, target: str, seen: set[str]) -> list[PageHit]:
        hits: list[PageHit] = []
        for file in sorted(self._files.values(), key=lambda f: str(f.path)):
            if file.path.name.lower() != target and file.path.stem.lower() != target:
                continue
            pages = sorted((p for p in self._pages.values() if p.file_id == file.id), key=lambda p: p.page_no)
            for page in pages:
                seen.add(page.id)
                hits.append(
                    PageHit(
                        page_id=page.id,
                        file_id=file.id,
                        path=file.path,
                        page_no=page.page_no,
                        kind=file.kind,
                        score=1.0,
                        stage="filename",
                    )
                )
        return hits

    def _content_hits(self, target: str, seen: set[str]) -> list[PageHit]:
        scored: list[tuple[int, Page]] = []
        for page in self._pages.values():
            if page.id in seen:
                continue
            count = page.text.lower().count(target)
            if count > 0:
                scored.append((count, page))
        scored.sort(key=lambda pair: (-pair[0], pair[1].file_id, pair[1].page_no))
        hits: list[PageHit] = []
        for count, page in scored:
            file = self._files.get(page.file_id)
            if file is None:
                continue
            hits.append(
                PageHit(
                    page_id=page.id,
                    file_id=page.file_id,
                    path=file.path,
                    page_no=page.page_no,
                    kind=file.kind,
                    score=float(count),
                    stage="content",
                    snippet=page.text[:200],
                )
            )
        return hits

    def stats(self) -> IndexStats:
        files = list(self._files.values())
        pages = list(self._pages.values())
        reason_counts: dict[str, int] = {}
        for file in files:
            if file.skip_reason is not None:
                reason_counts[file.skip_reason] = reason_counts.get(file.skip_reason, 0) + 1
        return IndexStats(
            files_scanned=len(files),
            files_text_indexed=sum(1 for f in files if f.state is FileState.TEXT_INDEXED),
            files_skipped=sum(1 for f in files if f.state is FileState.SKIPPED),
            pages_total=len(pages),
            # The vector store is the authority. `ReadIndexStats` replaces this
            # with its count, so a fake that guessed here would hide that.
            pages_embedded=0,
            bytes_on_disk=sum(len(p.text.encode("utf-8")) for p in pages),
            skips_by_reason=tuple(sorted(reason_counts.items())),
        )
