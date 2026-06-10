# Dependabot for Go repositories — rationale and full reference config

Companion to the `go-release` skill. [templates/dependabot.yaml](templates/dependabot.yaml) is the starting subset for a
fresh Go repo; this reference explains why each knob is set the way it is and shows the full ecosystem matrix to grow
into.

## The shape every entry shares

Every ecosystem entry uses the same three settings:

```yaml
schedule:
    interval: daily
cooldown:
    default-days: 7
groups:
    all-minor-and-patch:
        patterns:
            - "*"
        update-types:
            - minor
            - patch
```

- **Daily checks, 7-day cooldown.** Dependabot looks every day but waits seven days after a release before proposing it.
  Compromised or yanked releases are almost always caught by the ecosystem within days — the cooldown means they never
  reach your repo — and rapid successive releases collapse into one bump instead of a PR per patch.
- **Minor + patch grouped into one PR per ecosystem.** One reviewable PR a week per ecosystem instead of a stream of
  single-package bumps. **Majors are deliberately excluded** from the group: a breaking upgrade arrives as its own PR,
  with its own changelog, reviewed on its own merits.

## The Go-specific entries

A Go repo following the `go-project` layout needs three entries as a baseline:

- **`gomod` at `/`** — the application module. Minor/patch bumps to direct and indirect dependencies arrive grouped; a
  new major of a dependency arrives alone.
- **`gomod` at `/tools`** — the pinned developer CLIs (`addlicense`, `goreleaser`, `syft`) live in their own module, so
  they need their own entry; Dependabot does not descend into nested modules. Give the group a distinct name (`tools`)
  so tool bumps never ride along with application dependency PRs — the same isolation the separate `tools/go.mod` exists
  to provide.
- **`github-actions` at `/`** — the CI and release workflows pin every action to a full commit SHA (see the `go-release`
  skill's CI conventions). Dependabot understands SHA pins with a version comment and updates both together, so pinning
  stays secure _and_ fresh.

## Ecosystems to add as the repo grows them

Add an entry per artifact type the repo actually contains — same schedule/cooldown/group shape:

| Ecosystem        | When                                                               | Covers                       |
| ---------------- | ------------------------------------------------------------------ | ---------------------------- |
| `npm`            | `package.json` pinning prose tooling (prettier, markdownlint-cli2) | the pinned Node CLIs         |
| `docker`         | a `Dockerfile` with versioned base images                          | `FROM` image tags            |
| `docker-compose` | a `docker-compose.yaml` for a local stack                          | `image:` tags in the compose |
| `uv`             | Python notebooks/scripts managed by uv                             | `pyproject.toml` / lockfile  |

Keep each versioned artifact in exactly one Dependabot-visible place. If something else needs the value (for example a
Makefile that runs a compose-managed image), derive it from the managed file rather than repeating the pin — one source
of truth, one update PR.

## Full reference config

The complete `.github/dependabot.yaml` for a Go repo with a tools module, Node prose tooling, and a Docker-based local
stack:

```yaml
version: 2

updates:
    - package-ecosystem: github-actions
      directory: /
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          all-minor-and-patch:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch

    - package-ecosystem: gomod
      directory: /
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          all-minor-and-patch:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch

    # Build/release tools live in their own module (tools/go.mod); group their
    # updates separately so tool bumps never ride along with application PRs.
    - package-ecosystem: gomod
      directory: /tools
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          tools:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch

    - package-ecosystem: npm
      directory: /
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          all-minor-and-patch:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch

    - package-ecosystem: docker
      directory: /
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          all-minor-and-patch:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch

    - package-ecosystem: docker-compose
      directory: /
      schedule:
          interval: daily
      cooldown:
          default-days: 7
      groups:
          all-minor-and-patch:
              patterns:
                  - "*"
              update-types:
                  - minor
                  - patch
```
