# PRD: local file RAG desktop app

Status: v1 scope locked on 2026-09-07.
Ship target: seven working days from day 1.
Platform: macOS on Apple Silicon.

## One line

Find the page, see why it matched, ask it a question.
Local index, retrieval on page images, answers with page citations.

## Problem

Most of what sits on a Desktop or in Downloads has no useful words.
Screenshots are named `IMG_4821.png`.
Slide decks say everything in charts.
Scanned PDFs have no text layer.
Invoices and reports hide the number you need in a table.

Spotlight in macOS 26 OCRs images and ranks results with a semantic index.
It cannot show why something matched and it cannot answer a question.
Google Drive and Notion search only their own silo.
Fenn, Dhito, LocalSpider and Index are closed source.
omni-macos is open source but is search only, with no explanation of matches.
Every one of them embeds everything up front, so the first run is slow and the index fills with files nobody will ever look for.

## Who it is for

Primary user: a builder or knowledge worker on an Apple Silicon Mac with a messy Desktop, Documents and Downloads.
They know the file exists.
They cannot describe it in words a filename search would hit.

Secondary audience: CTOs, founders and engineering leads deciding whether to hire Leander for a complicated AI build.
What they must see: a hard technical bet, shipped in a week, measured, explained, and polished.
The product is the proof.

## Positioning

| | Spotlight (macOS 26) | Fenn | omni-macos | This app |
| --- | --- | --- | --- | --- |
| Runs locally | yes | yes | yes | yes |
| Open source | no | no | code Apache 2.0, weights CC-BY-NC | yes, permissive code and weights |
| Retrieval on page images | no, OCR text | not stated | one vector per chunk | multi-vector per page, late interaction |
| Shows why a page matched | no | citations only | no | patch heatmap on the page |
| Answers questions | no | yes | no | yes, streamed, page cited |
| Index visible and editable | no | no | folder filters | counts, exclusions, per-file state, skip reasons |
| Indexing cost model | eager | eager | eager, incremental | two-stage retrieval, with a storage cap instead of a cap on what is embedded |
| Retrieval eval built in | no | no | no | recall@k from clicks plus a golden set |

## Principles

1. Local by default.
   The index and every embedding stay on the machine.
   The answer step is the only network call, it is labeled, and offline mode disables it.
2. Show the work.
   Every result can explain itself.
   The index can be inspected and corrected.
3. Bound what the expensive signal costs.
   Cheap signals cover everything.
   Expensive vectors exist only for pages a query touched or a user recently opened.
4. Measure inside the product.
   The app reports its own recall.

## Hero demo

Forty five seconds, Wi-Fi off for the first half.
Type "stripe webhook error screenshot".
A PNG from Desktop appears and the red dialog glows on the heatmap.
Type "slide with the funnel chart".
A page from a deck appears, no matching text anywhere in it.
Wi-Fi on.
Ask "what did the Q2 hosting invoice charge for egress".
The answer streams with a citation, the citation opens the page, the heatmap shows the line.
Open the index screen: files scanned, pages embedded, storage used, one folder excluded.

## Scope of v1

Functional requirements.
Each one is testable.

