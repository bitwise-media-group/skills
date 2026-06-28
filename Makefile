# Developer tasks. `make help` lists targets.
#
# Node CLIs run straight from node_modules so package-lock.json is the source
# of truth (no npx, no globals). Go developer CLIs are pinned in tools/go.mod
# and run via `go tool` (see tools/README.md). Evals run through the evolve
# CLI (github.com/bitwise-media-group/evolve); EVOLVE points at a sibling
# checkout's binary for now and will become a pinned go-tool later.

# one -ignore flag per non-empty line in .licenseignore (quoted to avoid shell globbing)
LICENSE_HOLDER := 'Bitwise Media Group Ltd'
LICENSE_IGNORE := $(foreach pattern,$(shell cat .licenseignore 2>/dev/null),-ignore '$(pattern)')

.PHONY: help
help: ## list targets
	@ awk -F": .*## " "/^[a-z-]+:.*## /{printf \"  %-14s %s\\n\", \$$1, \$$2}" $(MAKEFILE_LIST)

.PHONY: pr
pr: fmt lint ## prepare a pull request

.PHONY: ci
ci: lint ## run the continuous integration checks

.PHONY: fmt
fmt: node_modules ## auto-format the repo with prettier (pinned in package.json)
	@ npm run format
	@ npm run lint:fix
	@ go tool addlicense -l mit -c $(LICENSE_HOLDER) -s=only $(LICENSE_IGNORE) .

.PHONY: lint
lint: node_modules ## markdownlint all markdown (config: .markdownlint-cli2.yaml)
	@ npm run lint
	@ go tool evolve run checks --strict
	@ for f in plugins/*/evals/*/*.json; do \
		jq -e . "$$f" >/dev/null || { echo "invalid JSON: $$f"; exit 1; }; \
	done
	@ go tool addlicense -l mit -check -c $(LICENSE_HOLDER) -s=only $(LICENSE_IGNORE) .
	@ sh -n install.sh

.PHONY: build
build: ## no-op build gate (nothing to compile) so the reusable CI `make build` job passes
	@ :

.PHONY: test
test: ## ensures that the plugins are valid and the evaluation results meet minimum thresholds
	@ go tool evolve run checks
	@ go tool evolve report --check --junit=coverage/junit.xml --cobertura=coverage/cobertura-coverage.xml

.PHONY: triggers
triggers: ## Tier 1 - trigger accuracy + token usage
	@ go tool evolve run triggers --new --modified

.PHONY: evals
evals: ## Tier 2 - behavioral evals + token usage
	@ go tool evolve run evals --new --modified

.PHONY: all
all: ## all three tiers, then regenerate reports
	@ go tool evolve run all --new --modified

.PHONY: report
report: ## regenerate the EVALUATION files from stored results
	@ go tool evolve report

# Install the pinned npm dev tools (prettier, markdownlint) exactly as locked
# in package-lock.json. Re-runs only when package.json / package-lock.json change.
node_modules: package.json package-lock.json
	@ npm ci --ignore-scripts --no-fund
	@ node node_modules/@anthropic-ai/claude-code/install.cjs
	@ touch node_modules
