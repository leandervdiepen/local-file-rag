# Demo corpus

`make_demo_corpus.py` generates a synthetic, deterministic corpus for
developing and evaluating search: about 280 files across screenshots, PDF
reports, slide decks, notes, and junk the gate must skip.
Nothing here is real; every name and number is invented.

## Run it

```bash
uv run scripts/make_demo_corpus.py --out ~/demo-corpus
```

No project setup needed: dependencies are declared inline and `uv` installs
them into an ephemeral environment on first run.
Playwright's browser is separate from those dependencies.
If screenshots come up short, install it once:

```bash
uv run --with playwright playwright install chromium
```

## Options

| Flag | Default | Does |
|---|---|---|
| `--out` | `~/demo-corpus` | output directory |
| `--seed` | `20260907` | same seed, same bytes, every group |
| `--only` | all groups | regenerate one group: `screenshots`, `reports`, `decks`, `notes`, `junk` |

Each run writes `MANIFEST.json` in the output root: every file, its group,
whether the gate should index or skip it, and why.

## Files

- `corpus/` - one module per group, plus shared helpers: `rng.py`
  (deterministic randomness, word banks), `charts.py` (matplotlib),
  `manifest.py` (the manifest writer).
- `golden.jsonl` - 30 queries for recall evaluation. Ten have no matching
  words on the target page, so only image retrieval can win them.

## Run an eval

`eval.py` runs `golden.jsonl` through a running sidecar and writes one run directory under `eval-runs/`.

```bash
uv run scripts/eval.py --base-url http://127.0.0.1:PORT --token TOKEN
```

The sidecar must already have `~/demo-corpus` indexed.
`--corpus`, `--golden` and `--out` override the defaults, which are `~/demo-corpus`, `scripts/golden.jsonl` and `scripts/eval-runs`.
The exit code is 1 when any query that hit at 5 in the previous run misses now, so a day gate can run it as a check.
It is 2 when the run could not complete.

Each run lands in `eval-runs/<UTC timestamp>_<short sha>/`:

| File | Holds |
|---|---|
| `run.json` | who ran what: git sha, dirty flag, machine, corpus seed and manifest hash, golden sha, the previous run id, the aggregates, the regressions |
| `queries/<id>.json` | one file per golden query with its candidates, ranks, hits, timings and, on a miss, the thumbnail paths |
| `thumbs/` | thumbnails of the expected page and the rank 1 page, misses only |
| `errors.jsonl` | one line per attempt that produced nothing scorable, with a class; empty when nothing failed |
| `report.html` | the report, one file that opens offline |

`eval-runs/LATEST` names the newest run, and the next run compares itself against it.

## Read the report

The top of the page compares this run with the previous one: the identity strip, `hit@5` as a count out of 30 with the delta, `mrr@10`, and `hit@5` per `text_free` value and per `match_channel` value.
Regressions come next: every query that hit at 5 last run and misses now, with its query text, the expected page and the page that took rank 1.
That section stays collapsed when nothing regressed.
Below it is every query as a table, sortable by clicking a column header.
A red delta or a red query id is the only colour on the page, so a report with no red needs no reading.

`match_channel` says what a query gives the retriever to work with: `visual` when only the picture answers it, `filename` when the query names the file, `content` when the page text has to win.

Not built yet: `--cold`, which would clear `page_vectors` before the run, so `cold` in `run.json` is always `false`; the answer half with `golden_answers.jsonl` and the judge, which wait for Day 4 and leave `answer_model`, `judge_model`, `judge_prompt_sha` and `prices_read_on` as `null`.