| ID | Requirement |
| --- | --- |
| FR-1 | Onboarding offers Desktop, Documents and Downloads and lets the user add any folder. |
| FR-2 | The crawler walks enabled folders, applies the skip list, hashes contents for dedupe, records size, mtime, Spotlight last-used date and content type. |
| FR-3 | Stage 1 text comes from the PDF text layer via pypdfium2, from Apple Vision OCR for images and scanned pages, and raw for TXT and MD. It lands in a LanceDB full-text index. |
| FR-4 | A file watcher picks up new, changed and deleted files within five seconds. |
| FR-5 | One search box. Stage 1 results render in under 150 ms, grouped by file, with page thumbnails. |
| FR-6 | Stage 2 embeds candidate pages with ColQwen2 on demand, caches the vectors, and reranks by MaxSim. At most 30 uncached pages per query, with live progress text. |
| FR-7 | Every query runs a multivector search over the embedded pages and merges the result into the text candidates. This originally fired only when stage 1 returned fewer than five pages; measuring it on day 2 showed a weak text match is not a missing one, and the fallback never fired for the queries it existed to serve (D49). |
| FR-8 | Clicking a result shows the page with a patch heatmap. The user can view the combined map or one query token at a time and move a threshold slider. |
| FR-9 | Chat takes a question, retrieves pages, sends the top five page images to the provider the user picked, streams the answer, and renders citations as file plus page. Clicking a citation opens that page with its heatmap. Shipped pointing at OpenRouter, with Ollama as the option that keeps it on the machine. |
| FR-10 | Every result offers open in default app, reveal in Finder, and copy path. |
| FR-11 | The index screen shows files scanned, text indexed, pages embedded, storage used, per-folder toggles, an exclusion list, skipped files with reasons, a rescan button and a forget-file action. |
| FR-12 | When idle on AC power the sidecar embeds pages of the 200 most recently used files. |
| FR-13 | Opening a page at full size is recorded, which is what the storage cap evicts by. Not built: click logging with a query id, a recall endpoint, and a golden set runner inside the index screen. `scripts/eval.py` measures recall against a set that knows the right answer, which a stranger's own files never do. |
| FR-14 | Offline mode disables chat and says so in the chat panel. |
| FR-15 | Settings hold provider keys in encrypted storage and the answer model, chosen from what each provider is offering now. Folders live on the index screen. Idle embedding and the storage cap have no setting: they are a CLI flag and a constant, and neither has earned a control yet. |
| FR-16 | The app ships as an Apple Silicon DMG with the sidecar bundled. First run downloads model weights with progress. Search works without an API key. |

## Not in v1

Windows and Linux.
Office formats.
Mail, browser history, audio, video.
Cloud sources.
Moving or renaming files.
A local answer model.
Multi-user, sync, telemetry.
Parked ideas live in STATUS.md.

## Quality bar

Privacy: no network traffic except the explicit first-run model download and the Anthropic call during chat.
No analytics of any kind.

Latency targets on an M-series Mac, to be replaced by measured numbers on day 2:

| Path | Target |
| --- | --- |
| Stage 1 search | under 150 ms |
| Rerank of 300 cached pages | under 500 ms |
| Cold page embedding | 3 s per page or better |
| Heatmap, cold | under 2 s |
| Heatmap, cached | under 100 ms |
| Answer first token after retrieval | under 3 s |

Storage: pooled float16 vectors at roughly 80 KB per page, so 10,000 pages stay under 1 GB.
A storage cap evicts the least recently hit pages first.

Memory: the sidecar stays under 6 GB resident with the model loaded and unloads the model after ten idle minutes.

Robustness: corrupt, encrypted, empty and oversized files are skipped with a recorded reason.
A sidecar crash loses nothing because LanceDB is the only state.

Retrieval quality: recall@5 of 0.8 or better on the 30-query golden set over the demo corpus before launch.

## Numbers to publish

Pages per second on the build machine.
Kilobytes per page after pooling.
Recall@5 on the golden set, with the corpus described.
DMG size.
Time to first result on a fresh disk with about 40,000 files.

## Risks

| Risk | Fallback |
| --- | --- |
| ColQwen2 on MPS is slower than 3 s per page | Lazy cap absorbs it. Lower render resolution. Switch to ColSmol-500M without heatmaps as a last resort. |
| Heatmap grid mapping is wrong for some page aspect ratios | Use the processor grid metadata rather than inferring. Test portrait, landscape and square pages on day 3. |
| PyInstaller plus torch produces a broken or huge bundle | Ship a DMG that requires uv on the machine and say so in the README. Fix in v1.1. |
| Notarization blocks distribution | Ship unsigned with the quarantine removal instruction. |
| LanceDB multivector search behaves unexpectedly at small scale | Score MaxSim in numpy over the candidate set. LanceDB stays the store. |
| Apple Vision OCR misses on dense screenshots | Stage 2 does not depend on OCR. Log OCR coverage so the gap is visible. |

## Open questions

Product name.
Whether an Apple Developer account exists for signing and notarization.
Which public documents form the demo corpus for reproducible numbers.
