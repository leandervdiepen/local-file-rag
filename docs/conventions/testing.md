# Testing

A pyramid, not theater.
The tiers and what runs when are in the root `AGENTS.md`. This file is how to write a test that earns its place.

## What a test is for

A test fails a build when the thing it caught is wrong, not when it could be better.

That single rule decides most arguments:

- A rule with a reason outside taste fails the build. Dependency direction, a gate reason, MaxSim against a reference, an SSE stream that never terminates.
- An arithmetic threshold warns. Latency budgets and recall targets are measured and reported, and they gate a day, not a commit. Hardware varies and a flaky perf assertion trains people to rerun until green.
- Marketing wording is never pinned. Copy changes weekly and a test that breaks on a comma is a tax on writing.

## Unit

The most tests, seconds to run, on every task.

Everything in `sidecar/domain` and `sidecar/application`, everything in `renderer/domain` and `renderer/application`.
Ports get fakes, written by hand in `tests/fakes/`. Not mocks with expectations about call order, because that asserts the implementation rather than the behavior.

A fake is a real, working, in-memory implementation of the `Protocol`. A `FakePageStore` that actually stores pages in a dict is worth more than fifty mock assertions, and it gets reused everywhere.

Specific things that must have unit tests, because each one has burned someone:

| Subject | Test |
| --- | --- |
| gate rules | every skip reason, including the boundary case that just passes |
| MaxSim | scored against a naive nested-loop reference on random matrices |
| heatmap grid | portrait, landscape and square pages map to the right rows and cols |
| citation parsing | `[1]`, `[1][2]`, `[12]`, a bracket that is not a citation, an out-of-range index |
| SSE encoding | every event type round trips, including one split across chunk boundaries |
| result grouping | pages from one file group, ordering is stable, ties break the same way twice |
| keyboard state | arrows cross group boundaries, escape unwinds in the documented order |
| cost math | token counts to dollars at the current price, with zero and with a huge count |

## Integration

Some tests, run when the adapter changes.

Each adapter against its real dependency, in a temp directory that is deleted after.
LanceDB against a real database. pypdfium2 against fixture PDFs committed to the repo. Apple Vision OCR against a fixture PNG. Flask routes through the test client with fake ports. The sidecar handshake driven from the Electron main process.

Mark them `@pytest.mark.integration` so `make check` skips them and `make check-int` runs them.
Anything that loads the embedding model is also `@pytest.mark.slow` and runs at day gates only. One page, not a corpus.

Fixtures are small and committed. A fixture PDF is three pages, not three hundred.

## End to end

The fewest tests, at day gates and before shipping.

Playwright driving the real Electron app on three money paths:

1. Index a folder, search, see a result with a thumbnail.
2. Click a result, see the heatmap on the page.
3. Ask a question, see a streamed answer with a citation, with the Anthropic client pointed at a local stub through the base URL setting.

That stub is a real fixture, not a mock: a tiny HTTP server that speaks the Anthropic streaming wire format.
It lets the whole chat path run in CI, offline, for free, and it is the only way this test stays fast enough to keep.

End-to-end tests never run in the inner loop. They are slow and flaky by nature, so they guard gates, not edits.

## Determinism

A test that fails one run in twenty is worse than no test, because it teaches people to rerun.

- Never assert on wall clock time in a unit test. Inject the clock.
- Never depend on dict or filesystem ordering. Sort before asserting.
- Seed every random source. The demo corpus generator takes a seed for exactly this reason.
- Wait for a condition, never for a duration. A `sleep` in a test is a bug that has not fired yet.

Fix flakiness on sight, including in a test you did not write and that has nothing to do with your task.

## Coverage

A signal, not a target.

Domain and application near complete, because they are cheap to cover and that is where the logic is.
Adapters covered through integration.
UI covered through the three paths plus component tests where a component holds logic.

Nobody adds a test to raise a number.
