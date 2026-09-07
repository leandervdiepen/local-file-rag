# Architecture

## Process model

```
Electron main ──spawn──▶ sidecar (Flask + waitress, loopback, random port, bearer token)
     │                        ├── indexer threads: crawl, hash, gate, extract, OCR, FTS upsert
     │                        ├── watchdog (FSEvents)
     │                        ├── embedder: MultiVectorEncoder on MPS, loads lazily, unloads when idle
     │                        ├── LanceDB directory in ~/Library/Application Support/<app>/db
     │                        └── Anthropic client (chat only)
     ├── folder dialogs, shell.openPath, showItemInFolder, safeStorage
     └── preload exposes { baseUrl, token } and the native actions
Renderer (React) ──fetch / EventSource──▶ sidecar
```

Handshake: main spawns `sidecar --port 0 --token <random>`.
The sidecar prints `READY <port>` on stdout once `/health` answers.
Main hands the base URL and token to the renderer through the preload bridge.
On quit main sends SIGTERM and waits up to five seconds for the sidecar to flush.

## HTTP contract

All routes require `Authorization: Bearer <token>`.
Streaming routes use server-sent events.

| Route | Purpose |
| --- | --- |
| `GET /health` | status, version, model loaded, db path |
| `GET /folders`, `POST /folders`, `DELETE /folders/{id}` | manage indexed folders |
| `GET /index/stats` | counts and storage for the index screen |
| `GET /index/files?state=&cursor=` | files by state, with skip reasons |
| `POST /index/rescan`, `POST /index/forget` | manual control |
| `GET /index/progress` | SSE: `progress` per file crawled, one terminal `done`. Ends immediately when no job is running |
| `GET /search?q=` | SSE: `candidates` right after stage 1, `progress` while embedding, `results` when reranked |
| `GET /pages/{id}/image?size=thumb|full` | rendered page PNG |
| `GET /pages/{id}/heatmap?q=` | JSON grid: rows, cols, tokens, per-token maps, combined map |
| `POST /chat` | SSE: `retrieval`, `token`, `citation`, `done` with usage |
| `POST /clicks` | log a result click |
| `GET /eval/recall` | recall@1, 5, 10 over the last 100 queries |
| `POST /eval/golden/run` | SSE progress, then per-query hits and recall |
| `GET /settings`, `PUT /settings` | model, offline mode, idle embedding, storage cap |
| `PUT /secrets/anthropic` | key for this process lifetime only |

## LanceDB tables

| Table | Columns |
| --- | --- |
| `folders` | id, path, enabled, added_at |
| `files` | id, path, folder_id, content_hash, size, mtime, last_used, kind, state, skip_reason, page_count, text (FTS), updated_at |
| `pages` | id, file_id, page_no, text (FTS), embedded_at, last_hit_at, hit_count |
| `page_vectors` | page_id, vectors as `list<list<float16, 128>>`, pool_factor |
| `queries` | id, text, ts, stage1_ms, stage2_ms, candidates, cold_pages |
| `clicks` | id, query_id, page_id, rank, ts |
| `golden` | id, query, expected_file, expected_page |

`page_vectors` gets a cosine index once it passes a few thousand rows.
Multivector search in LanceDB supports cosine only.
`files.kind` is one of pdf, image, text.
`files.state` is one of scanned, text_indexed, skipped.

## Indexing pipeline

1. Crawl with `os.scandir`, no symlink following, skip list: `node_modules`, `.git`, `Library`, `*.app`, caches, hidden directories.
2. Hash: full BLAKE3 for files under 50 MB, size plus mtime plus a head sample above that.
3. Detect kind by extension and magic bytes.
4. Gate: skip images under 300 px on the short side, files over 200 MB, icon and sprite formats. PDFs over 300 pages index the first 300 and carry a flag. Every skip records a reason.
5. Extract: pypdfium2 text per page. Apple Vision OCR for images and for PDF pages with an empty text layer, capped at 50 scanned pages per file in v1.
6. Upsert `files` and `pages` and refresh the FTS index.

Thumbnails render at 320 px wide on first display and cache to disk.
Embedding renders at 1024 px on the long side.
The processor resizes to the 768 patch budget from there.

## Query pipeline

1. Stage 1: FTS with BM25 over `files.text` and `pages.text`, filename boost, recency boost, up to 300 candidate pages. Emit `candidates`.
2. Candidates without vectors: embed up to 30, ordered by stage 1 score. Emit `progress` per page.
3. MaxSim over the candidate set in numpy: for each query vector take the max dot product over page vectors and sum. Query vectors are about 25 by 128, so 300 pages score in well under a second.
4. Sort by MaxSim. Exact filename matches pin to the top. Emit `results`.
5. Fewer than five stage 1 hits: run a LanceDB multivector search over `page_vectors`, limit 20, and continue from step 3.

## Heatmap

Re-encode the page without pooling, cache the unpooled vectors as `.npy` on disk with an LRU of 500 pages.
For each query token compute similarities against every patch token.
Reshape with the processor's image grid, which is rows by cols after spatial merge.
Skip instruction and special tokens.
The combined map is the max over query tokens.
Return rows, cols, tokens, per-token maps and the combined map as JSON.
The renderer draws a canvas overlay, thresholds at the 90th percentile by default, and blurs one patch radius.

## Answer pipeline

Take the top five pages after rerank and render each at 1024 px on the long side.
Send them as base64 image blocks followed by the question.
System prompt: answer only from the pages, cite as `[n]` where n is the page index, say plainly when the pages do not contain the answer.
Model `claude-opus-5`, adaptive thinking, effort medium, streaming through `client.messages.stream`, `max_tokens` 4096.
Include the server-side fallback option the Claude API skill recommends for Opus 5 and verify the exact beta header at implementation time.
Map `[n]` back to page ids and emit `citation` events.
Show input and output tokens with a cost estimate in the chat footer.

## Packaging

`pnpm build` runs electron-vite.
`uv run pyinstaller sidecar.spec` produces a onedir bundle in `resources/sidecar`.
electron-builder copies it through `extraResources` and produces an arm64 DMG.
Model weights download on first run into Application Support with SSE progress.
Ad-hoc signing for development.
Notarization only if a developer account exists, see the open questions in PRD.md.

## Security

Loopback only, random port, per-launch bearer token.
Renderer content security policy allows `connect-src` to the sidecar origin only.
API key encrypted with `safeStorage`, sent once per launch, held in sidecar memory.
No telemetry.

## Repo layout

```
app/                 electron-vite project: main, preload, renderer
sidecar/             python package, uv managed
  sidecar/api_*.py   one file per route group
  sidecar/crawl.py extract_pdf.py ocr_mac.py gate.py store.py
  sidecar/embed.py rerank.py heatmap.py answer.py jobs.py watcher.py settings.py
  tests/             pytest
scripts/             demo corpus fetch, golden set runner, bench
docs/                this planning folder moves here on day 1
```

Every source file stays under 200 lines.
Each file is named after what it contains.
