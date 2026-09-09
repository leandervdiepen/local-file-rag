# Status

Updated: 2026-09-08, autonomous build session.
Repo: this folder. Planning docs moved to `docs/` on day 1.
Linear: `Local file RAG v1` on team `diepen`, 57 issues, DPN-224 to DPN-280.

## Now

Day 5, the rest of trust. Idle pre-embedding on AC power, the storage cap with least recently hit eviction, and the remaining error states.

Days 2, 3 and 4 are done and their gates are recorded below. The index screen and the file watcher are in, so what is left of day 5 is the two background behaviours and the states that explain a failure.

## Next

1. Idle pre-embedding and the storage cap, which are what keep the index honest on a folder larger than the demo corpus.
2. The first golden run through `scripts/eval.py`, which is written and has never been run against a live sidecar. It is the only way to steer retrieval quality with evidence rather than taste.
3. Retrieval ranking. The vision path finds 7 of 9 text-free queries and lands 4 in the top 5, so the gap is ranking rather than reach, and the pooling factor and the candidate mix are the two levers.
4. Day 6 and day 7: the eval numbers, the design pass on the states, packaging and the DMG.

## Plan swaps

`KICKOFF.md` takes tasks from `PLAN.md` in order unless a dependency forces a swap, and a swap gets written down here.

| Landed early | Belongs to | Why |
| --- | --- | --- |
| The `Answerer` port in `application/ports.py`, plus `domain/providers.py` and `domain/answers.py` | Day 4 | The owner asked for multi-provider support mid-build. The shape of the answer step had to be settled before anything was written against a single vendor, and the port is what makes the difference between vendors data rather than code. D36 to D39 record what it decided. |

It landed as a port, a model registry and request types: no adapter, no route, no test.
Day 4 still owns `anthropic_answerer`, `openai_compatible_answerer` and the unit tests `conventions/testing.md` names for citation parsing and cost math.

| Coming forward | Belongs to | Why |
| --- | --- | --- |
| The 30 page cold cap, its ordering by stage 1 score and its `progress` events | Day 3 | Stage 2 cannot rank a page it has never read, so the cap and the reading it governs had to exist the moment reranking did. It is `Search._embed_cold` over `EmbedPages`, with the route relaying progress from a worker thread, and it is tested on both sides. Day 3 keeps the heatmap, which is where its work actually is. |
| `domain/heatmap.py` and the `PageExplainer` port | Day 3 | Written on day 2 as pure functions with no adapter behind them, because the vectors domain and the `PageEmbedder` port were being settled in the same sitting and the heatmap is the second configuration of the same model (D35). Day 3 keeps the endpoint, the canvas overlay, the threshold slider and the token picker, which is where its work actually is. This adds to what day 3 starts with rather than taking from it, and day 3's cut protection is unchanged. |
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

Still unmeasured: heatmap cold and cached, first token ms, recall over the whole golden set, DMG size.

### Day 2, the vision path

M1 Max, 64 GB, macOS 26.5.1, torch 2.14.0, sentence-transformers 6.0.1, `vidore/colqwen2-v1.0-merged` in float16, 2026-09-09.

| Metric | Value | Note |
| --- | --- | --- |
| Model load plus first page | 12.7 s | Weights are already in the Hugging Face cache |
| Seconds per page, synthetic 1024 px page | 1.67 s | A sparse drawn page |
| Seconds per page, real corpus pages | 4.1 to 4.9 s | Denser pages make more visual tokens. This is the number that matters |
| Query encode | 53 ms | 19 rows scored, of which 4 are the typed words |
| Pooled rows per page | 249 | At pool factor 3 |
| Unpooled rows per page | 747 | 736 patches on a 32 by 23 grid, plus 11 prompt tokens |
| Storage per page | 58 KB | Measured over 218 pages of `page_vectors` |
| Index on disk, 218 pages | 21 MB | 12.3 MB of it vectors, against 6.1 MB for text alone |
| Search, everything embedded | 0.4 to 0.9 s | Nine text-free queries, no page left to read |

