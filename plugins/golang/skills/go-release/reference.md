# Renovate for Go repositories — rationale and full reference config

Companion to the `go-release` skill. [templates/renovate.json5](templates/renovate.json5) is the starting subset for a
fresh Go repo; this reference explains why each knob is set the way it is and shows the full ecosystem matrix to grow
into.

## The shape every rule shares

Every packageRule uses the same two settings, on top of a global cooldown:

```json5
{
    minimumReleaseAge: "7 days",
    packageRules: [
        {
            matchManagers: ["gomod"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "go dependencies",
        },
    ],
}
```

- **7-day cooldown.** Renovate looks continuously but waits seven days after a release before proposing it
  (`minimumReleaseAge`). Compromised or yanked releases are almost always caught by the ecosystem within days — the
  cooldown means they never reach your repo — and rapid successive releases collapse into one bump instead of a PR per
  patch.
- **Minor + patch grouped into one PR per ecosystem.** One reviewable PR a week per ecosystem instead of a stream of
  single-package bumps. **Majors are deliberately excluded** from the group (the rule's `matchUpdateTypes` only matches
  `minor`/`patch`): a breaking upgrade arrives as its own PR, with its own changelog, reviewed on its own merits.

## The Go-specific rules

A Go repo following the `go-project` layout needs three rules as a baseline:

- **`gomod` matching `go.mod`** — the application module. Minor/patch bumps to direct and indirect dependencies arrive
  grouped; a new major of a dependency arrives alone. Renovate's `gomod` manager already parses the full `require` block
  (direct and indirect) with no extra opt-in — unlike Dependabot, which needs `dependency-type: all` to include indirect
  requires at all.
- **`gomod` matching `tools/go.mod`** — the pinned developer CLIs (`addlicense`, `goreleaser`, `syft`) live in their own
  module. Renovate's default `gomod` file matching already finds nested `go.mod` files with no extra config — Dependabot
  needed a separate `directory: /tools` entry just to descend into it. Give the rule a distinct `groupName` (`go tools`)
  so tool bumps never ride along with application dependency PRs — the same isolation the separate `tools/go.mod` exists
  to provide.
- **`github-actions`** — the CI and release workflows pin every action to a full commit SHA (see the `go-release`
  skill's CI conventions). Renovate understands SHA pins with a version comment and updates both together, so pinning
  stays secure _and_ fresh.

## Ecosystems to add as the repo grows them

Add a rule per manager the repo actually needs — same `matchUpdateTypes`/`groupName` shape (Renovate detects the manager
from the files present; these entries just need adding to `packageRules` once the repo has files of that kind):

| Manager          | When                                                               | Covers                       |
| ---------------- | ------------------------------------------------------------------ | ---------------------------- |
| `npm`            | `package.json` pinning prose tooling (prettier, markdownlint-cli2) | the pinned Node CLIs         |
| `dockerfile`     | a `Dockerfile` with versioned base images                          | `FROM` image tags            |
| `docker-compose` | a `docker-compose.yaml` for a local stack                          | `image:` tags in the compose |
| `pep621`         | Python notebooks/scripts managed by uv                             | `pyproject.toml` / `uv.lock` |

Keep each versioned artifact in exactly one Renovate-visible place. If something else needs the value (for example a
Makefile that runs a compose-managed image), derive it from the managed file rather than repeating the pin — one source
of truth, one update PR.

## Full reference config

The complete `.github/renovate.json5` for a Go repo with a tools module, Node prose tooling, and a Docker-based local
stack:

```json5
{
    $schema: "https://docs.renovatebot.com/renovate-schema.json",
    extends: ["config:recommended"],
    minimumReleaseAge: "7 days",
    packageRules: [
        {
            matchManagers: ["github-actions"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "github-actions",
        },
        {
            matchManagers: ["gomod"],
            matchFileNames: ["go.mod"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "go dependencies",
        },
        // Build/release tools live in their own module (tools/go.mod); group their
        // updates separately so tool bumps never ride along with application PRs.
        {
            matchManagers: ["gomod"],
            matchFileNames: ["tools/go.mod"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "go tools",
        },
        {
            matchManagers: ["npm"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "npm",
        },
        {
            matchManagers: ["dockerfile"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "docker",
        },
        {
            matchManagers: ["docker-compose"],
            matchUpdateTypes: ["minor", "patch"],
            groupName: "docker-compose",
        },
    ],
}
```
