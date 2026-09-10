#!/usr/bin/env -S uv run python
"""Record the showcase demo while driving the real app.

Run the app with a debugger port and a log to read the sidecar port from:

    cd app && pnpm exec electron-vite dev -- --remote-debugging-port=9222 > /tmp/app-dbg.log

then `uv run scripts/record_demo.py`. It writes /tmp/demo-raw.mov, which is
cropped to the window with ffmpeg.


Everything on screen is the app doing its own work. The script only supplies
the keystrokes, and it supplies them at reading speed, because a demo that
moves faster than a viewer can follow shows nothing. Every beat waits for the
app to actually be in the state it is about to film.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app_driver import Page  # noqa: E402

OUT = Path("/tmp/demo-raw.mov")
# The title bar sits above the content area, which is what screenX and screenY
# report, and h.264 wants even dimensions.
CHROME_HEIGHT = 30

# Long enough for every beat below, and the recorder stops itself at the end.
LENGTH_S = 48


def set_query(app: Page, text: str) -> None:
    app.js(
        """(() => {
          const box = document.querySelector('input[role=combobox]');
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(box, %s);
          box.dispatchEvent(new Event('input', {bubbles: true}));
        })()"""
        % json.dumps(text)
    )


def type_out(app: Page, text: str, per_key: float = 0.075) -> None:
    """Grow the query one character at a time, the way a person types it."""
    for length in range(1, len(text) + 1):
        set_query(app, text[:length])
        time.sleep(per_key)


KEYS = {" ": (32, "Space"), "ArrowDown": (40, "ArrowDown"), "Escape": (27, "Escape")}


def press(app: Page, key: str) -> None:
    """A key event through the debugger, with the fields Chromium expects.

    A synthetic KeyboardEvent dispatched from page script reaches React for
    some keys and not others, which cost a whole take. This is the real path.
    """
    code, name = KEYS[key]
    app.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "windowsVirtualKeyCode": code, "code": name, "key": key})
    if key == " ":
        app.call("Input.dispatchKeyEvent", {"type": "char", "text": " ", "unmodifiedText": " ", "key": " "})
    app.call("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": code, "code": name, "key": key})


def wait_for(app: Page, what: str, expression: str, seconds: float = 20.0) -> bool:
    """Poll until the app shows it. A demo that hopes is a demo that records nothing."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        if app.js(expression):
            return True
        time.sleep(0.5)
    print(f"  never happened: {what}")
    return False


def region(app: Page) -> str:
    left, top, width, height = json.loads(
        str(app.js("JSON.stringify([window.screenX, window.screenY, window.outerWidth, window.outerHeight])"))
    )
    return f"{left},{top - CHROME_HEIGHT},{width},{height + CHROME_HEIGHT}"


def main() -> int:
    app = Page()
    app.call("Page.bringToFront", {})
    while app.js("document.body.innerText.includes('Highlight')"):
        press(app, "Escape")
        time.sleep(0.6)
    set_query(app, "")
    time.sleep(1.5)

    OUT.unlink(missing_ok=True)
    # A fixed length, not a signal. screencapture finalises the file when its
    # timer ends; killing it leaves nothing on disk at all.
    recorder = subprocess.Popen(["screencapture", "-v", "-V", str(LENGTH_S), "-R", region(app), "-x", str(OUT)])
    time.sleep(3)

    try:
        # The query no filename and no keyword search can answer.
        type_out(app, "stripe webhook error screenshot")
        time.sleep(2)
        print("stage 1 up, waiting for the rerank")
        time.sleep(14)

        # Click the first result rather than arrowing to it, so the video
        # always opens the same page and a viewer sees the pointer do it.
        app.call("Page.bringToFront", {})
        picked = app.js("""(() => {
          const row = document.querySelector('[role=option]');
          if (!row) return null;
          row.click();
          return row.textContent.slice(0, 40);
        })()""")
        print("  opened:", picked)
        time.sleep(1.2)
        for attempt in range(3):
            press(app, " ")
            if wait_for(app, "the preview", "document.body.innerText.includes('Highlight')", 6):
                break
            print(f"  space did not land, retry {attempt + 1}")
        print("preview open, letting the heatmap settle")
        time.sleep(5)

        # The combined map is diffuse and the per token maps are not, which is
        # the whole reason the token picker exists. Show the one that works.
        clicked = app.js("""(() => {
          const chip = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'stripe');
          if (!chip) return false;
          chip.click();
          return true;
        })()""")
        print("  token chip clicked:", clicked)
        time.sleep(7)

        press(app, "Escape")
        time.sleep(2)
    finally:
        recorder.wait(timeout=LENGTH_S + 30)

    size = OUT.stat().st_size // 1024 if OUT.exists() else 0
    print(f"recorded {OUT}, {size} KB")
    return 0 if size else 1


if __name__ == "__main__":
    sys.exit(main())
