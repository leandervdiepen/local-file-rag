"""The composition root. The only file that names both a use case and an adapter."""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path

from flask import Flask

from sidecar.application.activity import Activity
from sidecar.application.answer_question import AnswerQuestion
from sidecar.application.apply_changes import ApplyChanges
from sidecar.application.embed_pages import EmbedPages
from sidecar.application.enforce_storage_cap import EnforceStorageCap
from sidecar.application.explain_page import ExplainPage
from sidecar.application.forget_file import ForgetFile
from sidecar.application.health import ReportHealth
from sidecar.application.index_folder import IndexFolder
from sidecar.application.indexing_jobs import IndexingJobs
from sidecar.application.list_index_files import ListIndexFiles
from sidecar.application.manage_folders import ManageFolders
from sidecar.application.ports import PageSource
from sidecar.application.pre_embed_recent import PreEmbedRecent
from sidecar.application.read_index_stats import ReadIndexStats
from sidecar.application.record_page_hit import RecordPageHit
from sidecar.application.render_page import RenderPage
from sidecar.application.run_golden_set import RunGoldenSet
from sidecar.application.search import VISUAL_CANDIDATE_LIMIT, Search
from sidecar.domain.changes import FileChange
from sidecar.domain.entities import FileKind
from sidecar.domain.eviction import DEFAULT_CAP_BYTES
from sidecar.domain.providers import PROVIDERS, ProviderId
from sidecar.infrastructure.background_loop import BackgroundLoop, Job
from sidecar.infrastructure.colqwen_embedder import DEFAULT_POOL_FACTOR, ColQwenEmbedder
from sidecar.infrastructure.filesystem_health import FilesystemHealthProbe
from sidecar.infrastructure.fs_crawler import FilesystemCrawler
from sidecar.infrastructure.fs_probe import FilesystemProbe
from sidecar.infrastructure.fs_watcher import FolderWatcher
from sidecar.infrastructure.image_pages import ImagePageSource
from sidecar.infrastructure.lancedb_folders import LanceDBFolders
from sidecar.infrastructure.lancedb_store import LanceDBStore
from sidecar.infrastructure.lancedb_vectors import LanceDBVectors
from sidecar.infrastructure.mac_power import MacPowerSource
from sidecar.infrastructure.openai_answerer import OpenAIAnswerer
from sidecar.infrastructure.pdfium_pages import PdfiumPageSource
from sidecar.infrastructure.system_clock import SystemClock
from sidecar.infrastructure.text_pages import TextFilePageSource
from sidecar.infrastructure.vision_ocr import AppleVisionTextReader
from sidecar.interface.auth import register_auth
from sidecar.interface.chat_routes import build_chat_blueprint
from sidecar.interface.cors import register_cors
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.eval_routes import build_eval_blueprint
from sidecar.interface.folder_routes import build_folder_blueprint
from sidecar.interface.health_routes import build_health_blueprint
from sidecar.interface.heatmap_routes import build_heatmap_blueprint
from sidecar.interface.index_routes import build_index_blueprint
from sidecar.interface.page_routes import build_page_blueprint
from sidecar.interface.search_routes import build_search_blueprint

logger = logging.getLogger(__name__)


def _page_sources() -> dict[FileKind, PageSource]:
    """One reader per file kind. `IndexFolder` and `RenderPage` share it, so a
    page is rendered by whatever read it."""
    return {
        FileKind.PDF: PdfiumPageSource(),
        FileKind.IMAGE: ImagePageSource(),
        FileKind.TEXT: TextFilePageSource(),
    }


