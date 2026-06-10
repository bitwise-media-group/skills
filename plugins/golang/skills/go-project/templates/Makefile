# Developer tasks. `make help` lists targets; `make pr` is the full local gate.
# Replace `myapp` with your binary name (the directory under cmd/).

APP     := myapp
APP_PKG := ./cmd/$(APP)
MODULE  := $(shell go list -m)

# Version metadata stamped into the binary via -ldflags. GoReleaser injects the
# same vars at the same import path ($(MODULE)/internal/version) on tagged releases.
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
COMMIT  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo none)
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w \
	-X $(MODULE)/internal/version.Version=$(VERSION) \
	-X $(MODULE)/internal/version.Commit=$(COMMIT) \
	-X $(MODULE)/internal/version.BuildDate=$(DATE)

# Fuzzing: `make fuzz` runs one target (FUZZ=) for FUZZTIME.
FUZZ_PKG ?= ./...
FUZZ     ?= Fuzz
FUZZTIME ?= 20s

# Run the Node lint/format CLIs straight from node_modules so the versions pinned
# in package.json / package-lock.json are used — never a global or npx copy.
NPMBIN := ./node_modules/.bin

# Go developer CLIs (addlicense, goreleaser, syft) are pinned in tools/go.mod — a
# separate module so their dependency graphs never touch the application's go.mod —
# and invoked directly with `go tool`: compiled into the build cache on first use,
# no GOBIN, no binaries to manage. `go -C tools tool <name>` runs the tool with its
# working directory set to tools/, so pass absolute paths ($(CURDIR)/...) to tools
# that touch files. Tools that must run at the repo root (goreleaser) use
# `go tool -modfile=tools/go.mod <name>` instead, which stays in the current directory.

.DEFAULT_GOAL := help
.PHONY: help pr fmt tidy vet license test fuzz build run snapshot release

help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

pr: license tidy fmt vet test fuzz build snapshot ## Full local gate — must pass before committing

# Install the pinned Node tools exactly as locked in package-lock.json.
# Re-runs only when package.json / the lockfile change.
node_modules: package.json package-lock.json
	npm ci
	@touch node_modules

fmt: node_modules ## Format the Go code, prose, and config (gofmt + prettier)
	go fmt ./...
	$(NPMBIN)/prettier --write .

tidy: ## Tidy the Go module references
	rm -f go.sum; go mod tidy

vet: node_modules ## Vet the Go code and lint Markdown (go vet + markdownlint-cli2)
	go vet ./...
	$(NPMBIN)/markdownlint-cli2 "**/*.md"

license: ## Inject license headers into the Go source (addlicense, pinned in tools/go.mod)
	go -C tools tool addlicense -f "$(CURDIR)/LICENSE" -v "$(CURDIR)/cmd" "$(CURDIR)/internal"

test: ## Run the unit tests (+ fuzz seed corpora)
	go test ./...

fuzz: ## Fuzz one target (FUZZ=FuzzParse FUZZTIME=20s FUZZ_PKG=./internal/keyval)
	go test -run '^$$' -fuzz '^$(FUZZ)$$' -fuzztime $(FUZZTIME) $(FUZZ_PKG)

build: ## Build the binary (./$(APP)) with version ldflags
	CGO_ENABLED=0 go build -trimpath -ldflags "$(LDFLAGS)" -o $(APP) $(APP_PKG)

run: build ## Build and run locally (override args via ARGS=...)
	./$(APP) $(ARGS)

snapshot: ## Local GoReleaser snapshot (binaries + images, no publish)
	go tool -modfile=tools/go.mod goreleaser release --snapshot --clean

release: ## Build & publish a GoReleaser release (needs a vX.Y.Z tag + creds)
	go tool -modfile=tools/go.mod goreleaser release --clean
