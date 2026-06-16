# Developer tasks. `make help` lists targets.
#
# Node CLIs run straight from node_modules so package-lock.json is the source
# of truth (no npx, no globals). Go developer CLIs are pinned in tools/go.mod
# and run via `go tool` (see tools/README.md). Evals run through the evolve
# CLI (github.com/bitwise-media-group/evolve); EVOLVE points at a sibling
# checkout's binary for now and will become a pinned go-tool later.
#
# Tier 1-2 pass-throughs:
#   SKILL=name   restrict to one skill (make eval-trigger SKILL=terraform-style)
#   MODELS=spec  provider names / model ids / "all" (default: all)
#   RUNS=n       Tier-1 runs per query
#   JOBS=n       concurrent agent runs (default: ceil(cpus/2))
#   NEW=1        only run evals whose stored results are missing/incomplete

NPMBIN := ./node_modules/.bin
EVOLVE ?= ../evolve/evolve

MODELS ?= all
SKILL_FLAG = $(if $(SKILL),--skill $(SKILL))
RUNS_FLAG  = $(if $(RUNS),--runs $(RUNS))
JOBS_FLAG  = $(if $(JOBS),--jobs $(JOBS))
NEW_FLAG   = $(if $(NEW),--new)

# plugins/ ships to end users, so scaffolding templates and bundled configs
# stay header-free.
LICENSE_HOLDER := 'Bitwise Media Group'
LICENSE_IGNORE := -ignore '.git/**' \
	-ignore 'node_modules/**' \
	-ignore '.claude/**' \
	-ignore 'plugins/**' \
	-ignore 'commit.sh'

.PHONY: help lint fmt license eval-static eval-trigger eval-behavior eval report

help: ## list targets
	@awk -F": .*## " "/^[a-z-]+:.*## /{printf \"  %-14s %s\\n\", \$$1, \$$2}" $(MAKEFILE_LIST)

fmt: node_modules ## auto-format the repo with prettier (pinned in package.json)
	@ $(NPMBIN)/prettier --write .

lint: node_modules ## markdownlint all markdown (config: .markdownlint-cli2.yaml)
	@ $(NPMBIN)/markdownlint-cli2 "**/*.md"

license: ## inject SPDX license headers (addlicense, pinned in tools/go.mod)
	@ go tool addlicense -l mit -c $(LICENSE_HOLDER) -s=only $(LICENSE_IGNORE) .

eval-static: ## Tier 0 - frontmatter, manifests, version sync
	$(EVOLVE) run checks --strict

eval-trigger: ## Tier 1 - trigger accuracy + token usage
	$(EVOLVE) run triggers --models "$(MODELS)" $(SKILL_FLAG) $(RUNS_FLAG) $(JOBS_FLAG) $(NEW_FLAG)

eval-behavior: ## Tier 2 - behavioral evals + token usage
	$(EVOLVE) run evals --models "$(MODELS)" $(SKILL_FLAG) $(JOBS_FLAG) $(NEW_FLAG)

eval: ## all three tiers, then regenerate reports
	$(EVOLVE) run all --models "$(MODELS)" $(SKILL_FLAG) $(RUNS_FLAG) $(JOBS_FLAG) $(NEW_FLAG)

report: ## regenerate the EVALUATION files from stored results
	$(EVOLVE) report

# Install the pinned npm dev tools (prettier, markdownlint) exactly as locked
# in package-lock.json. Re-runs only when package.json / package-lock.json change.
node_modules: package.json package-lock.json
	npm ci
	@touch node_modules
