"""The composition root. The only file that names both a use case and an adapter."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from sidecar.application.embed_pages import EmbedPages
from sidecar.application.health import ReportHealth
from sidecar.application.index_folder import IndexFolder
from sidecar.application.indexing_jobs import IndexingJobs
from sidecar.application.manage_folders import ManageFolders
from sidecar.application.ports import PageSource
from sidecar.application.read_index_stats import ReadIndexStats
from sidecar.application.render_page import RenderPage
from sidecar.application.search import Search
from sidecar.domain.entities import FileKind
from sidecar.infrastructure.filesystem_health import FilesystemHealthProbe
from sidecar.infrastructure.fs_crawler import FilesystemCrawler
from sidecar.infrastructure.fs_probe import FilesystemProbe
from sidecar.infrastructure.colqwen_embedder import ColQwenEmbedder
from sidecar.infrastructure.image_pages import ImagePageSource
from sidecar.infrastructure.lancedb_folders import LanceDBFolders
from sidecar.infrastructure.lancedb_store import LanceDBStore
from sidecar.infrastructure.lancedb_vectors import LanceDBVectors
from sidecar.infrastructure.pdfium_pages import PdfiumPageSource
from sidecar.infrastructure.system_clock import SystemClock
from sidecar.infrastructure.text_pages import TextFilePageSource
from sidecar.infrastructure.vision_ocr import AppleVisionTextReader
from sidecar.interface.auth import register_auth
from sidecar.interface.errors import register_error_handlers
from sidecar.interface.folder_routes import build_folder_blueprint
from sidecar.interface.health_routes import build_health_blueprint
from sidecar.interface.index_routes import build_index_blueprint
from sidecar.interface.page_routes import build_page_blueprint
from sidecar.interface.search_routes import build_search_blueprint


def _page_sources() -> dict[FileKind, PageSource]:
    """One reader per file kind. `IndexFolder` and `RenderPage` share it, so a
    page is rendered by whatever read it."""
    return {
        FileKind.PDF: PdfiumPageSource(),
        FileKind.IMAGE: ImagePageSource(),
        FileKind.TEXT: TextFilePageSource(),
    }


def build_app(token: str, db_path: Path) -> Flask:
    """Wire adapters into use cases and return a Flask app ready to serve."""
    app = Flask(__name__)

    register_error_handlers(app)
    register_auth(app, token)

    clock = SystemClock()
    store = LanceDBStore(db_path)
    folders = LanceDBFolders(db_path, clock)
    vectors = LanceDBVectors(db_path)
    sources = _page_sources()

    # One embedder for the whole process. It owns the model, loads it on the
    # first page anyone asks for and drops it when idle, so nothing else in
    # here has to know that a 4 GB model is behind these calls.
    embedder = ColQwenEmbedder()
    embed_pages = EmbedPages(store, sources, embedder, vectors, clock)

    index_folder = IndexFolder(
        crawler=FilesystemCrawler(),
        probe=FilesystemProbe(),
        sources=sources,
        ocr=AppleVisionTextReader(),
        store=store,
    )

    app.register_blueprint(build_health_blueprint(ReportHealth(clock=clock, probe=FilesystemHealthProbe(db_path))))
    app.register_blueprint(build_folder_blueprint(ManageFolders(folders)))
    app.register_blueprint(build_index_blueprint(IndexingJobs(index_folder, folders), ReadIndexStats(store)))
    app.register_blueprint(build_search_blueprint(Search(store, vectors, embedder, embed_pages)))
    app.register_blueprint(build_page_blueprint(RenderPage(store, sources)))

    return app
