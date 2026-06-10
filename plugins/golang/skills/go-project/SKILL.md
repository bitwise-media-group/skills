---
name: go-project
description: Scaffold a Go project with the canonical layout — cmd/ entrypoints with a thin main, private packages under internal/, a separate tools module pinning Go developer CLIs (invoked directly via go tool, no GOBIN), Node tools pinned in package.json and run from node_modules/.bin, and a Makefile whose pr target runs the full local gate. Use when creating a new Go project, service, or repository, restructuring an existing Go repo to the standard layout, pinning Go or Node developer tooling, or adding standard Makefile targets (pr, fmt, vet, test, fuzz, build) to a Go codebase.
license: MIT
---

# Scaffold a Go project

Creates a Go repository with the canonical layout, pinned tooling, and a Makefile gate. Apply the
`go-style` and `go-testing` skills while filling in real code, and wire releases with the
`go-release` skill.

## 1. Lay out the tree

```text
cmd/<app>/main.go     # one directory per binary; main stays thin
internal/<pkg>/       # all business logic; the compiler enforces privacy
tools/                # separate Go module pinning developer CLIs
Makefile
go.mod  go.sum
package.json          # pins Node tooling (prettier, markdownlint-cli2)
```

- One package per concern, named for what it provides (`clientmap`, `token`, `telemetry`) — never
  `util`, `common`, or `helpers`.
- No `pkg/` directory: code stays under `internal/` until a consumer outside the repo needs it.

## 2. Keep `main` thin

Copy [templates/main.go](templates/main.go): `main` derives the root context from process
signals, builds the JSON `slog` logger, and delegates to `run(ctx, log, args) error`. Everything
testable lives in `run` and the `internal/` packages; `main` is the only place that may call
`os.Exit`.

## 3. Pin Go developer CLIs in a separate tools module

Developer tools (`addlicense`, `goreleaser`, `syft`, …) are pinned in `tools/go.mod` — its own
module, so their large dependency graphs never touch the application's `go.mod`:

```text
module example.com/myapp/tools

go 1.26

tool (
	github.com/google/addlicense
	github.com/goreleaser/goreleaser/v2
	github.com/anchore/syft/cmd/syft
)
```

Add a tool with `go -C tools get -tool <module>@<version>` and invoke it directly with `go tool`
— no `GOBIN`, no prebuilt binaries: Go compiles the tool into the build cache on first use and
reuses it after that.

```sh
go -C tools tool addlicense -f "$PWD/LICENSE" -v "$PWD/cmd" "$PWD/internal"
```

`go -C tools` runs the tool with its working directory set to `tools/`, so pass absolute paths to
tools that touch files. A tool that must run at the repo root — goreleaser resolves
`.goreleaser.yaml` and `./cmd/...` against its working directory — is invoked as
`go tool -modfile=tools/go.mod goreleaser` instead, which stays in the current directory. Never
add a developer tool to the root `go.mod`, and never run a global or `npx`-downloaded copy.

## 4. Create the Makefile with the `pr` gate

Copy [templates/Makefile](templates/Makefile) and set `APP`. It provides:

- `pr` — the full local gate, in order: `license tidy fmt vet test fuzz build snapshot`. It must
  pass before every commit.
- Direct `go tool` invocations of the pinned CLIs (`go -C tools tool addlicense …`,
  `go tool -modfile=tools/go.mod goreleaser …`) — the build cache compiles and reuses them, so
  there is no `GOBIN` and nothing to install.
- Version metadata (`git describe`, short SHA, build date) stamped via `-ldflags -X` into
  `internal/version` — the same import path GoReleaser injects on release (see the `go-release`
  skill).
- `fuzz` parameterized by `FUZZ=` / `FUZZTIME=` / `FUZZ_PKG=`.

## 5. Pin Node tooling

`package.json` pins `prettier` and `markdownlint-cli2` as `devDependencies` at exact versions
(no ranges). `npm ci` installs them reproducibly from `package-lock.json`, and the Makefile runs
them from `node_modules/.bin` (`$(NPMBIN)/…`).

## 6. Finish

- Write the first `internal/` package and its tests (`go-style`, `go-testing` skills).
- Wire releases, CI, and Dependabot with the `go-release` skill.
- Run `make pr` and make sure it passes before committing.
