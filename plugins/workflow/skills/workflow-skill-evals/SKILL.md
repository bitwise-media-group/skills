---
name: workflow-skill-evals
description: Write the evolve evaluation suite for an agent skill: its triggers (triggers.json — Tier 1 activation tests) and behavioral evals (evals.json — Tier 2 task tests), under evals/<skill>/. Use when asked to generate, write, author, scaffold, or balance an eval suite, evals, or triggers for a skill; to create or edit a triggers.json or evals.json; to add behavioral evals to a SKILL.md; to add or rebalance positive and near-miss negative trigger cases; or to measure or evaluate whether a skill activates and fires on the right prompts and does its job. Follows the evolve evaluations guide and the JSON Schemas it links, fetched at author time so it tracks new assertion types and fields. Prefers deterministic assertions (file_exists, regex, command, tool_call) over the LLM judge. Not for running or sweeping existing suites, writing application unit tests, or comparing model quality.
license: MIT
---

# Generate an evolve evaluation suite for a skill

Turn a skill's `SKILL.md` into the two graded artifacts evolve runs against it:

- **`triggers.json`** (Tier 1) — does the skill activate on the prompts that should reach for it, and stay
  quiet on the ones that shouldn't?
- **`evals.json`** (Tier 2) — when it does fire, does it do the job? Real tasks in throwaway workspaces,
  graded by deterministic checks and, where only prose can judge, an LLM judge.

Both live **beside** the skill, never inside it: `evals/<skill>/`, a sibling of `skills/<skill>/`.

## 0. Read the upstream guide first — this skill is meant to evolve

evolve gains assertion types, eval fields, and CLI features over time. The authoritative, current source
is upstream, not this file. **Before authoring, fetch and skim:**

- Guide: <https://oss.bitwisemedia.uk/evolve/evaluations/> (sub-pages: `/triggers/`, `/evals/`,
  `/assertions/`, `/execution/`, `/results/`).
- Triggers schema: <https://raw.githubusercontent.com/bitwise-media-group/evolve/main/schemas/triggers.schema.json>
- Evals schema: <https://raw.githubusercontent.com/bitwise-media-group/evolve/main/schemas/evals.schema.json>

If the guide or a schema lists a field, assertion `type`, or tier this file doesn't mention, **the upstream
source wins** — use it. To discover new CLI surface in a repo that vendors evolve, run `evolve --help`,
`evolve run --help`, and `evolve docs` (here: `go tool evolve …`). See [reference.md](reference.md) for the
current assertion table, the staging rule, and worked examples, but treat upstream as the tiebreaker.

## 1. Locate the skill and its eval directory

Read the target `SKILL.md` end to end — the frontmatter `name` and `description` drive the triggers; the
body drives the behavioral evals. Then create `evals/<name>/` where `<name>` equals the skill's `name`
(and its directory). In this marketplace evals are `plugins/<plugin>/evals/<skill>/`; elsewhere mirror
whatever layout the repo's evolve config (`.evolve.json`) declares.

## 2. Author `triggers.json` (Tier 1) — start here, it's the cheapest signal

Envelope: a `triggers` array of `{ "query", "should_trigger" }`; `skill_name` echoes the directory.
Write **10–20** entries, roughly balanced:

- **Positives** — the real phrasings a user types when they want this skill. Vary the shape: an imperative,
  a question, a review-style ask. Each should name the task and domain concretely.
- **Negatives are where the signal lives.** A positives-only suite scores 100% and tells you nothing. Weight
  negatives toward **near-misses**: (a) **sibling skills' headline positives** — the adjacent skill in the
  same plugin is where false activations actually happen; (b) **same task, wrong domain** — a real positive
  with the language or framework swapped, which catches a skill keying off the verb instead of the context.

