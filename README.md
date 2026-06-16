# bitwise skills

Agent skills and plugins from Bitwise Media Group, packaged as a marketplace for **Claude Code**, **OpenAI Codex CLI**,
**Google Antigravity**, and **OpenCode**.

Skills follow the [Agent Skills](https://agentskills.io) open standard (`SKILL.md` with portable frontmatter), live once
under `plugins/<plugin>/skills/`, and are delivered to each tool through its native mechanism — no duplicated content.

## Plugins

### golang

Modern, stdlib-first Go development conventions.

| Skill        | What it does                                                                                                                                      |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `go-style`   | House style for Go: `%w` error wrapping, sentinels, `log/slog`, context threading, consumer interfaces, stdlib `net/http`, cobra + viper CLIs.    |
| `go-docs`    | Doc comments on every exported identifier, package comments in `doc.go`, and LLM-ready CLI reference generation for cobra tools.                  |
| `go-testing` | Table-driven tests with subtests, stdlib assertions, hand-written fakes, `httptest`, and native fuzz targets with seed corpora.                   |
| `go-project` | Scaffolds the canonical layout: `cmd/` + `internal/`, a pinned tools module (`go tool -modfile=tools/go.mod`), and a Makefile with the `pr` gate. |
| `go-release` | GoReleaser v2 with version ldflags, SBOMs, multi-arch images, SHA-pinned CI (`-race`, `govulncheck`), and Dependabot coverage.                    |

### terraform

Conventions and workflows for authoring reusable Terraform modules.

| Skill                | What it does                                                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `terraform-style`    | House style for HCL: collection types, resource naming, `name_prefix`, `for_each` toggles, variable/output grouping, null defaults, file layout.  |
| `terraform-module`   | Scaffolds a new module with the canonical layout (`terraform.tf`, `main.tf`, `variables.tf`, `outputs.tf`, `README.md`) from commented templates. |
| `terraform-validate` | The fmt → init/validate → tflint loop, with a bundled provider-agnostic `tflint.hcl`.                                                             |

## Installation

### Claude Code

```text
/plugin marketplace add bitwise-media-group/skills
/plugin install terraform@bitwise
```

### Codex CLI

```sh
codex plugin marketplace add bitwise-media-group/skills
codex plugin add terraform@bitwise
```

### OpenCode and Antigravity

Both read `.agents/skills/` natively. Clone this repo and symlink the skills in:

```sh
./install.sh                  # project scope: ./.agents/skills/ in the current directory
./install.sh --global         # user scope: ~/.agents/skills + ~/.gemini/skills
./install.sh --global --claude  # also link ~/.claude/skills
./install.sh --copy ...       # copy instead of symlink
```

Symlinked installs update on `git pull`. Alternatively,
[`npx skills add bitwise-media-group/skills`](https://github.com/vercel-labs/skills) works as a zero-clone installer;
`install.sh` is the supported path.

## Evals

Each skill ships with evals under `plugins/<plugin>/evals/<skill>/`, run through the
[evolve](https://github.com/bitwise-media-group/evolve) CLI (the `EVOLVE` make variable selects the binary):

- **Tier 0 — static lint** (`make eval-static`): frontmatter, manifests, version sync. Runs in CI on every push.
- **Tier 1 — trigger accuracy** (`make eval-trigger`): does the skill activate for the right prompts and stay quiet for
  near-misses? Real headless `claude -p` sessions.
- **Tier 2 — behavioral** (`make eval-behavior`): does following the skill produce correct artifacts? Graded
  deterministically (`terraform validate`, `tflint`, file/regex checks) with an optional LLM judge for subjective
  assertions.

Tiers 1–2 run per provider model (`MODELS=anthropic|openai|google|all` or specific model ids) and record token usage per
eval via the provider token-counting APIs. Results land in each skill's committed `results.json`; `make report`
(`evolve report`) renders them into [`EVALUATION.md`](EVALUATION.md) + `EVALUATION.json` (plugin-level rollup) and
`plugins/<plugin>/EVALUATION.md` (per-eval detail).

Tiers 1–2 cost tokens and run via the manual `evals` GitHub workflow or locally.

## Contributing

See [AGENTS.md](AGENTS.md) for repository conventions: layout, dual Claude/Codex manifests, frontmatter policy, and the
eval requirements for new skills.

## License

[MIT](LICENSE)
