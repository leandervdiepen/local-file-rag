# Status

Updated: 2026-09-08, autonomous build session.
Repo: this folder. Planning docs moved to `docs/` on day 1.
Linear: `Local file RAG v1` on team `diepen`, 57 issues, DPN-224 to DPN-280.

## Now

Day 2, the vision path. `embed.py`: lazy ColQwen2 load on MPS, float16, pooling factor 3, unloaded after ten idle minutes.

Day 1 is accepted. Every route in the day 1 slice is served, the renderer searches a real index with thumbnails, and the numbers are in the table below.
The evaluation research the owner asked for is running in parallel and lands in `docs/research/evaluation-2026-09.md`; see `Plan swaps`.

## Next

1. Page rendering at 1024 px long side for embedding, through the `PageSource` port that already renders at any size.
2. `page_vectors` writes and reads, and the cosine index once the row count passes 2,000. This is also where LanceDB earns or loses its 438 MB: see the risk below.
3. `rerank.py`: MaxSim in numpy over a candidate set.
4. The semantic fallback when stage 1 returns fewer than five pages.
5. `scripts/bench.py`, and the Day 2 acceptance: "slide with the funnel chart" finds the right slide with no matching page text.
6. The evaluation framework, once the research doc is in: golden runner behind `POST /eval/golden/run`, recall by query type, and the answer judge once Day 4 has answers to judge.

## Plan swaps

`KICKOFF.md` takes tasks from `PLAN.md` in order unless a dependency forces a swap, and a swap gets written down here.

| Landed early | Belongs to | Why |
| --- | --- | --- |
| The `Answerer` port in `application/ports.py`, plus `domain/providers.py` and `domain/answers.py` | Day 4 | The owner asked for multi-provider support mid-build. The shape of the answer step had to be settled before anything was written against a single vendor, and the port is what makes the difference between vendors data rather than code. D36 to D39 record what it decided. |

It landed as a port, a model registry and request types: no adapter, no route, no test.
Day 4 still owns `anthropic_answerer`, `openai_compatible_answerer` and the unit tests `conventions/testing.md` names for citation parsing and cost math.

| Coming forward | Belongs to | Why |
| --- | --- | --- |
| Evaluation: the golden runner behind `POST /eval/golden/run`, `scripts/eval.py` with a self-contained `report.html` and a regression diff against the previous run | Day 6 | The owner asked for it on day 1, 2026-09-08, with research first. The research (`docs/research/evaluation-2026-09.md`) settled D45 to D48. The retrieval half runs against stage 1 today and its first run is the stage 1 ceiling the Day 2 delta is measured from. The answer half, `golden_answers.jsonl` and the judge wait for Day 4 to produce answers. `bench.py` keeps speed and size; the runner owns recall and the splits. |

## Blockers

None blocking. Two items need Leander, neither stops the build.

## Needs Leander

| What | Why | What happens meanwhile |
| --- | --- | --- |
| An Anthropic API key, or `ant` CLI auth | `ANTHROPIC_API_KEY` is unset and `ant` is not installed, so no real chat call has been made | Day 4 builds and tests against a local stub that speaks the Anthropic streaming wire format. The real-call check stays open until a key exists. |
| Whether an Apple Developer account exists | Decides notarization on day 7 | Shipping unsigned per D18, with the quarantine removal instruction in the README. |

## Measurements

M1 Max, 64 GB, macOS 26.5.1, torch 2.14.0, sentence-transformers 6.0.1, 2026-09-07.
Model `vidore/colqwen2-v1.0-merged` in float16 unless noted. Three rendered A4 pages at 1024 px long side.

| Metric | Value | Note |
| --- | --- | --- |
| Model load time | 8.5 s | 12.8 s for the adapter build over `colqwen2-base` |
| Seconds per page, cold embed | 1.19 s | warm average, first page costs 3.6 s to lazy kernel compilation |
| Vectors per page before pooling | 747 x 128 | |
| Vectors per page after pooling at factor 3 | 249 | |
| KB per page after pooling, float16 | 62 KB | PRD estimated 80 KB |
| Query encode | 275 ms, 19 tokens | |
| Sidecar RSS with the model loaded | 1.7 GB | steady state, under the 6 GB target |
| Sidecar peak RSS during model load | 8.7 GB | transient, see the risk below |
| First run model download | 4.43 GB | 8.94 GB before D33 |
| Corpus generation | 280 files, 5.5 s | 130 indexable, 150 skipped across 7 reasons |

### Day 1, indexing and stage 1

M1 Max, 64 GB, macOS 26.5.1, Python 3.13.5, lancedb 0.38, 2026-09-08. `~/demo-corpus` at 283 files, driven over HTTP against the real sidecar.

