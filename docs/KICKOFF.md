# Kickoff prompt

Start from the parent folder so the session sees both this folder and the repo it will create:

```bash
cd ~/code
claude --permission-mode auto
```

Auto mode lets file edits and shell commands run without a prompt per call, which is what a multi-day autonomous run needs.
Paste everything below the rule as the first message.

---

ultracode

You are starting the build of the local file RAG desktop app.
The planning folder is `./local-file-rag`.
Read, in this order: `AGENTS.md`, `STATUS.md`, `PLAN.md`, `DECISIONS.md`, `ARCHITECTURE.md`, `PRD.md`.
Open `RESEARCH.md` only when a decision needs its evidence.
Those files are the spec. Do not re-plan what they settle.

## Mission

Work through `PLAN.md` from Day 0 to the definition of shipped in one continuous session.
Stop only when every remaining task needs my input.
Before you stop, `STATUS.md` lists each open item under `Needs Leander` with what you need and why, and everything that was not blocked is done.

## How you work

- One task at a time from `PLAN.md`, in order, unless a dependency forces a swap. Write the swap in `STATUS.md`.
- The acceptance test decides done. Run it in the real app, not only in a unit test.
- After each green task: check the box in `PLAN.md`, update `Now`, `Next` and `Measurements` in `STATUS.md`, move the Linear issue, commit to `main` with a message that names the task and the Linear key. No co-author trailers, no agent names in git.
- Reversible actions inside the repo and the app data directory never need my permission. Ask before deleting anything outside them, before any force push, and before spending more than 5 USD of API credit in one day.
- When a task needs me, write it under `Needs Leander` and take the next unblocked task. Stop only when nothing is unblocked.
- After every context compaction, re-read `STATUS.md` `Now` before touching code.
- Fix lint failures, test failures and flakiness on sight, even when unrelated to the current task.

## Input from me that you will hit

- Anthropic API key for real chat runs. Check `ANTHROPIC_API_KEY` and `ant auth status` first. If neither works, build and test against the local stub server and record the real-call check under `Needs Leander`.
- Apple Developer account for notarization. Ship unsigned by default.
- Product name. Use the working name `local-file-rag` everywhere it is needed.
- Publishing the repo and the post. Prepare both, publish neither.

## Ultracode rules

- The main session owns architecture, the domain model, the UI, prompts, and every decision with taste in it.
- Workflows and subagents take only mechanical, parallel-safe slices: scaffolding the two packages at once, writing adapter tests against a fixed port, generating fixtures and the demo corpus, lint sweeps, one-file-per-agent refactors with a spec.
- At most three agents at once. Mechanical slices run on Sonnet. Design never leaves the main session.
- At each day gate, spawn one fresh verifier agent that gets only the acceptance criteria and the running app. It never sees the code. Its report decides the gate.
- Do not spawn a workflow for what one shell command does.

## Architecture: onion on both sides

Sidecar, Python, `sidecar/`:

- `domain/`: pure code, standard library and numpy only. Entities, gate rules and skip reasons, MaxSim, heatmap grid mapping, ranking and tiebreaks, citation parsing.
- `application/`: use cases and ports. Ports are `typing.Protocol` classes. Use cases: `IndexFolder`, `Search`, `ExplainMatch`, `AnswerQuestion`, `ManageIndex`, `RunGoldenSet`. Each use case docstring states its invariant, not its steps.
- `infrastructure/`: one adapter per file. `lancedb_store`, `pdfium_extractor`, `vision_ocr`, `st_embedder`, `anthropic_answerer`, `watchdog_watcher`, `fs_crawler`, `spotlight_metadata`.
- `interface/`: Flask blueprints, SSE encoding, bearer auth, and one composition root that wires adapters into use cases.
- Dependencies point inward only. `import-linter` enforces it and runs in `make check`.

App, TypeScript, `app/src/`:

- `main/`: Electron main. Sidecar process manager, native actions, `safeStorage`.
- `preload/`: the typed bridge and nothing else.
- `renderer/domain/`: types and pure functions. Result grouping, heatmap thresholding, keyboard navigation state, cost math.
- `renderer/application/`: hooks that are use cases over ports: `SearchClient`, `ChatClient`, `IndexClient`, `SettingsClient`.
- `renderer/infrastructure/`: fetch and SSE adapters to the sidecar.
- `renderer/ui/`: components by feature folder: `search/`, `preview/`, `chat/`, `index/`, `settings/`, `onboarding/`, `shared/`.
- `dependency-cruiser` enforces the boundaries and runs in `make check`.

