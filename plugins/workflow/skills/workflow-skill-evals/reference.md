# Reference — authoring evolve eval suites

Depth behind [SKILL.md](SKILL.md). The **authoritative, current** source is the upstream guide and schemas; this file is
a snapshot for offline work. When they disagree, upstream wins.

- Guide: <https://oss.bitwisemedia.uk/evolve/evaluations/>
- Triggers schema: <https://raw.githubusercontent.com/bitwise-media-group/evolve/main/schemas/triggers.schema.json>
- Evals schema: <https://raw.githubusercontent.com/bitwise-media-group/evolve/main/schemas/evals.schema.json>

## The three tiers

- **Tier 0** — static checks evolve runs itself (license, schema validity, plugin wiring). Nothing to author.
- **Tier 1** — triggers. Does the skill activate on the right prompts? No model grades it; evolve drives the agent with
  each query against a workspace holding _every_ skill and watches which it reaches for.
- **Tier 2** — behavioral evals. Drop the agent into a throwaway workspace with the skill installed, hand it a real
  task, grade what it leaves behind.

## triggers.json fields

| Field            | Required | Meaning                                                                    |
| ---------------- | -------- | -------------------------------------------------------------------------- |
| `query`          | yes      | The prompt sent to the agent, verbatim                                     |
| `should_trigger` | yes      | Whether the skill under test is _expected_ to activate for this query      |
| `skip_providers` | no       | Provider ids to exclude for this one query (e.g. a model that can't judge) |

How a query scores: each run is a hit (the agent invoked the `Skill` tool for it or opened its `SKILL.md`) or a miss. A
query passes when its hit-rate lands on the expected side of 50% — `≥ 0.5` for `should_trigger: true`, `< 0.5` for
`false`. The skill's score is the share of queries that passed. Run an **odd** `--runs` so a query can't tie. Because
the prompts are pinned, two models' scores are directly comparable.

Negatives carry the signal. Two patterns to copy:

- **Cross-list siblings.** For each skill, add its sibling skills' headline positives as negatives — that is exactly
  where false activation happens. If `go-style` fires on "Set up GoReleaser", the `go-release` positive would have
  hidden the bug.
- **Same task, wrong domain.** Take a real positive and swap the language/framework ("Add structured logging to my
  Express app" for a Go skill). Catches a skill keying off the verb instead of the context.

Aim for a balanced set; a 90%-positive suite over-reports accuracy.

## evals.json fields (per case)

| Field             | Required | Meaning                                                                       |
| ----------------- | -------- | ----------------------------------------------------------------------------- |
| `id`              | yes      | Stable identifier; the results key. Lowercase-kebab by convention             |
| `prompt`          | yes      | The task sent to the agent                                                    |
| `assertions`      | one of\* | Deterministic + judge checks (below)                                          |
| `expectations`    | one of\* | Plain-language statements, each graded by the LLM judge **before** assertions |
| `name`            | no       | Human-readable label surfaced in reports                                      |
| `expected_output` | no       | Prose description of success; context for the judge, never graded on its own  |
| `files`           | no       | Input paths staged into the workspace before the run (staging rule below)     |
| `allowed_tools`   | no       | Space-separated tool allowlist (e.g. `Read Write Edit Bash(go *)`)            |
| `max_turns`       | no       | Per-case cap on agent turns; overrides the run default                        |
| `timeout_seconds` | no       | Per-case wall-clock cap; overrides the run default                            |
| `skip_providers`  | no       | Provider ids to skip for this case                                            |

\* A case must declare at least one `expectations` entry **or** one `assertions` entry, or it fails to load.

## Assertion types

Two families: **deterministic** (`file_exists`, `file_absent`, `regex`, `not_regex`, `command`, `tool_call`) and the
**LLM judge** (`llm`). Each assertion is pass / fail / skipped; `expectations` expand to `llm` assertions graded first,
in authored order, then the authored `assertions` in order. Patterns are Go RE2 (no backreferences/lookaround); in JSON
every backslash doubles (`\\.`, `\\s`).

| Type          | Required fields | Optional                         | Passes when…                                                              |
| ------------- | --------------- | -------------------------------- | ------------------------------------------------------------------------- |
| `file_exists` | `path`          | —                                | `path` (workspace-relative) exists after the run                          |
| `file_absent` | `path`          | —                                | `path` does **not** exist                                                 |
| `regex`       | `pattern`       | `path`                           | `pattern` matches `path`'s contents, or the agent's reply when no `path`  |
| `not_regex`   | `pattern`       | `path`                           | `pattern` does **not** match (a missing `path` file **fails**)            |
| `command`     | `run`           | `cwd`, `requires`, `expect_exit` | `run` (via `/bin/sh -c`) exits with `expect_exit` (default `0`)           |
| `tool_call`   | `tool`          | `pattern`                        | the agent invoked a tool whose name matches `tool` (args match `pattern`) |
| `llm`         | `text`          | —                                | the pinned judge (`claude-sonnet-4-6`) verifies `text`                    |

Notes:

- `command` is the strongest check — it runs the real toolchain over the output. `requires` keeps suites portable: the
  check **skips** (not fails) when the binary is absent. Set `expect_exit` when success means non-zero (e.g.
  `grep -rq TODO src/` with `expect_exit: 1` asserts the token is gone).
- `not_regex` with a `path` means "the file exists _and_ does not contain this". To assert a file is gone, use
  `file_absent`.
- `tool_call` is tri-state: skipped if the harness can't report tool calls, failed if it reports calls but none match.
  An MCP tool surfaces as `mcp__<server>__<tool>`. Unlike `regex`, it is not multiline.
- A bare string in `assertions` is shorthand for `{ "type": "llm", "text": <string> }`. Reserve the judge for genuinely
  subjective/holistic checks — each `llm` assertion costs a model call.

## The `files` staging rule

Paths are relative to the eval directory. Exactly one rule decides placement:

- Under **`files/`** → stages at its path relative to `files/`, preserving the tree. `files/internal/cli/root.go` →
  `internal/cli/root.go`.
- **Anything else** → stages by **basename** at the workspace root. `fixtures/clidemo/go.mod` → `go.mod`.

By convention `files/` mirrors the workspace tree (source the agent reads/edits at its real path), and
`fixtures/<name>/` holds a shared scaffold (often a `go.mod`) many cases reference. A fixture dir may hold more files
than a case names — only listed paths stage. Paths can't escape the workspace; a leading `evals/` segment is tolerated
for skill-root-relative paths.

## Worked example — deterministic-first, one judge check

```json
{
    "id": "parametrize",
    "prompt": "Write parametrized tests for parse in src/myapp/kv.py, including error paths, in tests/test_kv.py.",
    "allowed_tools": "Read Write Edit Glob Grep Skill Bash(uv *) Bash(pytest *) Bash(python3 *)",
    "files": ["files/src/myapp/kv.py"],
    "expectations": ["The agent explains which error paths it parametrized and why."],
    "assertions": [
        { "type": "file_exists", "path": "tests/test_kv.py" },
        { "type": "regex", "path": "tests/test_kv.py", "pattern": "pytest\\.mark\\.parametrize" },
        { "type": "not_regex", "path": "tests/test_kv.py", "pattern": "unittest|TestCase" },
        { "type": "command", "run": "python3 -m py_compile tests/test_kv.py", "requires": "python3" }
    ]
}
```

Deterministic checks pin the concrete artifacts; the lone `expectation` covers the part only prose can judge.

## Running and refreshing

```sh
evolve run triggers --runs 5            # Tier 1
evolve run evals --jobs 4               # Tier 2 (baselines run automatically; reports show lift)
```

Resume flags preserve completed entries: `--new` runs only missing/stale results, `--modified` reruns cases whose
authored content changed, `--failed` reruns failures. In this marketplace use `make triggers`, `make evals`, `make all`,
and `make report`; `evolve models` prints the model/pricing matrix. The committed `results.json` is sweep output —
regenerate reports with `make report`, never edit results or EVALUATION files by hand.
