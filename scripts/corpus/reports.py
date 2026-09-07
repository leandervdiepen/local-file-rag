"""Renders the 30 report PDFs from corpus.report_content data."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from corpus import report_content as rc
from corpus.charts import bar_chart, line_chart, pie_chart
from corpus.manifest import Manifest
from corpus.rng import make_rng

STYLES = getSampleStyleSheet()


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _table_flowable(rows: list[list[str]]) -> Table:
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1fb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd2e0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _chart_image(chart: dict, tmp_dir: Path, name: str) -> Image:
    path = tmp_dir / f"{name}.png"
    kind = chart["kind"]
    if kind == "bar":
        bar_chart(path, chart["labels"], chart["values"], chart["title"], chart["ylabel"])
    elif kind == "pie":
        pie_chart(path, chart["labels"], chart["values"], chart["title"])
    elif kind == "line":
        line_chart(path, chart["labels"], chart["series"], chart["title"], chart["ylabel"])
    else:
        raise ValueError(kind)
    # reportlab hashes this path string for the PDF's internal XObject name,
    # so tmp_dir must be a fixed path across runs or output stops being
    # byte-identical for the same seed.
    return Image(str(path), width=5.5 * inch, height=3 * inch)


def _build_pdf(path: Path, data: dict, tmp_dir: Path, slug: str) -> None:
    doc = SimpleDocTemplate(
        str(path), pagesize=letter, invariant=1,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
    )
    flow = [Paragraph(data["title"], STYLES["Title"]), Spacer(1, 12)]
    flow.append(Paragraph(data["intro"], STYLES["BodyText"]))
    flow.append(Spacer(1, 16))

    if data.get("chart_only_page"):
        flow.append(PageBreak())
        flow.append(_chart_image(data["chart"], tmp_dir, slug))
        flow.append(PageBreak())
        flow.append(Paragraph(data["narrative"], STYLES["BodyText"]))
    else:
        if "table" in data:
            flow.append(_table_flowable(data["table"]))
            flow.append(Spacer(1, 16))
        if "chart" in data:
            flow.append(_chart_image(data["chart"], tmp_dir, slug))
        if "outro" in data:
            flow.append(Spacer(1, 16))
            flow.append(Paragraph(data["outro"], STYLES["BodyText"]))
    doc.build(flow)


PLAN = [
    ("quarterly", rc.quarterly, 8),
    ("infra-cost", rc.infra_cost, 7),
    ("experiments", rc.experiment, 6),
    ("board", rc.board_update, 6),
]


def generate(seed: int, root: Path, manifest: Manifest, tmp_dir: Path) -> int:
    out_root = root / "reports"
    count = 0

    for dirname, fn, n in PLAN:
        out_dir = out_root / dirname
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            rng = make_rng(seed, f"report:{dirname}:{i}")
            force = dirname == "experiments" and i == 0
            data = fn(rng, seed, i, force_signup_jump=force) if force else fn(rng, seed, i)
            slug = "landing-page-signup-jump" if force else f"{_slug(data['title'])}-{i}"
            path = out_dir / f"{slug}.pdf"
            _build_pdf(path, data, tmp_dir, slug)
            manifest.add_indexed(path, "reports")
            count += 1

    invoice_dir = out_root / "invoices"
    invoice_dir.mkdir(parents=True, exist_ok=True)
    hero_rng = make_rng(seed, "report:invoice:hero")
    hero = rc.invoice(hero_rng, seed, 0, hero=True)
    hero_path = invoice_dir / "hosting-q2-2026.pdf"
    _build_pdf(hero_path, hero, tmp_dir, "hosting-q2-2026")
    manifest.add_indexed(hero_path, "reports")
    count += 1

    for i, (slug, period) in enumerate([
        ("compute-q1-2026", "Q1 2026"), ("saas-tools-q3-2026", "Q3 2026"),
    ]):
        rng = make_rng(seed, f"report:invoice:{i}")
        data = rc.invoice(rng, seed, i, period=period)
        path = invoice_dir / f"{slug}.pdf"
        _build_pdf(path, data, tmp_dir, slug)
        manifest.add_indexed(path, "reports")
        count += 1

    return count
