# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

# skills — the Claude skill/plugin marketplace and its evaluation suite.
#
# The reusable helpers come from the shared Makefile library
# (bitwise-media-group/make), consumed as the make/ submodule: help/commit from
# common.mk, the SHA-pinned Go CLIs (addlicense + the evolve eval CLI) from
# gotools.mk, license headers from license.mk, and the node_modules sentinel +
# prose format/lint from node.mk. skills composes the fragments directly rather
# than including a whole archetype, because its `test` is real (evolve eval
# thresholds) and `lint` needs the claude CLI plus the evolve/JSON/shell checks.
include make/fragments/common.mk
include make/fragments/gotools.mk
include make/fragments/license.mk
include make/fragments/node.mk

.PHONY: fmt lint build test e2e ci pr triggers evals all report evolve-checks

fmt:  fmt-prose license   ## auto-format prose + inject license headers
# Order matters: install the claude CLI (npm run lint's plugin-validate needs it)
# before lint-prose runs it, then the evolve/JSON/shell checks after.
lint: license-check node_modules/.claude-cli lint-prose evolve-checks ## all check-mode static analysis
build: ## no-op build gate (nothing to compile) so the reusable CI `make build` job passes
	@ :
test: $(EVOLVE) ## validate the plugins and that eval results meet the minimum thresholds
	@ $(EVOLVE) run checks
	@ $(EVOLVE) report --check --junit=coverage/junit.xml --cobertura=coverage/cobertura-coverage.xml
e2e: ## no-op: no end-to-end tests
	@ :
ci:   lint build test            ## the gates the reusable CI workflow runs
pr:   fmt lint build test commit ## full local gate before a pull request

# The extra check-mode analysis folded into `lint`: evolve's own checks, the eval
# fixtures' JSON validity, and the installer's shell syntax.
evolve-checks: node_modules $(EVOLVE)
	@ $(EVOLVE) run checks --strict
	@ for f in plugins/*/evals/*/*.json; do \
		jq -e . "$$f" >/dev/null || { echo "invalid JSON: $$f"; exit 1; }; \
	done
	@ sh -n install.sh

triggers: $(EVOLVE) ## Tier 1 - trigger accuracy + token usage
	@ $(EVOLVE) run triggers --new --modified

evals: $(EVOLVE) ## Tier 2 - behavioral evals + token usage
	@ $(EVOLVE) run evals --new --modified

all: $(EVOLVE) ## all three tiers, then regenerate reports
	@ $(EVOLVE) run all --new --modified

report: $(EVOLVE) ## regenerate the EVALUATION files from stored results
	@ $(EVOLVE) report

# `npm run lint` runs `claude plugin validate`, which needs the claude-code CLI.
# npm ci --ignore-scripts skips the package's own install step, so run it here once.
# The sentinel lives under node_modules/ (git-ignored, wiped whenever npm ci re-runs).
node_modules/.claude-cli: node_modules
	@ node node_modules/@anthropic-ai/claude-code/install.cjs
	@ touch node_modules/.claude-cli
