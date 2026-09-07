# Status

Updated: 2026-09-08, autonomous build session.
Repo: this folder. Planning docs moved to `docs/` on day 1.
Linear: `Local file RAG v1` on team `diepen`, 57 issues, DPN-224 to DPN-280.

## Now

Day 1, the interface layer. `jobs.py`: the background indexing thread and the progress endpoint it reports through.

Everything under it is done and tested. The indexing domain, the ports, every adapter, and `IndexFolder` and `Search` over them, now with the application tests that were missing.
`interface/composition.py` still registers `/health` and nothing else, so no indexing and no search is reachable over HTTP, and the renderer has nothing to call.
That is the whole of what is left on day 1: three routes, the composition root that wires the adapters into the use cases, and the search UI.

## Next

1. `jobs.py`: the background indexing thread and its progress endpoint. `IndexFolder` already takes a `ProgressSink` and nothing calls it.
2. The folder routes. `FolderStore` and `LanceDBFolders` exist and no route reaches them, so onboarding has nothing behind it.
3. The stage 1 search route. `Search.stage_one` and `encode_event` both exist, and `composition.py` registers `/health` and nothing else.
4. Renderer: folder picker on first run, search box, results grouped by file with thumbnails, and open, reveal and copy on a result. Main already exposes all three actions across the bridge.
5. The Day 1 acceptance run against `~/demo-corpus`, which is also where files per second crawled, OCR milliseconds per image and index size on disk get measured.

## Plan swaps

`KICKOFF.md` takes tasks from `PLAN.md` in order unless a dependency forces a swap, and a swap gets written down here.

| Landed early | Belongs to | Why |
| --- | --- | --- |
| The `Answerer` port in `application/ports.py`, plus `domain/providers.py` and `domain/answers.py` | Day 4 | The owner asked for multi-provider support mid-build. The shape of the answer step had to be settled before anything was written against a single vendor, and the port is what makes the difference between vendors data rather than code. D36 to D39 record what it decided. |

It landed as a port, a model registry and request types: no adapter, no route, no test.
Day 4 still owns `anthropic_answerer`, `openai_compatible_answerer` and the unit tests `conventions/testing.md` names for citation parsing and cost math.

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

Still unmeasured: stage 1 search ms, rerank ms, heatmap cold and cached, first token ms, recall@5, DMG size, index size on disk.

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
| `INDEXED_FOLDERS` in `app/src/main/allowed-paths.ts` is empty, so `isPathAllowed` rejects every path and the `shell.openPath` check guards nothing. | Security relevant. The guard reads as enforcement in review while nothing has ever been wired to the sidecar's indexed folders, so it has to be filled in the same change that first gives the renderer a path to open. |
| `app/.dependency-cruiser.cjs` exempts `src/renderer/domain/format.ts` from the `no-orphans` rule. | The exemption is the only reason a module nothing imports passes `make check`. Remove it the moment the search UI formats a size or a duration, or the rule stops catching dead code for everyone. |
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
