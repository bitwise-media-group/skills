# Developer tasks. `make help` lists targets; `make pr` is the full local gate.
# Every tool runs through `uv run`, so the versions resolved in uv.lock are used
# — never a global or pipx copy. The gate mirrors the CI workflow exactly.

.DEFAULT_GOAL := help
.PHONY: help pr sync fmt lint typecheck test build publish

help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

pr: fmt lint typecheck test build ## Full local gate — must pass before committing

sync: ## Install the locked dependencies (runtime + dev group) into .venv
	uv sync

fmt: ## Format code (ruff format)
	uv run ruff format .

lint: ## Lint and report (ruff check); use `make lint FIX=--fix` to autofix
	uv run ruff check $(FIX) .

typecheck: ## Type-check with ty
	uv run ty check

test: ## Run the test suite (pytest + Hypothesis)
	uv run pytest

build: ## Build the sdist + wheel into dist/
	uv build

publish: ## Publish dist/ to PyPI (Trusted Publishing in CI, or a token locally)
	uv publish
