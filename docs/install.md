---
description: Install the bitwise skills into Claude Code, Codex CLI, OpenCode, or Google Antigravity.
---

<!-- Content tabs need their fenced blocks indented under each tab, which markdownlint reads as indented code. -->
<!-- markdownlint-disable MD046 -->

# Install

The skills live once under `plugins/<plugin>/skills/` and reach each harness through its native mechanism: the Claude
Code and Codex CLI plugin marketplaces, or symlinks into the `.agents/skills/` directory that OpenCode and Antigravity
read. Pick a plugin from the **Plugins** section of the navigation — the examples below install `terraform`.

## Claude Code

Add the marketplace once, then install any plugin from it:

```text
/plugin marketplace add bitwise-media-group/skills
/plugin install terraform@bitwise
```

`/plugin` with no arguments opens the interactive browser, where you can enable, disable, and update installed plugins.
Plugins that ship slash commands register them on install, namespaced by plugin — `workflow` adds `/workflow:commit` and
`/workflow:security-report` (the bare `/commit` works too when nothing else claims it).

## Codex CLI

```sh
codex plugin marketplace add bitwise-media-group/skills
codex plugin add terraform@bitwise
```

Codex reads the same skills through its own manifests (`.agents/plugins/marketplace.json` and each plugin's
`.codex-plugin/plugin.json`), so versions stay in lockstep with the Claude marketplace.

## OpenCode and Antigravity

Both read `.agents/skills/` natively. Clone the repository and let `install.sh` symlink the skills in:

=== "Project scope"

    ```sh
    git clone https://github.com/bitwise-media-group/skills
    ./skills/install.sh                  # ./.agents/skills/ in the current directory
    ./skills/install.sh --project DIR    # ./.agents/skills/ in DIR
    ```

=== "User scope"

    ```sh
    git clone https://github.com/bitwise-media-group/skills
    ./skills/install.sh --global           # ~/.agents/skills + ~/.gemini/skills
    ./skills/install.sh --global --claude  # also link ~/.claude/skills
    ```

=== "Copy instead of link"

    ```sh
    ./skills/install.sh --copy           # any scope; copies the skill directories
    ./skills/install.sh --global --copy
    ```

Symlinked installs update on `git pull`. Copies don't — rerun `install.sh` after pulling.

!!! tip "Zero-clone alternative"

    [`npx skills add bitwise-media-group/skills`](https://github.com/vercel-labs/skills) installs without a clone, but
    `install.sh` is the supported path.

## What gets installed

Each plugin is a set of skills, and each skill is a directory with a compact `SKILL.md` plus optional companions
(`reference.md`, `templates/`). Skill names are prefixed by plugin (`terraform-style`, not `style`) because Codex,
Antigravity, and OpenCode install skills into flat, shared directories. The harness reads only each skill's `name` and
`description` up front, and loads the rest when a task matches.
