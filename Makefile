.DEFAULT_GOAL := help
.PHONY: help setup check check-int e2e dev build corpus bench \
        check-sidecar check-app int-sidecar clean

SIDECAR := sidecar
APP     := app
# --directory, not --project: --project points uv at the environment but leaves
# the working directory at the repo root, so every relative path below breaks.
UV      := uv --directory $(SIDECAR)
PNPM    := pnpm --dir $(APP)

help: ## List targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk -F':.*?## ' '{printf "  %-14s %s\n", $$1, $$2}'

setup: ## Install both packages
	$(UV) sync --all-extras
	$(PNPM) install

check: check-sidecar check-app ## Lint, typecheck, unit tests, architecture tests

check-sidecar:
	$(UV) run ruff format --check src tests
	$(UV) run ruff check src tests
	$(UV) run mypy src
	$(UV) run lint-imports
	$(UV) run pytest -m "not slow and not integration" -q

check-app:
	$(PNPM) run lint
	$(PNPM) run typecheck
	$(PNPM) run depcruise
	$(PNPM) run test

check-int: int-sidecar ## Integration tests, adapters against real dependencies

int-sidecar:
	$(UV) run pytest -m integration -q

e2e: ## Playwright over Electron, the three money paths
	$(PNPM) run e2e

dev: ## Run the app against a dev sidecar
	$(PNPM) run dev

build: ## Package the sidecar and produce the arm64 DMG
	$(UV) run pyinstaller --clean --noconfirm $(SIDECAR)/sidecar.spec
	$(PNPM) run build

# The corpus generator carries its own dependencies inline, so it runs outside
# both projects. bench needs the sidecar, so it runs inside it and reaches back out.
corpus: ## Generate the demo corpus into ~/demo-corpus
	uv run scripts/make_demo_corpus.py --out ~/demo-corpus

bench: ## Measure retrieval and print the numbers
	$(UV) run python ../scripts/bench.py --corpus ~/demo-corpus --golden ../scripts/golden.jsonl

clean: ## Remove build output, keep the index and the corpus
	rm -rf $(APP)/out $(APP)/release $(SIDECAR)/dist $(SIDECAR)/build