Files stay small, around 200 lines, and are named after what they contain. The number is a guide; splitting a cohesive file to satisfy it is worse than leaving it.
No `index.ts` barrels.
Before writing anything, look for the existing thing. A second copy of any logic becomes a shared module the moment it appears.

## Testing: a pyramid, not theater

- Unit, the most, seconds, on every task: all `domain` and `application` code with fakes for ports, renderer `domain` and `application` with vitest. Cover every gate reason, MaxSim against a naive reference, heatmap grids for portrait, landscape and square pages, citation parsing, SSE encoding, result grouping, keyboard state, cost math.
- Integration, some, when the adapter changes: each adapter against its real dependency in a temp directory. LanceDB store, pdfium on fixture PDFs, Vision OCR on a fixture PNG, Flask routes through the test client with fake ports, the sidecar handshake driven from the Electron main process. The embedder test on one page is marked `slow` and runs at day gates only.
- End to end, the fewest, at day gates and before shipping only: Playwright for Electron on three money paths. Index a folder, search, see a result with a thumbnail. Click a result, see the heatmap. Ask a question, see an answer with a citation, with Anthropic replaced by a local stub through the base URL setting. Never in the inner loop.
- `make check` at the repo root runs lint, typecheck, unit tests and architecture tests for both packages. It is green before every commit. `make check-int` and `make e2e` are separate targets.
- A test fails a build when the thing it caught is wrong, not when it could be better. Never pin marketing wording.
- Coverage is a signal, not a target. Domain and application near complete, adapters through integration, UI through the three paths plus component tests where a component holds logic.

## UI direction

Minimal and spartan.
Monochrome first, one accent, generous air, real typography, no decorative motion.
Before UI work load: `better-layout`, `better-typography`, `better-colors`, `better-ui`, `better-accessibility`, `better-writing`, `emil-design-eng`, `make-interfaces-feel-better`, `vercel-react-best-practices`, `vercel-composition-patterns`.
Load `impeccable` for the Day 6 pass.
Motion only where it explains a state change: indexing progress, streaming text, the heatmap reveal.
Keyboard first.
Design every state: first run, empty, loading, error, offline, model downloading, sidecar down.
Copy says what happens, never what will not happen.

## A codebase for humans and agents

- Root `AGENTS.md` under 120 lines, with `CLAUDE.md` pointing to it: layer map, the `make` targets, how to add a use case, how to add an adapter, the testing tiers, what not to do.
- Move `./local-file-rag` into the repo as `docs/` on Day 1 and keep every file in it current. `DECISIONS.md` grows by rows.
- Ports are the contract. An agent must be able to implement an adapter from the Protocol alone.
- Every script has `--help`. `make` targets are the only commands anyone needs to know.

## Linear

A Linear team, reached over MCP.
Create the project `Local file RAG v1` once, with milestones Day 0 through Day 7 and one issue per `PLAN.md` task carrying its acceptance test in the description.
Move issues to In Progress and Done as you go.
`PLAN.md` and `STATUS.md` stay your source of truth. Linear is my view.
Never file an issue that would still be true in six months. That is a doc.

## Measured, not guessed

Every number in `STATUS.md`, the README or a commit message comes from a run you did, with machine, model and date.
If you did not measure it, do not write it.

## Order of operations right now

1. Linear project and issues, one pass.
2. Day 0 spike: seconds per page on MPS with `vidore/colqwen2-v1.0` through `MultiVectorEncoder`. Record it. Above 3 seconds per page, apply the fallback from the PRD risk table and write the decision down.
3. Day 0 corpus: `scripts/make_demo_corpus.py` generates a realistic synthetic corpus. Chart-heavy PDFs with matplotlib, slide-style PDFs, screenshots rendered from HTML with Playwright including an error dialog whose only text is inside the image, invoices with an egress line, markdown notes, and junk that the gate must skip. Write `scripts/golden.jsonl` with 30 queries, nine of which have no matching words on the target page. Real files from my Desktop or Downloads are read only and never committed.
4. Day 1 onward per `PLAN.md`.

Go.
Report only when a day gate passes or you are stopped, and at a gate the report is `STATUS.md`.
