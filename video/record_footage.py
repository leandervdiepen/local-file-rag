#!/usr/bin/env python3
"""Record the launch footage from the real app, one clip per beat.

Run the app with a debugger port and a log to read the sidecar port from:

    cd app && env -u ELECTRON_RUN_AS_NODE pnpm exec electron-vite dev -- --remote-debugging-port=9222 > /tmp/app-dbg.log

then `python3 video/record_footage.py`. It writes `video/public/clips/<beat>.mp4`
and `video/src/clips.json` with each clip's length in frames.

The frames come from Chromium's own screencast of the renderer, with the
viewport set to 1280 by 800 at a device scale factor of 2. That is the app
drawing itself at Retina density whatever display it happens to be on, so the
footage is sharp on a 1x monitor and nothing on the machine has to change.

Everything on screen is the app doing its own work. The script supplies
keystrokes at reading speed and waits for the app to be in the state it is
about to film. It never fakes a result, a number or a latency.

Every beat runs once with the recorder off before it runs for real. The dry
run loads the model and fills the renderer's image cache, so the take shows
the app answering rather than the app warming up. The sidecar can abort inside
pdfium when two pages render at once (see the report in video/README.md), and
a beat that saw a restart is thrown away and taken again.
"""

from __future__ import annotations

import base64
import json
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import cdp  # noqa: E402
from app_driver import LOG_PATH, Page  # noqa: E402

CLIPS = REPO / "video" / "public" / "clips"
FRAMES = REPO / "video" / "frames"
MANIFEST = REPO / "video" / "src" / "clips.json"
FPS = 30
VIEWPORT = {"width": 1280, "height": 800, "deviceScaleFactor": 2, "mobile": False}

HERO_QUERY = "stripe webhook error screenshot"
# A golden query whose page carries none of its words and still ranks first
# (scripts/golden.jsonl g10, hit@1 on run 20260910T022443Z).
VISUAL_QUERY = "mobile home screen with a ton of notification badges"
QUESTION = "what did the Q2 hosting invoice charge for egress"

# The combined map at the default cutoff is diffuse (docs/STATUS.md, day 3), so
# each heatmap beat picks one query word and a tighter cutoff. Every word of
# every query was screenshotted at 90, 95, 97 and 99 before these were chosen:
# "stripe" marks the word stripe in the dialog, "notification" lands beside the
# badged icons, "invoice" lands on the word invoice in the title.
HERO_WORD, HERO_CUT = "stripe", 95
VISUAL_WORD, VISUAL_CUT = "notification", 99
CITED_WORD, CITED_CUT = "invoice", 99


class Screencast:
    """A second debugger connection that only receives frames and acknowledges them."""

    def __init__(self) -> None:
        targets = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list"))
        target = next(t for t in targets if t["type"] == "page")
        url = urlparse(target["webSocketDebuggerUrl"])
        self.sock = socket.create_connection((url.hostname, url.port), timeout=600)
        cdp._handshake(self.sock, url.hostname, url.port, url.path)
        self.frames: list[tuple[float, Path]] = []
        self.marks: dict[str, tuple[float, float]] = {}
        self.current: str | None = None
        self.started = 0.0
        self.running = True
        self.thread = threading.Thread(target=self._pump, daemon=True)

    def start(self) -> None:
        FRAMES.mkdir(parents=True, exist_ok=True)
        for old in FRAMES.iterdir():
            old.unlink()
        cdp._send(self.sock, {"id": 1, "method": "Emulation.setDeviceMetricsOverride", "params": VIEWPORT})
        cdp._send(
            self.sock,
            {
                "id": 2,
                "method": "Page.startScreencast",
                "params": {"format": "jpeg", "quality": 95, "maxWidth": 2560, "maxHeight": 1600, "everyNthFrame": 1},
            },
        )
        self.thread.start()

    def _pump(self) -> None:
        while self.running:
            try:
                message = cdp._recv(self.sock)
            except OSError:
                return
            if message.get("method") != "Page.screencastFrame":
                continue
            params = message["params"]
            path = FRAMES / f"{len(self.frames):06d}.jpg"
            path.write_bytes(base64.b64decode(params["data"]))
            self.frames.append((params["metadata"]["timestamp"], path))
            cdp._send(
                self.sock,
                {"id": 100 + len(self.frames), "method": "Page.screencastFrameAck", "params": {"sessionId": params["sessionId"]}},
            )

    def begin(self, name: str) -> None:
        self.current = name
        self.started = time.time()

    def end(self, keep: bool) -> None:
        assert self.current
        if keep:
            self.marks[self.current] = (self.started, time.time())
        self.current = None

    def stop(self) -> None:
        self.running = False
        cdp._send(self.sock, {"id": 3, "method": "Page.stopScreencast", "params": {}})
        cdp._send(self.sock, {"id": 4, "method": "Emulation.clearDeviceMetricsOverride", "params": {}})
        time.sleep(0.5)
        self.sock.close()


