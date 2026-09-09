# Seven day plan

Timelines assume agentic coding with Claude Code, not hand typing.
A day is eight to ten focused hours.
Each task has an acceptance test.
A task is done when the test passes in the real app, not when the code exists.
Record every measured number in STATUS.md.

## Day 0, the evening before

Two hours.
Purpose: kill the day 2 risk before day 1 starts.

- [x] Install uv, Node 22, pnpm. Confirm Xcode command line tools.
- [x] Spike: `uv init spike && uv add sentence-transformers torch pypdfium2 pillow`. Load `vidore/colqwen2-v1.0` with `MultiVectorEncoder`, device `mps`. Embed one rendered PDF page. Record load time, seconds per page, vectors per page, peak memory, torch version that worked.
- [x] Spike: encode a query, compute MaxSim against three pages, confirm the right page wins.
- [x] Build the demo corpus with `scripts/make_demo_corpus.py`: synthetic but realistic, about 300 files. Real files from Desktop or Downloads may be added read only and are never committed. Target mix: 40 screenshots, 30 PDFs with charts and tables, 10 slide decks exported to PDF, 50 markdown and text files, plus 150 junk files that should be gated or ranked low. Put it in `~/demo-corpus`.
- [x] Write 30 golden queries against the corpus in `scripts/golden.jsonl`: query, expected file, expected page. Ten with no matching words on the page.
- [ ] Check whether an Apple Developer account exists. Write the answer in STATUS.md.

Acceptance: the spike prints a seconds-per-page number under 3 s and picks the right page.

## Day 1, skeleton

- [x] Create the repo next to this folder. Move this folder to `docs/`. Link it from STATUS.md.
- [x] `app/`: electron-vite with React 19, TypeScript, Tailwind v4. Main spawns the sidecar, reads `READY <port>`, exposes base URL and token through preload.
- [x] `sidecar/`: uv project, Flask 3 app, waitress entrypoint, bearer token middleware, `/health`.
- [x] Layer skeleton in both packages per KICKOFF.md: domain, application with ports, infrastructure, interface. import-linter and dependency-cruiser wired into `make check` on day one, before any adapter exists.
- [x] `store.py`: LanceDB tables from ARCHITECTURE.md. FTS index on `files.text` and `pages.text`.
- [x] `crawl.py`, `gate.py`: skip list, hashing, kind detection, skip reasons.
- [x] `extract_pdf.py`: pypdfium2 text per page and page count.
- [x] `ocr_mac.py`: Apple Vision OCR for images and empty-text PDF pages.
- [x] `jobs.py`: background indexing thread with a progress endpoint.
- [x] `api_search.py`: SSE search emitting `candidates` from stage 1 only.
- [x] Renderer: folder picker on first run, search box, results grouped by file with thumbnails from `/pages/{id}/image?size=thumb`.
- [x] Renderer: open, reveal in Finder, copy path.

Acceptance: pick `~/demo-corpus`, 300 files indexed, a filename query and an OCR text query each return in under 150 ms with thumbnails.
Measure: files per second crawled, OCR milliseconds per image, index size on disk.

## Day 2, vision path

- [x] `embed.py`: lazy model load, MPS, pooling factor 3, float16, unload after ten idle minutes.
- [x] Page rendering at 1024 px long side for embedding.
- [x] `page_vectors` writes and reads. Create the cosine index once row count passes 2,000.
- [x] `rerank.py`: MaxSim in numpy over a candidate set.
- [x] Multivector search merged into the candidate set on every search, not only a thin one. D49 withdrew the fewer-than-five rule with the measurement that killed it.
- [ ] `scripts/bench.py`: pages per second, KB per page, rerank time for 300 pages. Recall moved to the golden set runner by D46, which reports it per query split rather than as one number.

Acceptance: "slide with the funnel chart" returns the right slide although no page text matches.
Measure: everything the bench script prints. Put it in STATUS.md with machine and date.

## Day 3, two stages and the heatmap

Protect this day.
Nothing else gets pulled forward into it.