```json
{
  "$schema": "https://raw.githubusercontent.com/bitwise-media-group/evolve/main/schemas/triggers.schema.json",
  "skill_name": "go-style",
  "triggers": [
    { "query": "Refactor this Go code to wrap errors properly", "should_trigger": true },
    { "query": "Convert these log.Printf calls to slog", "should_trigger": true },
    { "query": "Write table-driven tests for this Go function", "should_trigger": false },
    { "query": "Refactor this Rust code to use idiomatic error handling", "should_trigger": false }
  ]
}
```

Start from [templates/triggers.json](templates/triggers.json). If you changed the skill's `description`,
the trigger surface moved — re-run Tier 1.

## 3. Author `evals.json` (Tier 2) — prove it does the job

Envelope: an `evals` array. Each case needs an `id` (lowercase-kebab; it is the results key), a `prompt`
(the real task), and **at least one** `assertions` entry **or** one `expectations` entry. Write **2–5**
cases covering the skill's headline behaviors and its important refusals/guards.

**Prefer deterministic assertions over the LLM judge** — they are cheap, fast, and reproducible. Reach for
the judge only for holistic claims a rule can't express. The current types:

- `file_exists` / `file_absent` — the agent created (or correctly did not create) `path`.
- `regex` / `not_regex` — `pattern` (Go RE2, multiline) matches a workspace file (`path`) or, with no
  `path`, the agent's final response. A missing `path` file **fails** either check.
- `command` — run `run` via `/bin/sh -c`; passes when the exit code equals `expect_exit` (default `0`).
  Set `requires` to a binary so the check **skips** (not fails) where it's absent; `cwd` runs in a subdir.
  This is the strongest check — it runs the real toolchain over the output.
- `tool_call` — the agent actually invoked a tool matching `tool` (regex), optionally with args matching
  `pattern`. Inspects behavior, not just artifacts.
- `llm` (or a bare string in `assertions`) — a pinned judge verifies `text`. `expectations` is a top-level
  array of such statements, graded first.

Scope `allowed_tools` per case (e.g. `Read Write Edit Glob Grep Skill Bash(go *)`) so a pass reflects the
skill, not the model improvising. Stage inputs with `files` (see §4). Start from
[templates/evals.json](templates/evals.json); the full table and examples are in [reference.md](reference.md).

```json
{
  "id": "project-scaffold",
  "prompt": "Scaffold a new Go service called orderd with our canonical cmd / tools-module / Makefile layout.",
  "allowed_tools": "Read Write Edit Glob Grep Skill Bash(go *) Bash(gofmt *) Bash(mkdir *)",
  "assertions": [
    { "type": "file_exists", "path": "cmd/orderd/main.go" },
    { "type": "regex", "path": "Makefile", "pattern": "^pr:" },
    { "type": "command", "run": "go vet ./...", "requires": "go" }
  ]
}
```

## 4. Stage fixtures with `files`

`files` lists input paths **relative to the eval directory**, staged into the workspace before the run.
One rule decides where each lands:

- A path under **`files/`** stages at its path _relative to `files/`_, preserving the tree
  (`files/internal/cli/root.go` → `internal/cli/root.go`). Use this whenever the **path matters** —
  subdirectories, multi-file layouts, or basenames that would otherwise collide (two `go.mod`s).
- **Any other path** stages by **basename** at the workspace root
  (`fixtures/clidemo/go.mod` → `go.mod`). Use `fixtures/<name>/` for a shared scaffold many cases reference.
  A fixture dir may hold more files than a case names; only listed paths are staged.

Author fixtures as the smallest compiling/valid context the assertions need — a real `go.mod` that
`require`s the right deps lets a `command` assertion lean on the toolchain.

## 5. Validate and run

Add the `$schema` key to both files (above) for editor validation. Then:

```sh
evolve run triggers --runs 5        # Tier 1; odd runs avoid 50/50 ties
evolve run evals --jobs 4           # Tier 2; baselines run automatically
```

In this repo those are `make triggers` and `make evals` (`make all` for both tiers plus reports), and
`make fmt && make lint` gates the eval JSON, schema, and markdown before committing. The committed
`results.json` is written by the sweeps — never hand-edit it. A brand-new suite simply has none until its
first run.