def encode(cast: Screencast) -> dict[str, int]:
    """Hold every frame until the next one, then flatten to constant frame rate."""
    CLIPS.mkdir(parents=True, exist_ok=True)
    lengths: dict[str, int] = {}
    for name, (start, stop) in cast.marks.items():
        before = [f for f in cast.frames if f[0] <= start]
        inside = [f for f in cast.frames if start < f[0] < stop]
        shown = ([before[-1]] if before else []) + inside
        listing = FRAMES / f"{name}.txt"
        with listing.open("w") as out:
            for index, (stamp, path) in enumerate(shown):
                begins = max(stamp, start)
                ends = shown[index + 1][0] if index + 1 < len(shown) else stop
                out.write(f"file '{path}'\nduration {max(ends - begins, 1 / FPS):.4f}\n")
            out.write(f"file '{shown[-1][1]}'\n")
        target = CLIPS / f"{name}.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-vf", f"fps={FPS}",
             "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-an", str(target)],
            check=True,
        )
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", str(target)],
            capture_output=True, text=True, check=True,
        )
        lengths[name] = int(probe.stdout.strip())
        print(f"  {name}: {lengths[name]} frames, {target.stat().st_size // 1024} KB")
    return lengths


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


def type_out(app: Page, text: str, per_key: float = 0.07) -> None:
    for length in range(1, len(text) + 1):
        set_query(app, text[:length])
        time.sleep(per_key)


KEYS = {" ": (32, "Space"), "ArrowDown": (40, "ArrowDown"), "Escape": (27, "Escape"), "Enter": (13, "Enter")}


def press(app: Page, key: str, shift: bool = False) -> None:
    """A key event through the debugger, with the fields Chromium expects. The box is focused first: keys go to the focused element."""
    code, name = KEYS[key]
    modifiers = 8 if shift else 0
    app.js("document.querySelector('input[role=combobox]')?.focus()")
    base = {"windowsVirtualKeyCode": code, "code": name, "key": key, "modifiers": modifiers}
    app.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **base})
    if key == " ":
        app.call("Input.dispatchKeyEvent", {"type": "char", "text": " ", "unmodifiedText": " ", "key": " ", "modifiers": modifiers})
    app.call("Input.dispatchKeyEvent", {"type": "keyUp", **base})