### Day 2 gate

PARTIAL PASS, and the shortfall is ranking rather than reach.

The acceptance asks that "slide with the funnel chart" returns the right slide although no page text matches. It returns it at rank 26 of 54, so the page is reachable and not yet well ranked.

Across the nine text-free golden queries, none of which stage 1 can answer at all:

| Measure | Before D49 | After |
| --- | --- | --- |
| Expected page found anywhere | 0 of 9 | 7 of 9 |
| Expected page in the top 5 | 0 of 9 | 4 of 9 |

Every one of those hits is a page BM25 could not have returned, which is the number that justifies the vision path.
The two levers on the remaining gap are the pooling factor and the candidate mix, and the golden runner is how to pull them with evidence.

### Day 3, the heatmap

M1 Max, 2026-09-09, on `IMG_4821.png` from the demo corpus with the query "stripe webhook error screenshot".

| Metric | Value | Note |
| --- | --- | --- |
| Cold heatmap | 1441 ms | Under the 2 s the plan asks for. It is one unpooled re-encode |
| Cached heatmap | 44 ms | Under 100 ms. Moving the slider or switching tokens costs nothing |
| Patch grid | 21 by 35 | 735 patches, from `image_grid_thw` halved by the spatial merge |
| Patches above the default cutoff | 74 of 735 | The 90th percentile, as designed |

### Day 3 gate

PASS on the acceptance as written, with a measured limitation worth naming.

- "stripe webhook error screenshot" returns `IMG_4821.png` first, and it is the Stripe webhook error screenshot.
- Cold 1441 ms and cached 44 ms both beat their budgets.
- The overlay was drawn and looked at, not just asserted on. The token "stripe" lands exactly on the word "stripe" inside the dialog.

The limitation: the combined map is diffuse. The dialog covers 13 percent of that page and the lit patches land on it 12 percent of the time at the default cutoff, 16 at the 95th and 25 at the 99th, so the combined view is close to chance and a tighter cutoff is not reliably better on eight patches.

Two things follow, both measured rather than assumed.
Per-token maps localize where the combined map does not: specific nouns like "stripe" and "webhook" point at real content, while "error" and "screenshot" are noise, so the token picker is not a nicety, it is how the heatmap becomes readable.
Subtracting the padding-token response, which is what a patch answers when it answers nothing, raises per-token precision (`error` 4 to 14 percent, `screenshot` 0 to 14) and lowers the combined map (12 to 7), so it was not shipped: a transform that improves the detail view and degrades the headline is not a win.

This corpus is the hardest case for patch localization, because a synthetic screenshot is mostly flat grey and gives the model nothing to distinguish in the background. The published number on real documents is a mean IoU of 0.569 (`docs/research/evaluation-2026-09.md`). Re-measure on real files before drawing a conclusion about the model.

### Day 4, chat

M1 Max, 2026-09-09, `openrouter/free` against the indexed demo corpus, five page images per answer.

| Metric | Value | Note |
| --- | --- | --- |
| First token after retrieval | 15.0 to 18.5 s | The free router is the slow part. A paid model is the lever if this matters |
| Tokens per question | about 3,300 in, 190 out | Five 1024 px page images dominate the input |
| Cost per question | 0 | D38's default is free, so development costs nothing |

### Day 4 gate

PASS.

Asked "what did the hosting invoice charge for egress", it answered:

> The hosting invoice charged $1,472.00 for data egress, based on 18.4 TB at $80.00 per TB. [1]

All three figures are exactly what the page says, and the citation resolves to `hosting-q2-2026.pdf` page 1, which is the invoice.
Asked for a sister's phone number, it answered "The provided pages do not contain the sister's phone number" and cited nothing, which is the abstention the acceptance asks for.

