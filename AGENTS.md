# local-file-rag

Local file search on page images. Find the page, see why it matched, ask it a question.
macOS on Apple Silicon. Electron shell, Python sidecar, LanceDB store.

Start every session by reading `docs/STATUS.md`. Its `Now` section is the only task in flight.
`docs/PLAN.md` holds the day plan and the acceptance test that decides done.
`docs/DECISIONS.md` holds locked choices. Do not relitigate one without new evidence, and write the evidence there.
`docs/conventions/` holds the rules per domain. Read the one you are about to work in.

## Layer map

Dependencies point inward only. Both packages have the same four layers.

`sidecar/src/sidecar/` (Python)

| Layer | Holds | May import |
|---|---|---|
| `domain/` | entities, gate rules, MaxSim, heatmap grid mapping, ranking, citation parsing | stdlib, numpy |
| `application/` | use cases and the `Protocol` ports they depend on | `domain` |
| `infrastructure/` | one adapter per file, one external dependency each | `domain`, `application` |
| `interface/` | Flask blueprints, SSE encoding, auth, the composition root | all of the above |

`app/src/` (TypeScript)

| Layer | Holds | May import |
|---|---|---|
| `renderer/domain/` | types and pure functions: grouping, thresholding, keyboard state, cost math | nothing |
| `renderer/application/` | hooks that are use cases over ports | `domain` |
| `renderer/infrastructure/` | fetch and SSE adapters to the sidecar | `domain`, `application` |
| `renderer/ui/` | components in feature folders | all of the above |
| `main/`, `preload/` | process lifecycle, native actions, the typed bridge | their own layer only |

`import-linter` and `dependency-cruiser` enforce this and run in `make check`.

## Commands

`make` targets are the only commands anyone needs.

| Target | Does |
|---|---|
| `make setup` | install both packages |
| `make check` | lint, typecheck, unit tests, architecture tests, both packages |
| `make check-int` | integration tests, adapters against their real dependencies |
| `make e2e` | Playwright over Electron, the three money paths |
| `make dev` | run the app against a dev sidecar |
| `make corpus` | generate the demo corpus into `~/demo-corpus` |
| `make bench` | measure retrieval and write the numbers |

`make check` is green before every commit.
Every script under `scripts/` answers `--help`.

## How to add a use case

1. Write the port in `application/ports.py` as a `typing.Protocol`. Name it for what it provides, not who implements it.
2. Write the use case in `application/<name>.py`. Its docstring states the invariant it guarantees, not its steps.
3. Test it in `sidecar/tests/application/` with fakes for the ports. No adapter, no network, no disk.
4. Wire it in `interface/composition.py`. That is the only file that names both a use case and an adapter.

## How to add an adapter

1. Find the port it implements. The `Protocol` is the whole contract, so read nothing else.
2. One adapter per file in `infrastructure/`, named after the dependency: `lancedb_store.py`, not `store_impl.py`.
3. Everything the external library returns is converted to a domain type before it leaves the file. Library types never cross the boundary.
4. Test it in `sidecar/tests/integration/` against the real dependency in a temp directory. Mark it `@pytest.mark.slow` if it loads a model.

## Testing tiers

| Tier | When it runs | Covers |
|---|---|---|
| unit | every task, `make check` | all of `domain` and `application`, both packages |
| integration | when an adapter changes, `make check-int` | each adapter against its real dependency |
| end to end | day gates and before shipping, `make e2e` | index and search, heatmap, chat with a stubbed answerer |

A test fails a build when the thing it caught is wrong, not when it could be better.
Never pin marketing wording in a test.
Coverage is a signal, not a target.

## What not to do

- Do not add a file type, source or platform that `docs/PRD.md` puts out of scope. Park it in `docs/STATUS.md` under `Ideas parked`.
- Do not swap the retrieval model, the store or the sidecar framework without updating `docs/DECISIONS.md` first.
- Do not write a number into a doc, a README or a commit message that you did not measure. Every number carries machine, model and date.
- Do not commit a secret. The Anthropic key arrives over the local API and lives in sidecar memory only.
- Do not create `index.ts` barrels. Name a file after what is in it.
- Keep files small, around 200 lines, by separating concerns. It is a guide, not a gate: split a file because it holds two ideas, never because it holds too many lines.
- Do not write a second copy of any logic. The moment it appears, it becomes a shared module.
