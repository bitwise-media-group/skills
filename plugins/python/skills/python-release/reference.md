# Python release engineering — rationale and full reference config

Companion to the `python-release` skill. Why publishing and Dependabot are set up the way they are, and the full
ecosystem matrix to grow into.

## Why Trusted Publishing instead of a token

PyPI Trusted Publishing exchanges a short-lived GitHub OIDC token for an upload credential scoped to one project, minted
per run and expiring in minutes. There is no long-lived API token to store in repository secrets, leak in a log, or
rotate. The workflow needs `permissions: id-token: write` (to mint the OIDC token) and nothing else;
`uv publish --trusted-publishing always` performs the exchange.

Configure the publisher once on PyPI (project → Settings → Publishing) with the repository, the workflow filename
(`release.yaml`), and an environment name. Pin the same `environment:` in the job so only that environment — which you
can protect with required reviewers — can publish. For the very first release, use PyPI's **pending publisher** flow to
register the project name before it exists.

## Why static versioning here

The `uv_build` backend takes the version from `[project] version` in `pyproject.toml`. The release ritual is: bump that
field, commit, tag `vX.Y.Z` **matching it**, push. The tag and the artifact version are then guaranteed identical
because both come from the same committed line. Expose it at runtime from the installed metadata rather than
re-declaring it:

```python
from importlib.metadata import version

__version__ = version("myapp")
```

If you would rather derive the version from the git tag (no manual bump), switch the build backend to `hatchling` +
`hatch-vcs` and set `[project] dynamic = ["version"]` — more moving parts, in exchange for the tag being the single
source of truth. The static approach is the simpler default.

## The Dependabot shape

Every ecosystem entry uses the same three settings — daily checks, a 7-day cooldown, and minor + patch grouped into one
PR:

- **Daily checks, 7-day cooldown.** Dependabot looks daily but waits a week after a release before proposing it.
  Compromised or yanked releases are almost always caught within days, so the cooldown keeps them out of your repo, and
  a flurry of patch releases collapses into one bump.
- **Minor + patch grouped per ecosystem.** One reviewable PR a week per ecosystem instead of a stream of single-package
  bumps. **Majors are deliberately excluded** from the group so a breaking upgrade arrives as its own PR with its own
  changelog.

The two baseline entries:

- **`uv` at `/`** — reads `pyproject.toml` and `uv.lock`, covering both runtime dependencies and the
  `[dependency-groups] dev` tools (ruff, ty, pytest). One entry keeps the whole resolution fresh.
- **`github-actions` at `/`** — the CI and release workflows pin every action to a full commit SHA (see the skill's CI
  conventions). Dependabot understands SHA pins with a version comment and bumps the SHA and comment together, so
  pinning stays secure _and_ fresh.

## Ecosystems to add as the repo grows

Same schedule/cooldown/group shape, one entry per artifact type the repo actually contains:

| Ecosystem        | When                                      | Covers                       |
| ---------------- | ----------------------------------------- | ---------------------------- |
| `docker`         | a `Dockerfile` with versioned base images | `FROM` image tags            |
| `docker-compose` | a `docker-compose.yaml` for a local stack | `image:` tags in the compose |
| `npm`            | `package.json` pinning JS/prose tooling   | the pinned Node CLIs         |

Keep each versioned artifact in exactly one Dependabot-visible place — one source of truth, one update PR.