Two things the run found and fixed.
The free model can spend its whole budget reasoning and stream no content at all, which showed as an empty panel: a user cannot tell a refusal from a failure, so an answer with no answer in it is now reported as unavailable with a message naming what to do.
Lifting the `[1]` out of the prose left sentences like "the invoice on page  says", so the marker stays where it was written and the chip beneath repeats the number.

### Day 6, the first golden run

M1 Max, 64 GB, macOS 26.5.1, `vidore/colqwen2-v1.0-merged` in float16, pool factor 3, 2026-09-09.
30 golden queries over `~/demo-corpus` at 275 crawled files, 218 pages, all embedded before the run.
Run `20260909T165833Z_60075d8`, driven by `scripts/eval.py` against a live sidecar.

| Split | Queries | hit@1 | hit@5 | hit@10 | MRR@10 |
| --- | --- | --- | --- | --- | --- |
| Everything | 30 | 0.73 | 0.83 | 0.87 | 0.78 |
| Text bearing | 21 | 0.95 | 1.00 | 1.00 | 0.97 |
| Text free | 9 | 0.22 | 0.44 | 0.56 | 0.34 |
| Channel: content | 14 | 0.93 | 1.00 | 1.00 | 0.95 |
| Channel: filename | 7 | 1.00 | 1.00 | 1.00 | 1.00 |
| Channel: visual | 9 | 0.22 | 0.44 | 0.56 | 0.34 |

The aggregate clears the day 6 bar of 0.8, and the aggregate is the wrong number to read.
Text and filename retrieval is 21 for 21 at five.
Every one of the five misses is a visual query, which is the half of the product that has no other way to be answered.

The candidate limit is not the lever.
Sweeping it at 30, 60, 120 and 250 against one index moved nothing: 0.833 overall and 0.444 visual at every setting.
It does change what is reachable, and at 250 every page in the corpus is a candidate, so the ceiling and the floor are the same number.
That rules out recall and leaves ranking.

Looking at the pages says what ranking is doing wrong.
For "chart showing signups after the landing page redesign" the expected page is a line chart titled "Account growth" with the jump in it.
The page the model ranks first is page 3 of the same file, which is a paragraph reading "We shipped a redesigned landing page in week four and watched signups roughly double".
For "slide with the funnel chart" the first result is `notes/meetings/farid-funnel-stage-30.md`, a text note with the word funnel in it.

Both are the same failure: a page whose text says the words beats the page that shows the thing.
MaxSim gives every query token its best patch, and a page covered in text has a strong patch for every token, while a chart has a few strong ones and a lot of whitespace.
That is a density bias, and it means the visual channel is currently returning what the text channel already found.

The pooling factor is not the lever either.
Re-indexing the whole corpus at pool factor 1, which stores 747 vectors a page instead of 249, gives the same 0.833 overall and the same 0.444 visual.
Both levers named as the way forward on day 5 are now measured and both are null results.

That is worth keeping for a reason beyond retrieval: pooling at 3 costs nothing in quality and a third of the disk, so D35's factor stands on evidence rather than on the paper's default.

What is left is the fusion.
Stage 1 and stage 2 currently agree too much, because a page whose words match is a strong text candidate and a strong MaxSim candidate at the same time, and nothing in the ranking knows that the second signal added no information.
Changing that is a ranking change that would need to be measured against the 21 for 21 the text channel currently gets, and it is not something to try without the harness pointed at it.
The gate is written as recall@5 of 0.8 or better, or the gap written down with the failing queries. Both halves are now true, and the honest reading is the second one.

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
| `Page.embedded_at` and the `pages.embedded_at` column are dead. Nothing writes them and nothing reads them. | Still true. They were the second copy of a fact the vector store owns, and keeping them in step made `pages` a table two threads wrote, which `conventions/python.md` forbids. The writer is gone and `ReadIndexStats` now counts from `VectorStore`, so what is left is a field, a property, a schema column and two entity tests that describe nothing. Remove them in one sweep once the day 2 adapters are merged, since `lancedb_schema.py` is being edited in the same slice. |
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
