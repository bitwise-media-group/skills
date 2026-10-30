---
description:
    Bootstrap a new repository following the workflow-new-repository skill — the shared mise toolchain, the language
    scaffold for an archetype, and the SHA-pinned reusable GitHub workflow callers.
argument-hint: [archetype: go|node|python|swift|terraform|common] [name]
---

# New repository

Apply the `workflow-new-repository` skill to bootstrap a new repository.

Arguments from the user (archetype, then repo name or directory): $ARGUMENTS

Follow the skill exactly:

- If no archetype is given, ask for one (`go`, `node`, `python`, `swift`, `terraform`, or `common`) before writing
  anything; never infer it from the name.
- Add the toolchain with the `workflow-toolchain` skill and the workflow callers with the `actions-reusable-workflows`
  skill, each at its latest release.
- Verify with `make fmt` and `make lint`, hand the commit off through `commit.sh`, and only list the GitHub-side steps
  (create the remote, apply the repo template, Apps, Pages) — do not perform them without explicit confirmation.
