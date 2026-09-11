# Contributing

Contributions are welcome.
You do not need repository access to contribute.
Fork the repository, create a branch in your fork, and open a pull request against `main`.

Report security vulnerabilities through the private process in [`SECURITY.md`](SECURITY.md), not in a public issue.

## Read the project rules

Read [`AGENTS.md`](AGENTS.md) before changing code.
It defines the product boundary, the architecture, and the rules that apply to every contribution.

Use these when your change touches their area:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) explains the layers, the route table, and where code belongs.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) records every locked decision with the reason it was locked.
- [`docs/STATUS.md`](docs/STATUS.md) holds every measurement with the machine, model and date it came from.
- [`docs/PRD.md`](docs/PRD.md) defines the scope.

## Set up the repository

Apple silicon, macOS. You need [uv](https://docs.astral.sh/uv/), Node 24 or newer, and pnpm.

```sh
git clone https://github.com/<your-account>/local-file-rag.git
cd local-file-rag
make setup
make corpus   # generates ~/demo-corpus to develop against
make dev
```

The first search downloads the retrieval model, 4.43 GB, once.
It lands in `~/.cache/huggingface` and is shared with every other project on the machine.

Provider keys for the answering step are optional.
Copy `.env.example` to `.env` for running from source.
`.env` is ignored by Git and the shipped app never reads it.

## Make a focused change

Small fixes can go straight into a pull request.
Open an issue first when a change adds product behaviour, changes the HTTP API, or may sit outside the documented scope.

Keep documentation in the same pull request as the behaviour it describes.
Documentation states what is true now and does not keep a history of what it replaced.

These rules shape every implementation:

- Nothing about a user's files leaves the machine except the three calls named in [`SECURITY.md`](SECURITY.md).
  A change that adds a fourth needs to argue against that claim first.
- Architecture dependencies point inward, on both sides.
  The Python domain layer holds the standard library and numpy, nothing else, and `make check` fails when that stops being true.
- Every number in a document comes from a run someone actually did, next to the machine, model and date it came from.
  An estimate is not a measurement and does not go in a table.
- A fake and the adapter it stands in for must agree.
  Drift between them is how this project shipped a watcher that indexed nothing while every unit test passed.

## Run the required checks

```sh
make check       # format, lint, types, import contracts, dependency-cruiser, unit tests
make check-int   # adapters against real LanceDB, real pdfium, the real filesystem
```

`make check` and `make check-int` both run in CI on every pull request and have to pass before `main` can change.

Two more suites exist and are not in CI, because they need the model or a display:

```sh
make slow   # the tests that load the real 4.43 GB retrieval model
make e2e    # Playwright drives the packaged app: index, search, open a page, read the heatmap
```

Run `make slow` when you touch embedding, reranking or the heatmap.
Run `make e2e` when you touch the window, the preload bridge, or the content security policy.

A bug fix starts with reproducing the bug the way a user hits it, not with a unit test that agrees with your theory.

## Open the pull request

Explain the behaviour that changes, why it changes, and how you verified it.
Paste the output of the run that convinced you, not a description of it.

Use a short, lowercase, imperative commit message that explains the intent:

```text
fix(pdfium): concurrent page renders aborted the whole sidecar
```

Do not use messages such as `update files`.
Do not add an agent as a co-author.
