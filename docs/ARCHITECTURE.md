# Architecture

## Process model

```
Electron main ──spawn──▶ sidecar (Flask + waitress, loopback, random port, bearer token)
     │                        ├── indexer threads: crawl, hash, gate, extract, OCR, FTS upsert
     │                        ├── watchdog (FSEvents)
     │                        ├── embedder: MultiVectorEncoder on MPS, loads lazily, unloads when idle
     │                        ├── LanceDB directory in ~/Library/Application Support/<app>/db
     │                        └── answer adapters, one per wire format (chat only)
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
| `GET /health` | status, version, whether the model is loaded, how far any download has got, db path |
| `GET /folders`, `POST /folders`, `PATCH /folders/{id}`, `DELETE /folders/{id}` | manage indexed folders. `PATCH` takes `{"enabled": bool}` and a folder that is off keeps its rows and stops being searched |
| `GET /index/stats` | counts and storage for the index screen |
| `GET /index/files?state=&cursor=` | files by state, with skip reasons |
| `POST /index/rescan` | start a crawl of every enabled folder |
| `DELETE /index/files/{id}` | forget one file, rows and vectors, leaving the file on disk |
| `GET /index/progress` | SSE: `progress` per file crawled, one terminal `done`. Ends immediately when no job is running |
| `GET /search?q=` | SSE: `candidates` right after stage 1, `progress` while embedding, `results` when reranked |
| `GET /pages/{id}/image?size=thumb\|full` | rendered page PNG. A `full` request counts as the user opening that page |
| `GET /pages/{id}/heatmap?q=` | JSON grid: rows, cols, tokens, per-token maps, combined map |
| `POST /chat` | body carries `question`, `provider` and `model_id`; SSE `retrieval`, `token`, `citation`, then one `done` with usage or one `error` |
| `GET /providers` | every place answers can come from, and whether each has a key |
| `GET /providers/{id}/models` | what that provider is offering now, asked of the provider (D52) |
| `GET /secrets`, `PUT /secrets/{provider}`, `DELETE /secrets/{provider}` | which providers have a key, and setting one. Held in memory only, never returned |
| `POST /eval/golden/run` | body carries the golden set and the corpus root; SSE `progress`, one `query` per row with ranks and timings, `done` with aggregates per split (D46) |

`tests/interface/test_route_table.py` reads this table and compares it with the
app's own URL map, so a route added without a row here fails `make check`.

## LanceDB tables

| Table | Columns |
| --- | --- |
| `folders` | id, path, enabled, added_at |
| `files` | id, path, folder_id, content_hash, size_bytes, mtime, kind, state, skip_reason, page_count, last_used, truncated_pages, text (FTS, the filename) |
| `pages` | id, file_id, page_no, text (FTS), last_hit_at, hit_count |
| `page_vectors` | page_id, vectors as `list<list<float16, 128>>`, pool_factor |

Four tables, not six. Query and click logging were planned and never built, so
recall is measured by the golden set runner instead (D46).

`page_vectors` gets a cosine index once it passes a few thousand rows.
Multivector search in LanceDB supports cosine only.
`files.kind` is one of pdf, image, text.
`files.state` is one of text_indexed or skipped. A file is read and stored in one step, so there is no resting state between the two.

## Indexing pipeline

1. Crawl with `os.scandir`, no symlink following. Directories skipped by name: `.git`, `.hg`, `.svn`, `node_modules`, `Library`, `__pycache__`, `.venv`, `venv`, `Caches`, `.Trash`, `DerivedData`, `.next`, `dist`, `build`. Skipped by suffix: `.app`, `.framework`, `.bundle`, `.xcodeproj`, `.photoslibrary`.
   `dist` and `build` are the two worth knowing about, since a folder of your own called either is skipped without a word. `domain/gate.py` is the list, and `tests/integration/test_demo_corpus_gate.py` is what keeps this paragraph true.
2. Hash: full BLAKE3 for files under 50 MB, size plus mtime plus a sample of the head, middle and tail above that.
3. Detect kind by extension and magic bytes.
4. Gate: skip images under 300 px on the short side, files over 200 MB, icon and sprite formats. PDFs over 300 pages index the first 300 and carry a flag. Every skip records a reason.
5. Extract: pypdfium2 text per page. Apple Vision OCR for images and for PDF pages with an empty text layer, capped at 50 scanned pages per file in v1.
6. Upsert `files` and `pages` and refresh the FTS index.
7. Embed every page that has no vectors yet, reporting `pages_embedded`. Text first because it is seconds and makes search work at once, vectors second because they are the slow part (D49).

Thumbnails render at 320 px on the long side on first display. There is no disk cache: a page id names one page of one file's content, so the response carries an immutable ETag and the renderer never asks twice.
Embedding renders at 1024 px on the long side.
The processor resizes to the 768 patch budget from there.

## Query pipeline

1. Stage 1: FTS with BM25 over `files.text` and `pages.text`, filename boost, recency boost, up to 300 candidate pages. Emit `candidates`.
1a. Add up to 30 pages from a multivector search over `page_vectors`, merged into the candidate set. Every search does this, not only a thin one: see D49.
2. Candidates without vectors: embed up to 30, ordered by stage 1 score. Emit `progress` per page.
3. MaxSim over the candidate set in numpy: for each query vector take the max dot product over page vectors and sum. Query vectors are about 25 by 128, so 300 pages score in well under a second.
4. Sort by MaxSim. Exact filename matches pin to the top. Emit `results`.
5. Superseded by step 1a. The vector search is not a fallback for a thin result, it is half the candidate set on every query (D49).

## Heatmap

Re-encode the page without pooling, cache the unpooled vectors in memory, 500 pages, least recently used first (D50).
For each query token compute similarities against every patch token.
Reshape with the processor's image grid, which is rows by cols after spatial merge.
Skip instruction and special tokens.
The combined map is the max over query tokens.
Return rows, cols, tokens, per-token maps and the combined map as JSON.
The renderer draws a canvas overlay, thresholds at the 90th percentile by default, and blurs one patch radius.

## Answer pipeline

Take the top five pages after rerank and render each at 1600 px on the long side, which is `PageImageSize.FULL`.
Send them as base64 image blocks followed by the question.
System prompt: answer only from the pages, cite as `[n]` where n is the page index, say plainly when the pages do not contain the answer.
Both answerers speak their wire format over `urllib` rather than through a vendor SDK (D51), which is what keeps the PyInstaller bundle from carrying two client libraries for one streaming POST.
Which provider and model answer is the user's choice, read from their settings, and what each provider offers is asked of the provider (D52).
Map `[n]` back to page ids and emit `citation` events.
Show input and output tokens with a cost estimate in the chat footer.

## Packaging

`pnpm build` runs electron-vite.
`uv run pyinstaller sidecar.spec` produces a onedir bundle in `resources/sidecar`.
electron-builder copies it through `extraResources` and produces an arm64 DMG.
Model weights download on first run into the Hugging Face cache at `~/.cache/huggingface`, and `/health` reports the bytes as they land. Only the index database lives in Application Support.
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
  sidecar/src/sidecar/domain/          pure rules: MaxSim, heatmap, citations, the gate
  sidecar/src/sidecar/application/     use cases and the ports they depend on
  sidecar/src/sidecar/infrastructure/  adapters: ColQwen2, LanceDB, pdfium, Vision, watchdog
  sidecar/src/sidecar/interface/       Flask blueprints and the composition root
  tests/             pytest
scripts/             demo corpus fetch, golden set runner, bench
docs/                this planning folder moves here on day 1
```

Files stay small, around 200 lines, by separating concerns rather than by splitting to hit a number. Six are over it today and each is one cohesive thing.
Each file is named after what it contains.
