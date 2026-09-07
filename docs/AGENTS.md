# Agent instructions for this folder

This folder is the planning and tracking home of a one-week desktop app build.
The code repo will be created on day 1 next to this folder and linked from STATUS.md.

## Every session

- Start by reading STATUS.md. Its `Now` section is the only task in flight.
- Read PLAN.md for the day you are in. Acceptance criteria decide when a task is done, not effort spent.
- End by updating STATUS.md: what was done, measured numbers, the new `Now`, the new `Next`, open blockers.
- Keep DECISIONS.md the single source of truth for locked choices. Do not relitigate one without new evidence. Record the evidence when you do.

## Standards that apply here

- Leander's global CLAUDE.md applies in full: no em dashes, no agent co-author trailers, small files, lint and tests green, comments explain why.
- Reproduce before fixing. For this app that means a real folder of real files, indexed through the real sidecar, viewed in the real Electron window.
- Be picky about the UI. The heatmap and the index screen are the launch video. Anything that looks off gets fixed on sight.
- Numbers in docs come from measurement. Write the machine, the model, and the date next to every number.

## What not to do

- Do not add file types, sources, or platforms that are out of scope in PRD.md. Write them in STATUS.md under `Ideas parked` instead.
- Do not swap the retrieval model, the store, or the sidecar framework without updating DECISIONS.md first.
- Do not commit secrets. The sidecar reads the Anthropic key from the macOS keychain or an env var, never from a tracked file.
