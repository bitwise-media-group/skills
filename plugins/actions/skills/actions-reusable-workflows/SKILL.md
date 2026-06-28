---
name: actions-reusable-workflows
description: Wire a repository to the bitwise-media-group/github-workflows reusable workflows — thin caller workflows for CI, CodeQL, release (release-please/GoReleaser), and the signature-preserving fast-forward /merge, merge-notice, and Dependabot auto-merge flows — plus the Makefile consumer contract, @v2 pinning, and FF Merge org setup. Use when setting up CI, CodeQL, releases, or auto-merge for a repo, adding a caller that uses the shared/reusable workflows, scaffolding a repo's .github/ with the org's standard automation, or asked which reusable workflow to call and what to grant it.
license: MIT
---

# Wire the bitwise reusable workflows

The org centralises CI, CodeQL, release, and the fast-forward `/merge` automation in the
`bitwise-media-group/github-workflows` library. A consuming repo keeps a **thin caller** in
`.github/workflows/` that owns its triggers and grants a permission ceiling, then delegates the work
to a reusable workflow with `uses:`. Copy a caller from this skill's [templates/](templates/)
directory and pin it.

Author bespoke workflows with the `actions-style` skill, harden them with `actions-security`, and
run `actions-validate` before committing.

## 1. The caller pattern

The caller declares `on:`, sets the `permissions:` ceiling the reusable workflow's jobs need (a
reusable workflow can never exceed the caller's grant), and calls one workflow per job:

```yaml
name: Continuous integration
on:
  push:
    branches: [main]
  pull_request:
    branches: ["main", "releases/*"]
permissions:
  contents: read
jobs:
  ci:
    uses: bitwise-media-group/github-workflows/.github/workflows/ci.yaml@v2
```

A caller may add product-specific jobs (an `integration` job, say) alongside the reusable-workflow
job. None of these workflows use `pull_request_target` to run PR code.

## 2. Catalog

Each workflow has a ready-to-copy template; grant exactly the listed ceiling and nothing more. None
of these run PR code or use `pull_request_target` unsafely.

- **`ci.yaml`** ([template](templates/ci.yaml)) — canonical Makefile gates (lint/build/test) plus
  Codecov upload. Caller grants `contents: read`. Inputs: `e2e` (default `false`), `go-version-file`,
  `node-version-file`, `cache-dependency-path`. No secrets.
- **`codeql.yaml`** ([template](templates/codeql.yaml)) — CodeQL over `actions` + `go` +
  `javascript-typescript`, by detection. Caller grants `security-events: write`, `packages: read`,
  `actions: read`, `contents: read`. Inputs: `go-version-file`, `config-file` (pass
  `./.github/codeql/codeql-config.yaml`, [template](templates/codeql-config.yaml), to exclude a
  bundled `dist/`). No secrets.
- **`release.yaml`** ([template](templates/release.yaml)) — release-please → GoReleaser (when a
  `.goreleaser.yaml` exists) or a `dist/` rebuild + verify. Caller grants
  `contents`/`issues`/`pull-requests: write`, plus `id-token`/`attestations`/`artifact-metadata: write`
  for the GoReleaser path only. Inputs: `vanity-tags` (default `false`; set it for Actions/reusable
  repos pinned `@v1`). Optional secret `homebrew-tap-token`.
- **`merge.yaml`** ([template](templates/merge.yaml)) — signature-preserving fast-forward `/merge`
  plus set-and-forget auto-merge. Caller grants `permissions: {}` (the App token does the privileged
  work). Inputs: `app-client-id` (required), `require-approval`/`maintainer-only` (default `true`),
  `label`, `merge-command`, `arm-command`. Required secret `app-private-key`.
- **`merge-notice.yaml`** ([template](templates/merge-notice.yaml)) — posts a one-time "this repo
  merges via `/merge`" comment on new PRs. Caller grants `pull-requests: write`. Input: `pr-number`
  (required). No secrets.
- **`dependabot-merge.yaml`** ([template](templates/dependabot-merge.yaml)) — auto-approves
  Dependabot minor/patch PRs and fast-forwards them once CI is green. Caller grants `permissions: {}`.
  Inputs: `app-client-id` (required), `update-types`. Required secret `app-private-key`.

The merge flows also need a [`dependabot.yaml`](templates/dependabot.yaml) and the org setup in §5.

## 3. The consumer contract

The reusable workflows stay config-free by assuming a small contract — the **Makefile is the
language boundary**, and toolchains are set up from marker files at the repo root:

- **Makefile targets** `lint`, `build`, `test` (emitting `coverage/cobertura-coverage.xml`), and
  `e2e`. Stub any that don't apply as a no-op so `make <target>` always succeeds:

  ```makefile
  build: ## no-op: nothing to build
  	@:
  ```

- **Toolchain detection** — a root `go.mod` selects Go (`setup-go`); a `package.json` selects Node
  (`setup-node` + `npm ci`). A tools-only `go.work` + `tools/go.mod` is dev tooling, not a Go
  product, so it does **not** trigger the Go path.
- **Release** — `release-please-config.json` + `.release-please-manifest.json`; an optional
  `.goreleaser.yaml` (`release-type: go`, `draft: true`) selects the GoReleaser path, otherwise the
  publish path rebuilds via `make build` and verifies a committed `dist/`.

## 4. Pinning

The templates pin `@v2`, the floating major tag that moves to each release in the v2.x line (the
matching minor tag `@v2.1` moves too). Pin to a release tag (`@v2.1.0`) or a full commit SHA for
stricter supply-chain guarantees; Dependabot's `github-actions` ecosystem can bump either. Avoid
`@main` except for short-lived testing against a feature branch.

## 5. Fast-forward merge: org setup

`merge.yaml`, `dependabot-merge.yaml`, and `merge-notice.yaml` drive the
`bitwise-media-group/ff-merge` action via a short-lived GitHub App token (so commit signatures
survive). The one-time, org-wide setup — the "FF Merge" App, its ruleset bypass, the
`FF_MERGE_CLIENT_ID` variable, and the `FF_MERGE_PRIVATE_KEY` secret — is documented in
[`bitwise-media-group/ff-merge`](https://github.com/bitwise-media-group/ff-merge). The contract is
input `app-client-id` (from `vars.FF_MERGE_CLIENT_ID`) + secret `app-private-key` (from
`secrets.FF_MERGE_PRIVATE_KEY`); align older callers using `client-id`/`app-key` to these names. The
merge flows also require branch protection that requires PR review.
