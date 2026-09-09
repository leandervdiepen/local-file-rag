#!/usr/bin/env -S uv run --with pillow python
"""Draw the app icon and build the .icns electron-builder expects.

The icon is the product in one picture: a page, and the one band on it that
answered the query. Generated rather than drawn by hand so it can be changed
by editing two numbers, and so the repo carries the source of its own icon.

Run: uv run --with pillow scripts/make_icon.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

CANVAS = 1024
# macOS insets the artwork inside the grid square; the squircle fills this box.
MARGIN = 100
CORNER = 224

# The same three colours the app uses, from app/src/renderer/tokens.css.
INK = (28, 26, 24)
PAPER = (250, 249, 247)
HEAT = (226, 78, 54)
RULE = (206, 203, 198)

# Sizes `iconutil` requires, each at one and two times.
SIZES = (16, 32, 128, 256, 512)


def draw() -> Image.Image:
    icon = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    pen = ImageDraw.Draw(icon)

    pen.rounded_rectangle((MARGIN, MARGIN, CANVAS - MARGIN, CANVAS - MARGIN), CORNER, fill=INK)

    # The page, portrait, sitting slightly high so the icon reads balanced.
    page = (326, 236, 698, 762)
    pen.rounded_rectangle(page, 18, fill=PAPER)

    left, top, right, _ = page
    line_left, line_right = left + 46, right - 46
    thickness, gap = 20, 54

    # Lines of text, with the fourth one lit. Not the first: the point of the
    # product is finding the line you would have had to scroll to.
    for index in range(7):
        y = top + 92 + index * gap
        if index == 3:
            pen.rounded_rectangle((line_left - 18, y - 14, line_right + 18, y + thickness + 14), 8, fill=HEAT)
        else:
            width = line_right if index % 3 else line_right - 82
            pen.rounded_rectangle((line_left, y, width, y + thickness), 6, fill=RULE)

    return icon


def build(out: Path) -> None:
    iconset = out.parent / "icon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir(parents=True)

    icon = draw()
    icon.save(out.parent / "icon.png")
    for size in SIZES:
        icon.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
        icon.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")

    subprocess.run(["iconutil", "--convert", "icns", str(iconset), "--output", str(out)], check=True)
    shutil.rmtree(iconset)
    print(f"wrote {out} and {out.parent / 'icon.png'}")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "app/build/icon.icns"))
