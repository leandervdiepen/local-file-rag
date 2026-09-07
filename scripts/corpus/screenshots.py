"""Renders the 40 screenshots with Playwright and names them like real ones."""

from __future__ import annotations

from pathlib import Path

from datetime import timedelta

from corpus import screenshot_templates as tpl
from corpus.manifest import Manifest
from corpus.rng import ANCHOR_DATE, SPREAD_DAYS, make_rng
from corpus.screenshot_content import build_instances

BUILDERS = {
    "error_dialog": tpl.error_dialog,
    "terminal": tpl.terminal,
    "dashboard": tpl.dashboard,
    "chat": tpl.chat,
    "settings": tpl.settings,
    "code_editor": tpl.code_editor,
    "cloud_console": tpl.cloud_console,
    "mobile": tpl.mobile,
}

PLAYWRIGHT_HINT = (
    "Chromium not found for Playwright. Run "
    "`uv run --with playwright playwright install chromium` "
    "then re-run this script to generate screenshots."
)


def _past_date(rng) -> str:
    stamp = ANCHOR_DATE - timedelta(days=rng.uniform(0, SPREAD_DAYS))
    return stamp.strftime("%Y-%m-%d")


def _filename(rng, index: int, used: set[str]) -> str:
    style = rng.randrange(3)
    while True:
        if style == 0:
            h, m, s = rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
            name = f"Screenshot {_past_date(rng)} at {h:02d}.{m:02d}.{s:02d}.png"
        elif style == 1:
            name = f"IMG_{rng.randint(1000, 9999)}.png"
        else:
            name = f"CleanShot {_past_date(rng)}.png"
        if name not in used:
            used.add(name)
            return name
        style = (style + 1) % 3


def generate(seed: int, root: Path, manifest: Manifest) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(PLAYWRIGHT_HINT)
        return 0

    out_dir = root / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    instances = build_instances(seed)
    naming_rng = make_rng(seed, "screenshot-names")
    used: set[str] = set()

    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception:
                print(PLAYWRIGHT_HINT)
                return 0
            page = browser.new_page(
                viewport={"width": 1440, "height": 900}, device_scale_factor=2
            )
            count = 0
            for i, (category, inst) in enumerate(instances):
                html = BUILDERS[category](**inst["params"])
                filename = inst.get("force_filename") or _filename(
                    naming_rng, i, used
                )
                used.add(filename)
                path = out_dir / filename
                page.set_content(html)
                page.screenshot(path=str(path))
                manifest.add_indexed(path, "screenshots")
                count += 1
            browser.close()
            return count
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"{PLAYWRIGHT_HINT} ({exc})")
        return 0
