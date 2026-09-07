# Status

Updated: 2026-09-07, autonomous build session.
Repo: this folder. Planning docs moved to `docs/` on day 1.
Linear: `Local file RAG v1` on team `diepen`, 57 issues, DPN-224 to DPN-280.

## Now

Day 1. Sidecar skeleton and corpus are done. Waiting on the Electron scaffold, then the store, crawler and gate.

## Next

`store.py` LanceDB tables, then `crawl.py` and `gate.py` against the 280 file demo corpus.

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
