# Workflow style — rationale and extended examples

Background for the rules in [SKILL.md](SKILL.md). Read this when a rule is surprising or a reviewer pushes back. Section
numbers mirror the skill.

## 1. Why `.yaml` and one workflow per file

GitHub accepts both `.yml` and `.yaml`; the org standardises on `.yaml` so callers, examples, and `workflow_run`
`workflows:` lists all reference the same spelling. One workflow per file keeps the trigger surface and the permission
ceiling auditable: a reviewer can read a single file and know exactly when it runs and what it can do.

## 2. Why narrow triggers

An unfiltered `pull_request` or `push` runs on every branch and every path, wasting minutes and widening the attack
surface. Branch and path filters make the trigger intent explicit and stop documentation-only PRs from spending CI. The
thin-caller pattern — a per-repo workflow that owns the `on:` block and delegates the work to a reusable workflow — is
covered by the `actions-reusable-workflows` skill.

## 3. Truthy and falsey, precisely

GitHub Actions evaluates an `if:` (and every `${{ }}`) as an expression and coerces the result to a boolean using
JavaScript-like rules. The full set of **falsey** values is:

| Value          | Falsey? | Note                                |
| -------------- | ------- | ----------------------------------- |
| `false`        | yes     | the boolean                         |
| `0`, `-0`      | yes     | numeric zero                        |
| `''`           | yes     | empty string                        |
| `null`         | yes     | also an unset/missing context value |
| `'false'`      | **no**  | a non-empty string is truthy        |
| `'0'`          | **no**  | likewise — a non-empty string       |
| `' '`          | **no**  | a space is non-empty                |
| any other text | no      | truthy                              |

Two consequences shape the rules:

- **Boolean inputs.** `workflow_call` / `workflow_dispatch` inputs declared `type: boolean` arrive as real booleans.
  `if: ${{ inputs.e2e }}` is correct and reads cleanly; `inputs.e2e == 'true'` is redundant noise that also breaks the
  moment someone passes the boolean through a context that stringifies it.
- **String values.** `vars.*`, `env.*`, and `github.event.inputs.*` (a manually dispatched input that is _not_
  `type: boolean`) are strings. The string `'false'` is non-empty, so `if: ${{ vars.DEPLOY }}` is **true even when the
  value is "false"** — a classic foot-gun. Compare explicitly: `if: ${{ vars.DEPLOY == 'true' }}`.

The reusable workflows in `bitwise-media-group/github-workflows` gate their opt-in jobs with `if: ${{ inputs.e2e }}`
precisely because `e2e` is declared `type: boolean`.

See GitHub's
[Evaluate expressions in workflows and actions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions)
for the canonical coercion table.

## 4. Concurrency groups

`cancel-in-progress: true` keyed on `${{ github.workflow }}-${{ github.ref }}` keeps only the newest run for a branch/PR
alive — older runs are obsolete the moment a new commit lands. Ref-moving work (release tagging, fast-forward merges) is
the opposite: cancelling mid-flight can leave a tag half-moved, so those workflows use a fixed group (e.g. `release`)
with `cancel-in-progress: false`, and serialise rather than cancel.

## 5. Dynamic matrices

A static matrix is clearest when the legs are known. When they depend on changed files or repo contents, emit a JSON
array from a prep job (`echo "targets=[\"a\",\"b\"]" >> "$GITHUB_OUTPUT"`) and expand it with
`fromJSON(needs.prep.outputs.targets)`. This keeps the fan-out in one place instead of duplicating jobs.

## 6. Job outputs over re-derivation

Re-computing a value (a version, a detected language, a changed-files list) in several jobs invites drift. Compute once,
publish via `outputs`, and consume with `needs.<job>.outputs.<name>`. Pinning `runs-on` to a concrete image avoids
silent behaviour changes when GitHub rolls `ubuntu-latest`.

## 8. Reusable vs composite, and the permission ceiling

A **reusable workflow** (`workflow_call`) is a whole workflow — multiple jobs, each with its own `runs-on` and
`permissions` — invoked with `uses:` at the job level. A **composite action** packages a sequence of steps that run
inside a caller's job. Reach for a reusable workflow when you need jobs, matrices, or per-job permissions; reach for a
composite action to factor repeated steps.

A reusable workflow's jobs can never exceed the permissions the **calling** job was granted — the caller's
`permissions:` block is a hard ceiling. So the reusable workflow declares `permissions: {}` at the top and grants each
job the minimum it needs, and the caller grants only that ceiling. Passing `secrets: inherit` hands the reusable
workflow every secret in the repo; enumerate the secrets it actually needs instead. Both points are expanded in the
`actions-security` skill.