- [x] Candidate embedding with the 30 page cap, ordered by stage 1 score, `progress` events with "reading 12 of 24 pages". Built on day 2, because stage 2 cannot rank a page it has not read. See `Plan swaps` in STATUS.md.
- [x] `heatmap.py`: unpooled re-encode, per-token and combined maps from the processor grid, in-memory LRU of 500 pages (D50).
- [x] `GET /pages/{id}/heatmap?q=` returning the JSON grid.
- [x] Renderer page preview: canvas overlay, combined versus per-token toggle, threshold slider defaulting to the 90th percentile, one patch blur.
- [x] Test portrait, landscape and square pages. The overlay must sit on the right pixels in all three. Covered by the grid test in `test_colqwen_embedder.py` and by drawing a marked half page and asserting the peak lands on it.

Acceptance: "stripe webhook error screenshot" returns the PNG and the red dialog glows. Cold heatmap under 2 s, cached under 100 ms.
Measure: cold and cached heatmap times.

## Day 4, chat

- [x] Two answerers, streaming, top five page images, prompt and citation parsing in the domain, usage capture. Written against the wire with urllib rather than the Anthropic SDK: see D51.
- [x] `POST /chat` SSE with `retrieval`, `token`, `citation`, `done`.
- [x] Renderer chat panel: streaming text, citation chips, clicking a chip opens the page preview with heatmap, token and cost footer.
- [ ] Offline mode toggle. Chat panel says what it disables.
- [ ] Settings: Anthropic key through `safeStorage`, `PUT /secrets/anthropic`, model selector.

Acceptance: "what did the Q2 hosting invoice charge for egress" answers with a correct page citation. A question with no answer in the corpus returns "not in your files" and no citation.
Measure: first token latency after retrieval, tokens per question.
Passed 2026-09-09. See `Day 4 gate` in STATUS.md.

## Day 5, trust

- [x] Index screen: stats, folders, skipped files with reasons, rescan, per-folder toggles, forget file.
- [x] `watcher.py`: watchdog FSEvents, debounce, add, change, delete within five seconds.
- [x] Idle pre-embedding of the 200 most recently used files on AC power.
- [x] Storage cap with least recently hit eviction.
- [x] Error states: sidecar down, model download failed, folder permission denied, corrupt file.

Acceptance: drop a PDF into the folder and it is searchable in five seconds. Exclude a folder and its results vanish. Stats match `ls` counts.
Passed 2026-09-09 by `scripts/day5_acceptance.py` against a live sidecar: 2.14 s to searchable, an excluded folder returns nothing and returns 21 results again when turned back on, 2 files scanned against 2 on disk.

## Day 6, eval and polish

- [ ] Click logging and `GET /eval/recall`.
- [ ] Golden set runner in the index screen with per-query hit or miss.
- [ ] Design pass with the interface skills: empty states, loading states, focus states, spacing, type.
- [x] Keyboard: global shortcut opens the window, arrows move, enter opens, escape clears.
- [ ] Tests complete per the pyramid in KICKOFF.md: unit on domain and application, integration per adapter, Playwright Electron on the three money paths with Anthropic stubbed.
- [x] Lint and typecheck green in both projects.

Acceptance: recall@5 of 0.8 or better on the golden set, or the gap is written down with the failing queries. All checks green.

## Day 7, ship

- [x] PyInstaller onedir sidecar. Launch it from the packaged app.
- [x] electron-builder arm64 DMG. Installing on a clean user account is still open, and needs a second account on this Mac.
- [x] First-run model download with progress.
- [x] README: install, what stays local, what leaves the machine and when, the measured numbers, the architecture diagram, license.
- [ ] Record the video from LAUNCH.md. Take the screenshots.
- [ ] Publish the repo. Post.

Acceptance: a fresh Mac runs the 45 second demo from the DMG without a terminal.

## Cut order if behind

1. Golden set runner in the UI. Keep the script.
2. Idle pre-embedding.
3. Watcher. Keep manual rescan.
4. Per-token heatmap toggle. Keep the combined map.
5. Storage cap.
6. Streaming in chat.

Never cut: the heatmap, the index screen, the cold page cap with progress text, the DMG.

## If ahead of schedule

1. An MCP server that exposes search and page fetch, so Claude Desktop and Claude Code can search the user's files.
2. ColModernVBERT as a fast mode without heatmaps.
3. Recall comparison panel: stage 1 alone versus stage 1 plus 2.

## Definition of shipped

- [ ] DMG runs on a clean machine.
- [ ] The 45 second demo works end to end.
- [x] README claims match the code, word for word on privacy.
- [x] Measured numbers in README carry machine, model and date.
- [ ] Lint, typecheck, pytest, vitest and the Playwright smoke test pass.
- [ ] Repo public, post published, links in STATUS.md.
