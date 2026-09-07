"""What `IndexFolder` puts in the index. No adapter, no disk, no network.

The invariant under test is the one the use case promises: every file the
crawler found is in the index exactly once, either with its pages or with a
reason it has none. `test_index_folder_gate.py` covers the reasons.
"""

from __future__ import annotations

from sidecar.application.index_folder import MAX_OCR_PAGES_PER_FILE
from sidecar.domain.entities import FileKind, FileState
from sidecar.domain.gate import MAX_PDF_PAGES
from sidecar.domain.progress import IndexProgress
from tests.application.index_folder_world import FOLDER_ID, PDF_BYTES, World, a_mixed_world, png, snapshot


def test_a_pdf_an_image_and_a_text_file_each_land_with_their_pages() -> None:
    world = World()
    pdf = world.add("report.pdf", PDF_BYTES, ["one", "two", "three"])
    image = world.add("shot.png", png(400, 300), ["what the screenshot says"])
    text = world.add("notes.md", b"# notes", ["# notes"])

    world.run()

    assert [(world.stored(p).kind, world.stored(p).page_count) for p in (pdf, image, text)] == [
        (FileKind.PDF, 3),
        (FileKind.IMAGE, 1),
        (FileKind.TEXT, 1),
    ]
    assert [len(world.pages_of(p)) for p in (pdf, image, text)] == [3, 1, 1]
    assert {world.stored(p).state for p in (pdf, image, text)} == {FileState.TEXT_INDEXED}
    assert world.stored(pdf).content_hash != ""


def test_a_blank_page_goes_to_ocr_and_a_page_that_has_text_does_not() -> None:
    world = World()
    pdf = world.add("scan.pdf", PDF_BYTES, ["", "already extracted"])
    world.source.renders = {(pdf, 1): b"page-1-png", (pdf, 2): b"page-2-png"}
    world.ocr.texts = {b"page-1-png": "read by ocr", b"page-2-png": "never asked for"}

    world.run()

    assert [page.text for page in world.pages_of(pdf)] == ["read by ocr", "already extracted"]


def test_ocr_stops_after_the_budget_and_spends_it_on_the_pages_that_needed_it() -> None:
    world = World()
    total = MAX_OCR_PAGES_PER_FILE + 2
    pdf = world.add("scans.pdf", PDF_BYTES, ["a text layer"] + [""] * (total - 1))
    world.source.renders = {(pdf, n): f"png-{n}".encode() for n in range(1, total + 1)}
    world.ocr.texts = {f"png-{n}".encode(): f"ocr {n}" for n in range(1, total + 1)}

    world.run()

    texts = [page.text for page in world.pages_of(pdf)]
    assert texts[0] == "a text layer"
    assert texts[1:-1] == [f"ocr {n}" for n in range(2, MAX_OCR_PAGES_PER_FILE + 2)]
    assert texts[-1] == ""


def test_a_pdf_over_the_page_cap_is_truncated_and_flagged_rather_than_skipped() -> None:
    world = World()
    pdf = world.add("long.pdf", PDF_BYTES, [f"page {n}" for n in range(1, MAX_PDF_PAGES + 6)])

    world.run()

    stored = world.stored(pdf)
    assert (stored.state, stored.page_count, stored.truncated_pages) == (FileState.TEXT_INDEXED, MAX_PDF_PAGES, True)
    assert len(world.pages_of(pdf)) == MAX_PDF_PAGES


def test_running_twice_over_an_unchanged_crawl_leaves_the_store_identical() -> None:
    world = a_mixed_world()
    world.run()
    after_one_run = snapshot(world)

    world.run()

    assert snapshot(world) == after_one_run


def test_progress_counts_add_up_and_the_last_event_says_done() -> None:
    world = a_mixed_world()
    seen: list[IndexProgress] = []

    final = world.run(seen.append)

    files = len(world.crawler.files)
    assert len(seen) == files + 1
    assert [event.done for event in seen] == [False] * files + [True]
    assert all(event.current_path for event in seen[:-1])
    assert (final.done, final.current_path, final.folder_id) == (True, "", FOLDER_ID)
    assert final.files_seen == final.files_indexed + final.files_skipped == files
    assert final.pages_indexed == sum(len(world.pages_of(path)) for path in world.crawler.files)
