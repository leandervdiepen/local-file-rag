# Decisions

Locked on 2026-09-07 unless a later date is noted.
Change one only with new evidence, and write the evidence here.

| ID | Decision | Why |
|---|---|---|
| D01 | Electron shell, electron-vite, React 19, TypeScript, Tailwind v4, shadcn/ui, electron-builder | Leander's stack. A week leaves no room to learn Tauri and Rust packaging. |
| D02 | Flask 3 served by waitress as the sidecar HTTP layer | Requested. Server-sent events work through generator responses. waitress is a threaded production server with no async ceremony. |
| D03 | Python sidecar owns indexing, inference, retrieval and answering | Sentence Transformers, torch and the ColQwen weights exist in Python first. One process owns the index. |
| D04 | Sentence Transformers v6 `MultiVectorEncoder` for embedding and MaxSim | colpali-engine is deprecated in favor of it. Same models load. Token pooling is built in. |
| D05 | Retrieval model `vidore/colqwen2-v1.0` | Qwen2-VL-2B base, 128-dim vectors, at most 768 patches per page, rectangular patch grid so heatmaps work. Apache 2.0 base plus MIT adapters. ColQwen2.5 is 3B and heavier. ColModernVBERT is faster but its non-rectangular token grid has no similarity map support, and the heatmap is the hero. |
| D06 | torch on MPS, not MLX | No maintained MLX port of ColQwen was found. Lazy embedding makes one to three seconds per page acceptable. |
| D07 | LanceDB as the only store | Embedded, one directory, full-text index and multivector MaxSim search in one library, Python and TypeScript SDKs. Elasticsearch is a JVM inside a desktop app. Pinecone contradicts local-first and bills per vector. |
| D08 | Vectors live in a separate `page_vectors` table keyed by page id | Keeps `pages` light and avoids null multivector rows in an indexed column. |
| D09 | Hierarchical token pooling at factor 3, stored as float16 | Roughly a third of the vectors at about 98 percent of retrieval quality. Heatmaps need unpooled vectors, so they are computed by re-encoding the top page on demand and cached on disk. |
| D10 | pypdfium2 for PDF rendering and text, not PyMuPDF | PyMuPDF is AGPL. pypdfium2 is BSD-3 and Apache-2.0 with an arm64 wheel. |
| D11 | Apple Vision OCR through pyobjc for images and scanned pages | Native, fast, local, no Tesseract binaries to bundle. |
| D12 | `watchdog` inside the sidecar for file events | The process that owns the index owns the events. FSEvents backend on macOS. |
| D13 | Lazy two-stage retrieval with a cap of 30 uncached pages per query | Never embeds a file nobody asked about. Progress text makes the wait legible. |
| D14 | Claude Opus 5 via the Anthropic Python SDK for answers, streaming, page images as base64 blocks | Best answer quality on charts and tables. Model is a setting. No local answer model in v1. |
| D15 | Heatmap ships as a JSON grid and the renderer draws it on a canvas | Threshold and per-token toggles stay client side with zero round trips. |
| D16 | Sidecar binds loopback on a random port with a per-launch bearer token | Other local processes cannot read the index. |
| D17 | Anthropic key stored with Electron `safeStorage`, sent to the sidecar over the authenticated local API, held in memory only | No key in a tracked or plaintext file. |
| D18 | Apple Silicon only, DMG via electron-builder, unsigned acceptable for v1 | Notarization is a known time sink. Distribution must not block launch. |
| D19 | File types in v1: PDF, PNG, JPG, TXT, MD | Office formats need a LibreOffice conversion step. Not this week. |
| D20 | Code under MIT | Every dependency and model weight in the stack is permissive, so the whole thing can be. |
| D21 | No telemetry, ever | The privacy claim has to be literally true. |
| D22 | Onion architecture in both packages: domain, application with ports, infrastructure adapters, thin interface. Enforced by import-linter and dependency-cruiser in `make check` | Agents and humans can implement an adapter from a Protocol alone. Boundary tests keep the shape as the code grows fast. |
| D23 | Testing pyramid: unit on every task, integration when an adapter changes, three end-to-end money paths at day gates only | Fast inner loop. End-to-end runs are slow and flaky by nature, so they guard gates, not edits. |
| D24 | Linear mirrors PLAN.md for Leander's view. PLAN.md and STATUS.md stay the agent's source of truth | Two sources of truth drift. One is canonical, the other is a projection. |
| D25 | Autonomous session commits to `main` after every green task | Solo repo, small commits, every task leaves a checkpoint that survives compaction and crashes. |

## Added during the build

Locked on 2026-09-07 during the day 0 session unless a later date is noted.

| ID | Decision | Why |
|---|---|---|
| D26 | The planning folder became the repo root and its files moved to `docs/`, rather than a new repo being created beside it | Same result as the plan intended, one less path to keep in sync, and the working directory never moves out from under a running session. |
| D27 | Hugging Face downloads run with `HF_HUB_DISABLE_XET=1` | The Xet backend stalled at 65 MB of a 4.4 GB download and stayed there. The classic HTTP path ran at about 3.7 MB/s immediately. Measured 2026-09-07 on M1 Max. This has to carry into the packaged app's first-run download, not just into development. |
| D28 | Conventions live one file per domain in `docs/conventions/`, and `AGENTS.md` stays a map | A single 900 line agent file gets skimmed. A reader opening `react.md` before renderer work reads all of it. |
| D29 | `sidecar/` uses a src layout, `sidecar/src/sidecar/` | Tests import the installed package rather than the working directory, so a missing entry in the packaging config fails in the test run instead of in the DMG. |
| D30 | Typefaces ship as files in the bundle. No font CDN, in any environment | A request to a font CDN on app launch would contradict the README's privacy claim. The claim is a specification, so the build cannot have a development-only exception. |
| D31 | `peft` is a sidecar runtime dependency | `vidore/colqwen2-v1.0` is a LoRA adapter over `vidore/colqwen2-base`, and Sentence Transformers refuses to load it without `peft`. Found by the day 0 spike failing on it. |
| D32 | The Anthropic base URL is a setting, so the end-to-end chat test points at a local stub that speaks the streaming wire format | Keeps the third money path runnable offline, for free, on every gate, which is the only way that test survives the week. |
