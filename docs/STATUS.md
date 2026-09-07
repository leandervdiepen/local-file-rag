# Status

Updated: 2026-09-07, planning session.
Code repo: not created yet.

## Now

Day 0 in PLAN.md.
First task: the MultiVectorEncoder spike on MPS with `vidore/colqwen2-v1.0`.

## Next

Day 1 skeleton, starting with the repo and the sidecar handshake.

## Blockers

None.

## Measurements

| Metric | Value | Machine | Model | Date |
|---|---|---|---|---|
| Model load time | | | | |
| Seconds per page, cold embed | | | | |
| Vectors per page before pooling | | | | |
| KB per page after pooling | | | | |
| Stage 1 search ms | | | | |
| Rerank ms for 300 cached pages | | | | |
| Heatmap ms cold and cached | | | | |
| First token ms after retrieval | | | | |
| Recall@5, stage 1 only | | | | |
| Recall@5, stage 1 plus 2 | | | | |
| DMG size MB | | | | |
| Sidecar peak RSS GB | | | | |

## Open questions

- Product name.
- Apple Developer account for signing. Answer on day 0.
- Public corpus for reproducible numbers, or publish the demo corpus recipe.

## Ideas parked

- MCP server over the index for Claude Desktop and Claude Code.
- ColModernVBERT fast mode.
- Local answer model through MLX-VLM for a fully offline chat.
- Office formats through headless LibreOffice conversion.
- Audio notes through a local Whisper.
- Hosted team version on Postgres or Elasticsearch with Cohere or Voyage embeddings.

## Log

### 2026-09-07

Planning session.
Explored project ideas, chose this one, researched the stack on the web, wrote PRD, architecture, decisions, plan, launch notes.
No code written.
Kickoff prompt written in KICKOFF.md.
