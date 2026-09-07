# Launch

Load `direct-copy`, `humanizer` and `spoken-script` before writing any of the final words.
This file holds structure and claims, not copy.

## Video, 45 seconds

1. Wi-Fi icon off. Search box. Type "stripe webhook error screenshot". PNG appears, heatmap glows on the red dialog. Three seconds on the glow.
2. Type "slide with the funnel chart". The slide appears. Cut to the page text to show no matching words.
3. Wi-Fi on. Ask "what did the Q2 hosting invoice charge for egress". Answer streams, citation chip, click, page with heatmap on the line.
4. Index screen. Files scanned, pages embedded, storage, one folder excluded. Hold two seconds.
5. Terminal: `git clone`, DMG in Finder. End card with the repo.

Record at 2x scale on a clean user account with the demo corpus.
No cursor wandering.
No narration in the first cut, captions carry it.

## Screenshots

1. Heatmap on a screenshot.
2. Heatmap on a chart-only slide.
3. Chat answer with citation chips.
4. Index screen with skip reasons visible.
5. Architecture diagram from ARCHITECTURE.md rendered clean.

## Post structure

Hook: the query that no filename search can answer, and the page lighting up.
The bet: retrieval on page images, not OCR text, and why that finds charts.
The hard part: lazy two-stage indexing, so a 40,000 file disk needs a few thousand embedded pages, not all of them.
The proof: measured numbers table.
The privacy line, stated exactly as below.
Repo link.

## Claims the README and post may make

- The index and every embedding stay on this machine.
- The only network calls are the first-run model download and the answer step. The answer step sends the matched pages to Anthropic. Offline mode turns it off.
- No analytics.
- Every number is measured, with machine, model and date next to it.

Do not claim: "100 percent offline" while chat exists. "Never sends data" without the qualifier. Any number that was estimated.

## Where

X thread with the video first.
LinkedIn with the architecture angle.
Show HN with the two-stage indexing as the headline technical idea.
r/LocalLLaMA and r/macapps.
Write the architecture post the week after launch.