def wait_for(app: Page, what: str, expression: str, seconds: float = 30.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if app.js(expression):
            return True
        time.sleep(0.25)
    print(f"  never happened: {what}")
    return False


def wait_settled(app: Page, what: str) -> bool:
    """Stage 1 and stage 2 print the same status line when no page is cold, so give stage 2 its second after the line appears."""
    settled = wait_for(app, what, SETTLED, 30)
    time.sleep(1.6)
    return settled


def set_slider(app: Page, percentile: int) -> None:
    """Drag the Highlight slider: the cutoff is a percentile, so 97 shows the top 3 percent of patches."""
    app.js(
        """(() => {
          const s = document.querySelector('input[type=range]');
          if (!s) return;
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(s, %d);
          s.dispatchEvent(new Event('input', {bubbles: true}));
        })()"""
        % percentile
    )


def activate() -> None:
    """Bring the window forward. Chromium only screencasts a page it considers visible, and an occluded window is not."""
    subprocess.run(["osascript", "-e", 'tell application id "com.github.Electron" to activate'], check=False, capture_output=True)


def click_text(app: Page, text: str) -> bool:
    return bool(
        app.js(
            """(() => {
              const b = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === %s);
              if (!b) return false; b.click(); return true;
            })()"""
            % json.dumps(text)
        )
    )


HEATMAP_READY = "document.body.innerText.includes('Highlight')"
PREVIEW_OPEN = "document.querySelector('section[aria-label] header button') !== null"
SETTLED = "(() => { const s = document.querySelector('[role=status]'); return !!s && /pages? in /.test(s.textContent) && !/Reading/.test(s.textContent); })()"
CITED = "document.querySelector('ul[aria-label=\"Cited pages\"] button') !== null"


class Take:
    """One attempt at a beat, judged by what the app showed and whether the sidecar survived it."""

    def __init__(self) -> None:
        self.ok = True

    def expect(self, happened: bool) -> None:
        self.ok = self.ok and happened


def open_first_result(app: Page, take: Take, expected_file: str) -> None:
    """Select the first row by clicking it, so the same page opens every take, then Space for the preview.

    A synthetic key can miss, which cost a whole take once, so Space is retried.
    """
    take.expect(bool(app.js("(() => { const row = document.querySelector('[role=option]'); if (!row) return false; row.click(); return true; })()")))
    time.sleep(1.0)
    for attempt in range(3):
        press(app, " ")
        if wait_for(app, "the preview", PREVIEW_OPEN, 4):
            break
        print(f"  space did not land, retry {attempt + 1}")
    opened = str(app.js("document.querySelector('section[aria-label] header p')?.textContent") or "")
    if expected_file not in opened:
        print(f"  opened {opened!r}, wanted {expected_file}")
        take.expect(False)
    take.expect(wait_for(app, "the heatmap", HEATMAP_READY, 30))


def reset(app: Page) -> None:
    for _ in range(3):
        if not app.js("document.body.innerText.includes('Highlight') || document.body.innerText.includes('Close')"):
            break
        press(app, "Escape")
        time.sleep(0.4)
        click_text(app, "Close")
        time.sleep(0.4)
    set_query(app, "")
    time.sleep(0.8)


def sidecar_starts() -> int:
    return Path(LOG_PATH).read_text().count("serving on 127.0.0.1")


def prime_pdfium(app: Page) -> None:
    """Render one PDF page alone before anything renders two at once.

    pdfium scans the system fonts the first time a page needs a substitute
    face, and that scan is not safe to run from two threads. A fresh sidecar
    gets its first PDF render here, on its own, so the take does not hand it
    the race.
    """
    files = app.api("/index/files?state=text_indexed")["files"]
    pdf = next((f for f in files if f["kind"] == "pdf"), None)
    if pdf is None:
        return
    try:
        app.api(f"/pages/{pdf['id']}:1/image?size=thumb")
    except UnicodeDecodeError:
        return  # PNG bytes came back, which is the render happening
    except (urllib.error.HTTPError, json.JSONDecodeError):
        print("  priming render did not happen, carrying on")


def focus_word(app: Page, take: Take, word: str, cut: int) -> None:
    """One word of the query, at a cutoff where the marks sit on the thing that matched."""
    time.sleep(2.0)
    take.expect(click_text(app, word))
    time.sleep(1.2)
    set_slider(app, cut)
    time.sleep(3.5)


def beat_search(app: Page, take: Take, settle: float) -> None:
    time.sleep(settle)
    type_out(app, HERO_QUERY)
    take.expect(wait_settled(app, "the rerank"))
    time.sleep(1.4)
    open_first_result(app, take, "IMG_4821.png")
    focus_word(app, take, HERO_WORD, HERO_CUT)


def beat_visual(app: Page, take: Take, settle: float) -> None:
    time.sleep(settle)
    type_out(app, VISUAL_QUERY)
    take.expect(wait_settled(app, "the visual rerank"))
    time.sleep(1.6)
    open_first_result(app, take, "IMG_9013.png")
    focus_word(app, take, VISUAL_WORD, VISUAL_CUT)


def beat_ask(app: Page, take: Take, settle: float) -> None:
    time.sleep(settle)
    type_out(app, QUESTION)
    take.expect(wait_settled(app, "the question's search"))
    press(app, "Enter", shift=True)
    take.expect(wait_for(app, "the answer", CITED, 90))
    time.sleep(2.5)
    app.js("document.querySelector('ul[aria-label=\"Cited pages\"] button')?.click()")
    take.expect(wait_for(app, "the cited page's heatmap", HEATMAP_READY, 30))
    take.expect("hosting-q2-2026.pdf" in str(app.js("document.querySelector('section[aria-label] header p')?.textContent") or ""))
    focus_word(app, take, CITED_WORD, CITED_CUT)


def beat_index(app: Page, take: Take, settle: float) -> None:
    """The counts, then a scroll down into the files it skipped and why.

    The scroll is not decoration. Chromium sends a screencast frame when the
    page changes and nothing else, so a still screen films as no frames at
    all, and this beat was lost eight times in a row before that was the
    diagnosis rather than a window someone had covered up.
    """
    time.sleep(settle)
    take.expect(click_text(app, "Index"))
    take.expect(wait_for(app, "the index screen", "document.body.innerText.includes('Pages read by the model')", 10))
    time.sleep(1.6)
    scroll(app, to=760, over=2.6)
    time.sleep(1.2)


def scroll(app: Page, to: int, over: float) -> None:
    """Ease the scroller down to `to` over `over` seconds, one step per frame."""
    steps = max(int(over * FPS), 1)
    for step in range(1, steps + 1):
        eased = 1 - (1 - step / steps) ** 3
        app.js(
            """(() => {
              const el = document.scrollingElement;
              const inner = [...document.querySelectorAll('*')].find(n => n.scrollHeight > n.clientHeight + 40);
              (inner ?? el).scrollTop = %d;
            })()"""
            % round(to * eased)
        )
        time.sleep(1 / FPS)


BEATS = {"search": beat_search, "visual": beat_visual, "ask": beat_ask, "index": beat_index}


def run_beat(app: Page, cast: Screencast, name: str, record: bool) -> bool:
    activate()
    visible = wait_for(app, "the window to be visible", "document.visibilityState === 'visible'", 5)
    starts = sidecar_starts()
    frames_before = len(cast.frames)
    take = Take()
    if record:
        cast.begin(name)
    BEATS[name](app, take, settle=1.0 if record else 0.2)
    survived = sidecar_starts() == starts
    filmed = not record or len(cast.frames) - frames_before > 10
    ok = take.ok and survived and visible and filmed
    if record:
        cast.end(keep=ok)
    reset(app)
    label = "take" if record else "dry run"
    why = "" if survived else " (the sidecar restarted)"
    why += "" if filmed else " (no frames came: the window was covered, or nothing on screen moved)"
    print(f"  {name} {label}: {'ok' if ok else 'lost'}{why}")
    return ok


def main() -> int:
    # Named beats only, when a take was lost and the rest are still good. The
    # manifest keeps the lengths of the clips this run did not touch.
    wanted = [name for name in sys.argv[1:] if name in BEATS] or list(BEATS)
    app = Page()
    activate()
    cast = Screencast()
    cast.start()
    time.sleep(1.0)
    reset(app)
    prime_pdfium(app)

    try:
        for name in wanted:
            for attempt in range(4):
                if run_beat(app, cast, name, record=False) and run_beat(app, cast, name, record=True):
                    break
                print(f"  {name}: attempt {attempt + 1} lost, priming again")
                time.sleep(3.0)
                prime_pdfium(app)
    finally:
        cast.stop()

    kept = json.loads(MANIFEST.read_text())["frames"] if MANIFEST.exists() else {}
    kept.update(encode(cast))
    MANIFEST.write_text(json.dumps({"fps": FPS, "frames": kept}, indent=2) + "\n")
    print(f"wrote {MANIFEST}")
    return 0 if all(name in kept for name in wanted) else 1


if __name__ == "__main__":
    sys.exit(main())
