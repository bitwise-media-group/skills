---
description:
    Commit the current changes following the workflow-commit skill — Conventional Commit messages with a worktree-aware
    commit.sh signing handoff.
argument-hint: [optional scope or message hint]
---

# Commit changes

Apply the `workflow-commit` skill to commit the current working-tree changes.

Optional hint from the user (scope, message, or which files to include): $ARGUMENTS

Follow the skill exactly:

- Review `git status` and `git diff`, then group the changes into one or more Conventional Commits.
- Inside a git worktree: commit normally (these land unsigned) and write a `commit.sh` that re-signs the range you
  authored this session.
- In the main checkout: do not run `git commit` — write a `commit.sh` at the repo root containing the exact `git add` /
  `git commit` invocations for the user to run outside the sandbox.