| Metric | Value | Note |
| --- | --- | --- |
| Files crawled | 275 of 283 | The 8 under `.git` and `node_modules` are never walked, which is the point of excluding them |
| Files indexed, skipped | 130, 145 | Agrees with the manifest on every file, zero mismatches, all seven skip reasons exercised |
| Pages indexed | 218 | |
| Crawl time | 14.6 s, 18.8 files/s | OCR bound: 40 screenshots and every blank PDF page go through Vision |
| OCR per image | median 106 ms, p90 129 ms, max 398 ms | 40 screenshots rendered at 1600 px long side, through the real adapter |
| Render for OCR | median 73 ms | pypdfium2 and Pillow, same 40 images |
| Stage 1 search, server | 28 to 44 ms | 4 queries: two content, one filename, one OCR text |
| Stage 1 search, wall | 29 to 46 ms | Over loopback HTTP including the SSE frame |
| Thumbnail, first render | 30 to 83 ms | 320 px, then immutable and cached by the renderer |
| Index on disk | 6.1 MB | Text and BM25 only. `page_vectors` arrives on day 2 |

Still unmeasured: rerank ms, heatmap cold and cached, first token ms, recall@5, DMG size.

### dtype and build sweep

Each row is its own process, so the memory numbers are not contaminated by a previous load.

| Model | dtype | s/page | RSS loaded | Peak RSS | Winner score |
| --- | --- | --- | --- | --- | --- |
| colqwen2-v1.0 adapter | float16 | 1.25 | 1.8 GB | 12.8 GB | 12.93 |
| colqwen2-v1.0-merged | float16 | 1.19 | 1.7 GB | 8.7 GB | 12.92 |
| colqwen2-v1.0-merged | float32 | 1.49 | 2.8 GB | 12.8 GB | 12.95 |
| colqwen2-v1.0-merged | bfloat16 | 1.81 | 0.9 GB | 13.3 GB | 12.72 |

Retrieval is unchanged across all of them, so the choice is free: D33 and D34 take the fastest and smallest.

## Day 0 gate

PASS, both criteria.

- Seconds per page under 3: 1.19 measured.
- MaxSim picks the right page on a query with no matching words: page 2 scores 12.92 against 9.61 and 5.56.

The spike drew three pages, saved a real PDF, rendered it back through pypdfium2 at the resolution the indexer will use, and queried with "the screenshot of the red error dialog" against a page whose only clue is a red dialog. Page 1 carries the word "error" as a decoy and still loses.

## Day 1 gate

PASS.

- Both query kinds return under 150 ms with thumbnails: 28 to 44 ms measured on the server, under 50 ms wall.
- The OCR query "Webhook delivery failed" finds `IMG_4821.png` by text that exists only inside the pixels.
- The filename query returns the file's pages first, marked `filename`, ahead of content matches.
- The corpus is indexed end to end and reconciles against its manifest with zero mismatches.

The plan's "300 files indexed" was written before the corpus existed. The corpus has 283 files, of which 130 are indexable by design; the rest exist to exercise the seven skip reasons.

Verified over HTTP against the real sidecar and through the unit suites on both sides. The Electron window itself has not been driven against a live index yet; the Day 2 gate verifier does that first, before the vision path is judged.

Four defects the acceptance run found, all fixed before the gate was called:

- Eight `.conf` notes the corpus labelled indexable that the gate correctly refused. The fixture had widened D19. Now `.md`, and D44 records it.
- `bytes_on_disk` summed source file sizes, so the index screen would have shown 663 MB for a 6 MB index. It now measures the database directory.
- `files_scanned` counted a `SCANNED` state nothing ever wrote, so it was always zero. The state is gone and the count is every file the crawler saw.
- Text files raised on render, so a note had no thumbnail and, worse, could never be embedded or heatmapped on day 2 and 3. They now lay out as a typeset page at 1600 px and scale down.

## Risks found today

| Risk | Evidence | Response |
| --- | --- | --- |
| Peak RSS during model load is 8.7 GB | Measured. Steady state is only 1.7 GB, so this is the safetensors load, not the running model | Fine on 16 GB and up. Needs a check on an 8 GB Mac before the README claims a minimum. Not on the critical path. |
| Hugging Face Xet backend stalls | A 4.4 GB download sat at 65 MB with no progress for minutes. Classic HTTP ran at 3.7 MB/s immediately | D27: `HF_HUB_DISABLE_XET=1`, and it has to carry into the packaged app's first run download, not just development. |
| `transformers` silently ignores `torch_dtype` | Passing the old name loaded fp32 and doubled memory with no error | Use `dtype`. Worth an assertion in the embedder that the loaded dtype is the requested one. |

## Known debt

True now, and each one costs more the later it is paid.

