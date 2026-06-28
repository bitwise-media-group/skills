# workflow-commit reference

Worked `commit.sh` examples and notes. The `SKILL.md` body is the contract; this file shows the two scripts in full and
explains the choices.

## Why a commit.sh handoff at all

Commit signing needs hardware or agents the sandbox cannot reach — a YubiKey over USB/HID, a GPG agent, an SSH agent, or
the OS keychain holding a PIN. A `git commit -S` from inside the sandbox therefore fails, and an unsigned commit on a
protected branch is usually rejected downstream. The fix is to do the mechanical work in the sandbox but let the
**user** produce the signed commit by running a small script outside it. The script is the current batch of work,
regenerated each session.

## Main checkout — generate the commits

In the main checkout you never run `git commit`. You write the exact invocations instead, so the user gets byte-for-byte
the commits you intended, signed:

```sh
#!/usr/bin/env sh
set -eu

git add plugins/workflow/skills/workflow-commit
git commit -m "feat(workflow): add the workflow-commit skill"

git add plugins/workflow/skills/workflow-security-report
git commit -m "feat(workflow): add the security-report triage skill"

rm -- "$0"
```

One `git commit` per logical commit. Stage precisely (name paths; avoid `git add -A` unless you mean it). Put multi-line
bodies and trailers in additional `-m` flags.

## Worktree — commit now, re-sign on handoff

In a linked worktree you commit normally — those commits land unsigned on the `agent/<name>` branch — and the script's
job is only to re-sign the range you authored:

```sh
#!/usr/bin/env sh
set -eu

# Re-sign every commit authored this session. <base> is the parent of the first
# commit on this branch; swap the --exec command for the repo's signing setup.
base="$(git merge-base HEAD main)"
git rebase --exec 'git commit --amend --no-edit --no-verify -S' "$base"

rm -- "$0"
```

## Choosing `<base>`

`<base>` is the commit just before the first one you created this session:

- a fixed count — `HEAD~3` for three commits;
- a dynamic count — `$(git merge-base HEAD <parent-branch>)` re-signs everything this branch added on top of its parent
  (usually `main`).

## Customizing the signing step

`git commit --amend ... -S` signs with git's configured identity (`user.signingKey`, `gpg.format`, `commit.gpgSign`). If
the repository signs through a custom helper instead, replace the `--exec` command with that helper over the same range
— the contract is unchanged: the script re-signs `<base>..HEAD` and then deletes itself.

## The contract, restated

- `#!/usr/bin/env sh` + `set -eu` at the top.
- Overwrite any existing `commit.sh`; it is never appended to.
- `chmod +x commit.sh` when you write it.
- End with `rm -- "$0"` so a clean run removes the script and a failed run (under `set -eu`) leaves it in place to fix
  and rerun.
- Do not touch the repository `.gitignore`.
