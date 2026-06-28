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

### python

Modern Python on the Astral toolchain (`uv`, `ruff`, `ty`/`pyright`).

| Skill            | What it does                                                                                                                                        |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python-project` | Scaffolds the `src/` layout with `uv`: `pyproject.toml` on the `uv_build` backend, dev tools in a dependency group, and a Makefile `pr` gate.       |
| `python-style`   | House style enforced by `ruff format` + `ruff check`: the opinionated lint select set, `pathlib`, `logging`, and exception idioms.                  |
| `python-typing`  | Type every public API and gate it with `ty` or `pyright`: `[tool.ty]`/`[tool.pyright]` config, `X \| None`, PEP 695 generics, `Protocol` over ABCs. |
| `python-testing` | `pytest` with `@pytest.mark.parametrize`, fixtures, fakes over mocks, and Hypothesis property tests as the fuzzing analogue.                        |
| `python-docs`    | Google-style docstrings enforced via ruff `D` rules, and LLM-ready CLI reference generation for Typer/Click tools.                                  |
| `python-release` | `uv build` + `uv publish` via PyPI Trusted Publishing, SHA-pinned CI (`ruff`/`ty`/`pytest`), tag-driven releases, and Dependabot coverage.          |

### workflow

Developer-workflow commands and skills, layered on the global Conventional-Commits and `commit.sh` conventions.

| Skill                      | What it does                                                                                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workflow-commit`          | Conventional Commit messages with a sandbox-safe `commit.sh` handoff: commit unsigned inside a worktree and re-sign via the script, or generate the `git add`/`git commit` script in the main checkout. |
| `workflow-security-report` | Triage a code-scanning (CodeQL) finding fetched via `gh`: an immutable report and index row with SHA-pinned permalinks, recommending remediation or dismissal.                                          |
| `workflow-skill-evals`     | Generate an evolve evaluation suite for an agent skill: Tier 1 triggers and Tier 2 behavioral evals under `evals/<skill>/`, deterministic-first, tracking the upstream evolve guide and JSON Schemas.   |

The plugin also ships matching Claude Code commands — `/commit` and `/security-report` — as thin entry points to these
skills.

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
[evolve](https://github.com/bitwise-media-group/evolve) CLI (`go tool evolve`, pinned in `tools/go.mod`):

- **Tier 0 — static lint** (run inside `make lint`): frontmatter, manifests, version sync. Runs in CI on every push.
- **Tier 1 — trigger accuracy** (`make triggers`): does the skill activate for the right prompts and stay quiet for
  near-misses? Real headless `claude -p` sessions.
- **Tier 2 — behavioral** (`make evals`): does following the skill produce correct artifacts? Graded deterministically
  (`terraform validate`, `tflint`, file/regex checks) with an optional LLM judge for subjective assertions.

Tiers 1–2 run per provider model (evolve's `--models anthropic|openai|google|all`, or specific model ids; default from
`.evolve.json`) and record token usage per eval via the provider token-counting APIs. Results land in each skill's
committed `results.json`; `make report` (`evolve report`) renders them into [`EVALUATION.md`](EVALUATION.md) +
`EVALUATION.json` (plugin-level rollup) and `plugins/<plugin>/EVALUATION.md` (per-eval detail).

Tiers 1–2 cost tokens and run via the manual `evals` GitHub workflow or locally.

## Contributing

See [AGENTS.md](AGENTS.md) for repository conventions: layout, dual Claude/Codex manifests, frontmatter policy, and the
eval requirements for new skills.

## License

[MIT](LICENSE)
