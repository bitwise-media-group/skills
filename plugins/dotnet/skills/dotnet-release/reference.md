# .NET release engineering — rationale and full reference

Companion to the `dotnet-release` skill. The templates are the starting subset for a fresh package repo; this explains
why each knob is set the way it is and shows the configuration to grow into.

## Trusted Publishing: why OIDC, and how to set it up

A stored NuGet API key is a long-lived secret: it sits in repository secrets, never expires unless you rotate it, grants
push rights to anyone who can read the secret or run a workflow, and is the thing that leaks. Trusted Publishing
replaces it with short-lived credentials minted per run from the workflow's OIDC identity — there is no secret to steal,
and the trust is scoped to a specific repository and workflow.

The flow in [templates/release.yaml](templates/release.yaml):

1. The workflow requests an OIDC token (`permissions: id-token: write`).
2. The `NuGet/login` action sends that token to NuGet.org, which verifies it against the trusted-publishing policy and
   returns a short-lived API key as the step output `NUGET_API_KEY`.
3. `dotnet nuget push --api-key ${{ steps.login.outputs.NUGET_API_KEY }}` publishes with that temporary key, which
   expires shortly after.

One-time setup on NuGet.org (under your account → Trusted Publishing): create a policy naming the package owner, the
GitHub repository (`OWNER/REPO`), the workflow file (`release.yaml`), and optionally the environment (`nuget`). Set the
same `user:` on the `NuGet/login` step to that account. Gating the job behind a GitHub `environment` lets you add
required reviewers to the publish step.

## MinVer vs Nerdbank.GitVersioning

Both derive the version from git so the tag and the artifact can never disagree — pick by how much control you need.

- **MinVer (default).** One `PackageReference`, zero config files. The version is the nearest `vX.Y.Z` tag reachable
  from `HEAD`; commits after the tag produce a height-based prerelease (`1.2.3-alpha.0.5`). Releasing is
  `git tag v1.2.3 && git push --tags`. This is the closest analog to the tag-driven model the Go and Python release
  skills use, and the right default for most libraries.
- **Nerdbank.GitVersioning (`nbgv`).** A `version.json` declares the base version; the tool computes a deterministic
  build number from git height and integrates with CI build numbers, assembly versioning, and cloud build providers.
  Reach for it when you need build-height-based versions, a version that is set in a file rather than a tag, or tight
  CI-number integration.

Either way, set `fetch-depth: 0` on checkout so the full tag history is available — a shallow clone has no tags to
compute from.

## Deterministic builds, SourceLink, and symbols

- **`ContinuousIntegrationBuild=true`** (set only in CI, keyed off `$(GITHUB_ACTIONS)` in Directory.Build.props)
  normalizes embedded file paths so two builds of the same commit produce byte-identical output — the foundation for
  reproducible packages and reliable symbol matching.
- **`Deterministic=true`** removes nondeterministic inputs (timestamps, absolute paths) from the assembly.
- **SourceLink** (`Microsoft.SourceLink.GitHub`) embeds, for each source file, the commit-pinned URL it came from, so a
  debugger can fetch the exact source for a stack frame. `EmbedUntrackedSources=true` includes generated files that
  aren't in git.
- **Symbols** ship as a `.snupkg` (`SymbolPackageFormat=snupkg`) pushed alongside the `.nupkg`; NuGet.org's symbol
  server serves them to debuggers.

Verify locally: `dotnet pack -c Release` then inspect the `.nupkg` (it is a zip) for the expected `.nuspec` metadata,
and confirm a matching `.snupkg` is produced.

## Dependabot: the knobs and the ecosystem matrix

Every entry shares the same shape: `schedule.interval: daily`, `cooldown.default-days: 7`, and a `groups` block
collapsing `minor` + `patch` into one PR per ecosystem.

- **Daily checks, 7-day cooldown.** Dependabot looks daily but waits seven days after a release before proposing it —
  compromised or yanked releases are almost always caught within days, so they never reach your repo, and rapid
  successive patches collapse into one bump.
- **Minor + patch grouped, majors alone.** One reviewable PR per ecosystem per week; a breaking major upgrade arrives as
  its own PR with its own changelog, reviewed on its own merits.

| Ecosystem        | When                                                          | Covers                              |
| ---------------- | ------------------------------------------------------------- | ----------------------------------- |
| `nuget`          | always (reads Central Package Management)                     | `Directory.Packages.props` versions |
| `github-actions` | always (the SHA-pinned workflows)                             | action pins in `.github/workflows`  |
| `dotnet-sdk`     | a `global.json` pinning the SDK                               | the SDK band in `global.json`       |
| `docker`         | a `Dockerfile` with versioned base images                     | `FROM` image tags                   |
| `npm`            | `package.json` pinning prose tooling (prettier, markdownlint) | the pinned Node CLIs                |

Add an entry per artifact type the repo actually contains. The `dotnet-sdk` ecosystem is what keeps `global.json`
current — Dependabot proposes SDK band bumps the same way it does package versions.
