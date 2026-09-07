# Local file RAG desktop app

Working folder name: `local-file-rag`.
The product name is not chosen yet.
Rename the folder when it is.

A macOS desktop app that indexes your files locally, retrieves document pages by what they look like, shows you why a page matched, and answers questions with page citations.
Built as a one-week open source portfolio project.
Everything about the project lives in this folder until the code repo exists.

## Files

| File | What it holds |
| --- | --- |
| [PRD.md](PRD.md) | Problem, positioning, scope, requirements, quality bar, risks |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, process model, HTTP contract, LanceDB schema, pipelines, packaging |
| [PLAN.md](PLAN.md) | The seven days, task checkboxes, acceptance criteria, cut order |
| [STATUS.md](STATUS.md) | Where the build is right now. Read first, update last, every session |
| [DECISIONS.md](DECISIONS.md) | Every locked decision with its reason |
| [RESEARCH.md](RESEARCH.md) | What the web research found, with sources, and what it changed |
| [LAUNCH.md](LAUNCH.md) | Demo video beats, post structure, claims the README may make |
| [AGENTS.md](AGENTS.md) | Session protocol for any agent working in this folder |
| [KICKOFF.md](KICKOFF.md) | The prompt that starts the autonomous build session, and the command to launch it |

## Session protocol

1. Read [STATUS.md](STATUS.md). The `Now` section names the single next task.
2. Do that task. Check it off in [PLAN.md](PLAN.md).
3. Record measured numbers in [STATUS.md](STATUS.md) under `Measurements`. Never estimate a number that was measured.
4. If you change a locked decision, edit [DECISIONS.md](DECISIONS.md) in place and say why.
5. Before ending, rewrite `Now` and `Next` in [STATUS.md](STATUS.md).
