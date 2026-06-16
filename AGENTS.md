# bitwise skills — repository conventions

This repo is the **bitwise** skills/plugin marketplace: agent skills packaged as plugins, consumable by Claude Code,
OpenAI Codex CLI, Google Antigravity, and OpenCode. The global `~/.claude/CLAUDE.md` (Conventional Commits, `commit.sh`
signing handoff) applies on top of this file.

> `CLAUDE.md` is a symlink to this file — always edit `AGENTS.md`, never `CLAUDE.md`.

## Layout

- One plugin per directory under `plugins/<plugin>/`. Skills are the canonical source of truth at
  `plugins/<plugin>/skills/<skill-name>/SKILL.md` — they exist exactly once; every distribution channel (Claude/Codex
  marketplaces, `install.sh` symlinks) points at this tree.
- Evals live at `plugins/<plugin>/evals/<skill-name>/` (`triggers.json`, `evals.json`, fixtures, and the committed
  `results.json` the sweeps write), **not** inside the skill directory, so installed skills stay lean.
- Skill directory name must equal the frontmatter `name`.
- Skill names are globally namespaced by prefix (e.g. `terraform-style`, not `style`) because Codex/Antigravity/OpenCode
  install skills into flat shared directories.

## Dual manifests (Claude + Codex)

Every plugin carries two manifests; the repo carries two marketplace manifests:

| Consumer    | Marketplace (repo root)            | Plugin manifest                          |
| ----------- | ---------------------------------- | ---------------------------------------- |
| Claude Code | `.claude-plugin/marketplace.json`  | `plugins/<n>/.claude-plugin/plugin.json` |
| Codex CLI   | `.agents/plugins/marketplace.json` | `plugins/<n>/.codex-plugin/plugin.json`  |

Rules:

- **Versions stay in sync** between the two plugin manifests (enforced by `evolve run checks`). Codex requires strict
  semver.
- Marketplace `source` paths are explicit and `./`-prefixed (`"./plugins/terraform"`). Do not use Claude's
  `metadata.pluginRoot` — Codex fallback-reads Claude's manifest and resolves sources against the repo root.
- **Never add a `hooks/` directory to a plugin.** Codex default-discovers `hooks/hooks.json` with an incompatible
  schema.

## Skill frontmatter policy

Portable fields only — these skills must work on all four tools, and only `name`/`description` are read everywhere:

- `name`: `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars, equals the directory name.
- `description`: third person, ≤ 1024 chars, with explicit trigger phrases ("Use when …"). The description is the only
  signal harnesses use to decide activation — write it for recall.
- `license`: `MIT`.

No Claude-specific fields (`allowed-tools`, `model`, `context`, `hooks`, …) unless a skill genuinely needs them, and
then only with a comment in the PR explaining the cross-tool impact.

## Progressive disclosure

Keep `SKILL.md` compact (well under 500 lines; Codex truncates bodies around 8 KB). Put depth — rationale, extended
examples, edge cases — in companion files (`reference.md`, `templates/`) linked from the body by relative path.
Cross-reference sibling skills by **name** ("see the `terraform-style` skill"), never by path: installed layouts differ
per tool.

## Evals

Evals run through the [evolve](https://github.com/bitwise-media-group/evolve) CLI (`.evolve.json` holds the repo config;
the `EVOLVE` make variable points at a sibling checkout's binary for now):

- Every new skill ships with `evals/<skill>/triggers.json` (10–20 `{query, should_trigger}` entries inside the
  `{"skill_name", "triggers"}` envelope; negatives must be near-misses) and `evals.json` (2–5 behavioral evals with
  assertions, `{"skill_name", "evals"}` envelope). Schemas live in evolve's `schemas/` directory.
- Eval `files` are fixture paths, never inline content. A path under `files/` stages into the workspace at its path
  relative to `files/`; anything else stages by basename (e.g. `fixtures/<name>/go.mod` for per-eval `go.mod` files that
  would collide under `files/`).
- Changing a skill `description` ⇒ rerun Tier 1: `make eval-trigger`.
- Prefer deterministic assertions (`terraform validate`, `tflint`, file/regex checks) over LLM-judged ones.
- Results and token cost are committed: `evals/<skill>/results.json` (raw, rewritten per-model by the sweeps),
  `EVALUATION.md` + `EVALUATION.json` (root rollup), and `plugins/<plugin>/EVALUATION.md` (per-eval detail).
  `evolve report` (`make report`) regenerates the reports from the stored results — never edit them by hand. Token usage
  comes from each provider's token-counting API; `evolve models` prints the model/pricing matrix.

## Validation

Run before committing:

```sh
make fmt                          # prettier, pinned via package.json (SKILL.md is prettier-ignored)
make license                      # SPDX license headers via addlicense, pinned in tools/go.mod
make eval-static                  # Tier 0: frontmatter, manifests, version sync
claude plugin validate .          # Claude marketplace/plugin schema
make lint                         # markdown style (120-col, config in .markdownlint-cli2.yaml)
```

Node CLIs run from `node_modules/.bin` (locked by `package-lock.json` — no npx, no globals); Go developer CLIs are
pinned in `tools/go.mod` and run via `go tool` (resolved through the root `go.work`). The Makefile also wraps Tiers 1–2
(`make eval-trigger`, `make eval-behavior`, `make eval` for all tiers plus reports; pass `SKILL=`, `MODELS=`, `RUNS=`,
`JOBS=`) and `make report` for the EVALUATION files — all through the `evolve` binary selected by `EVOLVE=` (default
`../evolve/evolve`, a pinned go-tool later).

## Markdown style

Lint-clean per `.markdownlint-cli2.yaml`: blank lines around headings/lists/fences, a language on every code fence, ≤
120-col lines (tables exempt).