def build_app(
    token: str,
    db_path: Path,
    cap_bytes: int = DEFAULT_CAP_BYTES,
    visual_candidates: int = VISUAL_CANDIDATE_LIMIT,
    pool_factor: int = DEFAULT_POOL_FACTOR,
) -> Flask:
    """Wire adapters into use cases and return a Flask app ready to serve."""
    app = Flask(__name__)

    register_error_handlers(app)
    register_cors(app)
    register_auth(app, token)

    clock = SystemClock()
    store = LanceDBStore(db_path)
    folders = LanceDBFolders(db_path, clock)
    vectors = LanceDBVectors(db_path)
    sources = _page_sources()

    # One embedder for the whole process. It owns the model, loads it on the
    # first page anyone asks for and drops it when idle, so nothing else in
    # here has to know that a 4 GB model is behind these calls.
    embedder = ColQwenEmbedder(pool_factor=pool_factor)
    embed_pages = EmbedPages(store, sources, embedder, vectors)
    search = Search(store, vectors, embedder, embed_pages, folders, visual_candidates)

    index_folder = IndexFolder(
        crawler=FilesystemCrawler(),
        probe=FilesystemProbe(),
        sources=sources,
        ocr=AppleVisionTextReader(),
        store=store,
    )

    watcher = _start_watching(ApplyChanges(index_folder, folders, store, vectors))
    manage_folders = ManageFolders(folders, watcher)
    manage_folders.resume_watching()

    app.register_blueprint(build_health_blueprint(ReportHealth(clock=clock, probe=FilesystemHealthProbe(db_path))))
    app.register_blueprint(build_folder_blueprint(manage_folders))
    jobs = IndexingJobs(index_folder, folders, store, vectors, embed_pages)
    app.register_blueprint(
        build_index_blueprint(jobs, ReadIndexStats(store, vectors), ListIndexFiles(store), ForgetFile(store, vectors))
    )
    app.register_blueprint(build_search_blueprint(search))
    render_page = RenderPage(store, sources)
    app.register_blueprint(build_page_blueprint(render_page, RecordPageHit(store, clock)))
    app.register_blueprint(build_heatmap_blueprint(ExplainPage(render_page, embedder)))
    app.register_blueprint(build_chat_blueprint(search, AnswerQuestion(render_page, _answerer())))
    app.register_blueprint(build_eval_blueprint(RunGoldenSet(search, vectors)))

    activity = Activity()
    app.before_request(activity.touch)
    _start_background(
        [
            PreEmbedRecent(store, vectors, embed_pages, MacPowerSource(), activity, jobs, cap_bytes).tick,
            EnforceStorageCap(store, vectors, cap_bytes).run,
        ]
    )

    return app


def _answerer() -> OpenAIAnswerer:
    """The provider answers go to.

    One provider for now, chosen by D38 because it is free and needs no key,
    so the app answers before the user has configured anything. The settings
    screen replaces this with a choice, and every option except Anthropic
    speaks this same wire (D36).
    """
    provider = next(p for p in PROVIDERS if p.id is ProviderId.OPENROUTER)
    return OpenAIAnswerer(base_url=provider.base_url, api_key=os.environ.get(provider.env_var))


def _start_watching(apply_changes: ApplyChanges) -> FolderWatcher:
    """The running watcher, already started and registered to stop on exit.

    Started before any folder is watched, because watchdog takes a folder at
    any time but the app has to keep the two calls in one place to be sure
    the observer thread is up before the first event can arrive.

    A batch that fails is logged, not raised. It arrives on the watcher's own
    thread, where an exception reaches nothing that could tell the user, and
    one unreadable file must not stop the folder being watched.
    """

    def on_batch(changes: list[FileChange], sizes: dict[Path, int]) -> None:
        try:
            acted = apply_changes.run(changes, sizes)
        except Exception:
            logger.exception("applying %d filesystem changes failed", len(changes))
            return
        if acted:
            logger.info("applied %d of %d filesystem changes", acted, len(changes))

    watcher = FolderWatcher(on_batch)
    watcher.start()
    atexit.register(watcher.stop)
    return watcher


def _start_background(jobs: list[Job]) -> None:
    """The loop that pre-embeds and evicts, started and registered to stop on exit.

    Pre-embedding runs before the cap, so a tick that adds vectors is the same
    tick that checks whether they fit. The reverse order would leave the store
    over its cap for a whole interval every time.
    """
    loop = BackgroundLoop(jobs)
    loop.start()
    atexit.register(loop.stop)
