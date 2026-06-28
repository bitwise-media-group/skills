---
name: python-project
description: Scaffold and modernize a Python project with uv. Sets up the src/ layout; a pyproject.toml on uv's native uv_build backend; runtime deps plus a dev dependency group (PEP 735) pinning developer tooling like ruff, ty (or pyright), and pytest; a committed uv.lock and pinned interpreter; a thin __main__ entry point; and a Makefile whose pr target runs the full local gate. Use when: creating a new Python project, package, library, or CLI with uv; creating or configuring a pyproject.toml; choosing a build backend (uv_build) or dependency layout; restructuring an existing repo to the src/ layout; migrating from pip/requirements.txt, poetry, or pipenv onto uv; setting up a dev dependency group or pinning Python dev tools (ruff, ty or pyright, pytest); or adding Makefile targets (pr, fmt, lint, typecheck, test, build) to a Python codebase. Not for writing functions, type hints, tests, or publishing to PyPI — those are separate Python skills.
license: MIT
---

# Scaffold a Python project

Creates a Python repository with the src/ layout, uv-managed dependencies, pinned developer
tooling, and a Makefile gate. Apply the `python-style`, `python-typing`, and `python-testing`
skills while filling in real code, and wire releases with the `python-release` skill.

## 1. Initialize with uv

`uv` is the only tool for interpreters, virtual environments, dependencies, locking, building, and
publishing — do not reach for pip, pipenv, poetry, conda, pyenv, or pipx alongside it.

```sh
uv init --package myapp   # packaged app with a CLI entry point and [build-system]
uv init --lib myapp       # importable library (same src/ layout, no console script)
```

Both flavors produce the src/ layout and a `[build-system]`; the bare `uv init` (flat, no build
system) is only for throwaway scripts. uv writes `pyproject.toml` and `src/myapp/`, and the first
`uv sync`/`uv run` writes the `uv.lock` you commit.

## 2. Lay out the tree

```text
pyproject.toml
uv.lock              # committed — the reproducible, cross-platform resolution
.python-version      # pins the interpreter uv provisions for `uv run`
README.md            # referenced by `readme` in pyproject.toml
src/myapp/__init__.py
src/myapp/__main__.py
tests/
Makefile
```

- **src/ layout, never flat.** Tests run against the installed package, so a missing
  `__init__.py` or a packaging mistake fails locally instead of being masked by an
  import-from-cwd. Copy [templates/python-version](templates/python-version) to `.python-version`.
- One module per concern, named for what it provides (`store`, `client`, `config`) — never
  `utils`, `common`, or `helpers`.

## 3. Configure pyproject.toml on the uv_build backend

Copy [templates/pyproject.toml](templates/pyproject.toml). The choices that matter:

- **`[build-system]` uses uv's native backend** — `requires = ["uv_build>=0.11.21,<0.12"]`,
  `build-backend = "uv_build"`. It is fast and needs no configuration for the src/ layout; the
  upper bound keeps builds reproducible as the backend evolves.
- **`requires-python` is the floor** (`>=3.13`); `.python-version` pins the interpreter used
  during development. Runtime dependencies use lower bounds (`>=`), never `==` — `uv.lock` does
  the exact pinning.
- The `[tool.ruff]`, `[tool.ty.environment]` (or `[tool.pyright]`), and `[tool.pytest.ini_options]`
  blocks ship in the same file; their rationale lives in the `python-style`, `python-typing`, and
  `python-testing` skills.

## 4. Pin developer tooling in a dev dependency group

```sh
uv add --dev ruff ty pytest hypothesis
```

This lands in `[dependency-groups] dev` (PEP 735) — **not** `[project.optional-dependencies]`.
Dependency groups are for developing the project and are never published in the wheel; optional
dependencies are runtime extras for consumers. `uv sync` installs the group; `uv run <tool>`
executes it from the project environment, so there are no global installs to drift. Swap `ty` for
`pyright` (`uv add --dev pyright`) if the project type-checks with pyright instead — see the
`python-typing` skill.

## 5. Create the Makefile gate

Copy [templates/Makefile](templates/Makefile). Its `pr` target runs the full local gate in order —
`fmt lint typecheck test build` — every tool through `uv run` so the locked versions are used. It
mirrors the CI workflow (see `python-release`) so a green `make pr` means a green CI.

## 6. Keep the entry point thin

Copy the [`__main__.py` template](templates/__main__.py). `main(argv)` returns an `int` exit code and
`raise SystemExit(main())` runs under `if __name__ == "__main__"`; the real work lives in
importable modules so tests call functions directly instead of shelling out. Register the console
script under `[project.scripts]`.

## 7. Finish

- Write the first module and its tests (`python-style`, `python-typing`, `python-testing` skills).
- Document modules and public APIs as you go (`python-docs` skill).
- Wire releases, CI, and Dependabot with the `python-release` skill.
- Run `make pr` and make sure it passes before committing.
