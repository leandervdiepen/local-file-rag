# Launch video

`docs/launch.mp4` is composed here in [Remotion](https://www.remotion.dev) from footage of the real app.
Remotion is free for individuals and companies of up to three people, which this project is. A larger company needs a company licence.

## Re-render

```sh
cd video
pnpm install
pnpm render        # docs/launch.mp4
pnpm poster        # docs/images/launch-poster.jpg
pnpm studio        # scrub the timeline in a browser
```

The first render downloads Remotion's headless Chromium into `node_modules/.remotion`.
Nothing else leaves the machine: the fonts are the app's own files in `public/fonts`, and the footage is in `public/clips`.

## Re-record

The clips are the app drawing itself, captured through Chromium's screencast at a device scale factor of 2, so they are sharp on any display.
Start the app with a debugger port, then run the recorder against it with the demo corpus indexed:

```sh
cd app && env -u ELECTRON_RUN_AS_NODE pnpm exec electron-vite dev -- --remote-debugging-port=9222 > /tmp/app-dbg.log
python3 video/record_footage.py
```

It writes `public/clips/*.mp4` and `src/clips.json`. Trim points live in `src/Launch.tsx` and are chosen by looking at the footage, so check them after a new take.

Chromium only screencasts a page it considers visible, so the app window has to stay unobscured for the few minutes the take runs.
The recorder brings the window forward before every beat and retakes a beat whose frames stopped, but a browser window dropped on top of it mid-beat still costs that beat a retake. Park the app on a display nothing else is using.

Every beat runs once with the recorder off first, so the model is loaded and the renderer's image cache is warm when the take starts.
The recorder also counts sidecar restarts in `/tmp/app-dbg.log` and retakes any beat that saw one.
That guard exists because the sidecar aborted inside pdfium four times during the first session, every time with two or more threads rendering PDF pages at once (`~/Library/Logs/DiagnosticReports/python3.13-*.ips`, `CFX_FontMapper::AddInstalledFont`).
`PdfiumPageSource` takes no lock and pdfium is not thread safe, so concurrent thumbnail renders can take the whole sidecar down. That is an app bug, not a recording one, and it is left for the app to fix.

## Words

Captions follow `docs/LAUNCH.md`: only the claims it permits, every number from `docs/STATUS.md`, and no em dashes.
