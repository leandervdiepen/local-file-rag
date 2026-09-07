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
