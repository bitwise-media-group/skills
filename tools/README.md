# tools

Developer tooling for this repo:

- `go.mod` / `go.sum` — a standalone Go [tool module](https://go.dev/doc/modules/managing-dependencies#tools) that pins
  the Go developer CLIs, so their versions are tracked without leaking into the rest of the project. There is no Go
  application here — only `tool` directives.

The three-tier eval harness is [evolve](https://github.com/bitwise-media-group/evolve) (see the Evals section in the
repo README), invoked through the `EVOLVE` Makefile variable until it is pinned here as a Go tool.

## Pinned Go tools

| Tool                           | Purpose                                           |
| ------------------------------ | ------------------------------------------------- |
| `github.com/google/addlicense` | Add / verify license headers across source files. |

The root `go.work` points the go command at this module, so a pinned tool runs as plain `go tool` from anywhere in the
repo (or just use the Makefile targets):

```sh
go tool addlicense -l mit -c "Bitwise Media Group" -s=only -check .
```

## Maintenance

```sh
go -C tools get -tool <module/path>@latest   # add another tool
go -C tools get -tool -u ./...               # upgrade pinned tools
go -C tools mod tidy
```