| Debt | Why it matters |
| --- | --- |
| `isPathAllowed` compares resolved paths only, so a symlink inside an indexed folder that points outside it still opens. | Closing it needs the real path of the target, a filesystem call per click. Cheap, and worth doing before the index screen makes opening files routine. Main now reads the allowed roots from the sidecar's `GET /folders` on every check, so the list itself is no longer the gap. |
| TypeScript is pinned to 5.9.3 and Vite to 7.3.6 by ecosystem compatibility, not by choice. | Nothing in the repo records which package forces which pin, so the next attempt to bump one rediscovers the break instead of reading about it. |
| shadcn/ui is not installed. `ui/shared/Button.tsx` and `ui/shared/Screen.tsx` are hand rolled. | D01 and the Day 1 scaffold both name shadcn/ui. Every screen after the onboarding states either adopts it or D01 needs a row saying it was dropped and why. |
| Nothing removes stale rows. A file that stops being readable keeps the pages it had, so the index screen calls it skipped while a search still returns its content. | Breaks `IndexFolder`'s stated invariant, which is the promise the index screen is built on. Measured, not inferred: see D43. It is scheduled, not forgotten. Day 5 owns it, and `content_hash_of` is the method it needs. |

## Open questions

- Product name. Working name `local-file-rag` used everywhere, behind one constant.
- Public corpus for reproducible numbers, or publish the demo corpus recipe. The generator is deterministic under a seed, so the recipe is publishable as is.

## Ideas parked

- MCP server over the index for Claude Desktop and Claude Code.
- ColModernVBERT fast mode.
- Local answer model through MLX-VLM for a fully offline chat.
- Office formats through headless LibreOffice conversion.
- Audio notes through a local Whisper.
- Hosted team version on Postgres or Elasticsearch with Cohere or Voyage embeddings.

## Log

### 2026-09-07, planning

Explored project ideas, chose this one, researched the stack, wrote PRD, architecture, decisions, plan, launch notes. No code.

### 2026-09-07, build session

Repo created in place, planning docs moved to `docs/`. Conventions written one file per domain: product, design, copy, http-api, python, electron, react, testing.

Linear project and 57 issues created from PLAN.md.

Day 0 spike run and passed. Swept two model builds against three dtypes, six configurations, all passing both gates. Found that the merged build halves the download and the load peak for identical retrieval, and that float16 is the fastest dtype on MPS. D33 to D35 recorded.

Sidecar skeleton landed: four layers, import-linter green on three contracts, `/health` behind bearer auth, and an integration test that spawns the real CLI and reads the `READY <port>` handshake.

Demo corpus generator landed: 280 deterministic files, 7 skip reasons, three hero targets verified by reading the generated files back.

Found and fixed a real bug in the Makefile: `uv --project` points uv at the environment but leaves the working directory at the repo root, so every relative path in the check targets missed. `--directory` is the flag that moves cwd.

Electron shell landed: main owns the sidecar lifecycle with the handshake, backoff and a restart, preload exposes one typed bridge, and the renderer has all four layers behind the starting, ready, crashed and failed states.

Indexing landed everywhere except the interface layer: entities, kind detection and the gate in the domain, then the ports, then `fs_crawler`, `fs_probe`, `pdfium_pages`, `image_pages`, `text_pages`, `vision_ocr` and `lancedb_store` with its schema split out, and `IndexFolder` and `Search` over them. Nothing serves any of it over HTTP yet, and neither use case has a test.

Day 4 groundwork came forward: the `Answerer` port and the model registry. See `Plan swaps`.

`make check` and `make check-int` both green, 2026-09-08 on this machine: 96 sidecar unit tests, 75 sidecar integration tests, 43 app tests across 6 files, import-linter 3 contracts kept over 68 files and 170 dependencies, dependency-cruiser clean over 52 modules and 85 dependencies.

Day 1 debt cleared before the interface layer went on top of it. `IndexStore` gained `get_file`, `get_pages` and `content_hash_of`, and moved with the new `FolderStore` into `application/store_ports.py`, since the contracts no longer fit `ports.py` under the line budget. `IndexFolder` and `Search` got the tests they never had, and those tests found two real bugs: the OCR budget capped page numbers rather than pages sent to OCR, so a scanned appendix starting on page 200 got none of its unspent budget of 50, now fixed; and nothing removes stale rows, now D43 and scheduled for day 5. The demo corpus was refusing its own oversized and empty files at the type check, so two of the seven skip reasons were never exercised by it, and a full regeneration was doubling the manifest. Both fixed, and the corpus now stands at 282 files with every skip reason represented.

### 2026-09-08, day 1 closed

Day 1 debt cleared, then the interface layer: `IndexingJobs` on a daemon thread with per-subscriber queues, folder, index, search and page image routes, and the composition root that wires nine adapters into six use cases.
Renderer search landed: four domain modules, three hooks, five adapters including a hand-rolled SSE parser and a bounded object URL cache, and the search screen with keyboard-driven selection, grouped results and lazy thumbnails.
The allowlist in main now asks the sidecar which folders are indexed, on every check, so a renderer bug cannot open an arbitrary path.

The acceptance run against the real corpus found four defects the unit suites had passed over, listed under `Day 1 gate`. Two were in the fixture and two in the stats. One, text files refusing to render, would have blocked the vision path on day 2.

Suites at close: 174 sidecar unit, 78 sidecar integration, 86 app, import-linter 3 contracts kept, dependency-cruiser clean over 76 modules.
