"""Renders the 10 slide decks as landscape PDFs via reportlab's raw canvas.

Platypus is not used here: slide layout needs exact placement per slide,
not flowing text, and each deck is only a handful of pages.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as canvas_mod

from corpus import deck_content as dc
from corpus.charts import bar_chart, funnel_chart, line_chart, pie_chart
from corpus.manifest import Manifest

PAGE = (960, 540)
INK = HexColor("#18181b")
MUTED = HexColor("#71717a")
ACCENT = HexColor("#3b5bdb")


def _chart_path(tmp_dir: Path, deck_slug: str, index: int) -> Path:
    return tmp_dir / f"{deck_slug}-slide{index}.png"


def _render_chart(chart: dict, path: Path) -> None:
    kind = chart["kind"]
    if kind == "bar":
        bar_chart(path, chart["labels"], chart["values"], chart["title"], chart["ylabel"])
    elif kind == "pie":
        pie_chart(path, chart["labels"], chart["values"], chart["title"])
    elif kind == "line":
        line_chart(path, chart["labels"], chart["series"], chart["title"], chart["ylabel"])
    elif kind == "funnel":
        funnel_chart(path, chart["stages"], chart["values"])
    else:
        raise ValueError(kind)


def _draw_title(c: canvas_mod.Canvas, title: str, subtitle: str) -> None:
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(PAGE[0] / 2, PAGE[1] / 2 + 10, title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 18)
        c.drawCentredString(PAGE[0] / 2, PAGE[1] / 2 - 26, subtitle)


def _draw_bullets(c: canvas_mod.Canvas, title: str, items: list[str]) -> None:
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(60, PAGE[1] - 90, title)
    c.setFont("Helvetica", 17)
    y = PAGE[1] - 160
    for item in items:
        c.setFillColor(ACCENT)
        c.circle(66, y + 5, 3, fill=1, stroke=0)
        c.setFillColor(INK)
        c.drawString(84, y, item)
        y -= 42


def _draw_chart_slide(c: canvas_mod.Canvas, title: str, image_path: Path) -> None:
    if title:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(60, PAGE[1] - 70, title)
        img_top = PAGE[1] - 110
    else:
        img_top = PAGE[1] - 40
    # ImageReader hashes pixel content, not the temp-file path, so the
    # PDF's internal object naming stays stable across runs.
    c.drawImage(ImageReader(str(image_path)), 120, 40, width=720,
                height=img_top - 40, preserveAspectRatio=True, anchor="n")


def _render_deck(path: Path, deck: dict, tmp_dir: Path, seed: int) -> None:
    c = canvas_mod.Canvas(str(path), pagesize=PAGE, invariant=1)
    slug = path.stem
    for i, slide in enumerate(deck["slides"]):
        kind = slide["kind"]
        if kind == "title":
            _draw_title(c, slide["title"], slide["subtitle"])
        elif kind == "bullets":
            _draw_bullets(c, slide["title"], slide["items"])
        elif kind in ("chart", "chart_bare"):
            img_path = _chart_path(tmp_dir, slug, i)
            _render_chart(slide["chart"], img_path)
            _draw_chart_slide(c, slide.get("title", ""), img_path)
        else:
            raise ValueError(kind)
        c.showPage()
    c.save()


def generate(seed: int, root: Path, manifest: Manifest, tmp_dir: Path) -> int:
    out_dir = root / "decks"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for deck in dc.all_decks(seed):
        path = out_dir / deck["filename"]
        _render_deck(path, deck, tmp_dir, seed)
        manifest.add_indexed(path, "decks")
        count += 1
    return count
