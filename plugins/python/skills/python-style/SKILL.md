---
name: python-style
description: Modern Python house style: ruff is the single formatter and linter (replacing black, isort, flake8, pylint, pyupgrade) with an opinionated lint select set, plus idioms ruff cannot enforce — pathlib over os.path, module-level logging instead of print, specific chained exceptions, dataclasses for data, comprehensions and context managers. Use when formatting, linting, reviewing, or refactoring Python code or improving its idiomatic style; setting up, configuring, or running ruff (in pyproject.toml or replacing black/isort/flake8/pylint), or choosing which ruff lint rules to enable; converting print to logging, fixing exception handling, choosing pathlib vs os.path, or otherwise shaping errors, logging, file I/O, or data structures in Python. Not for type annotations, docstrings, tests, project/uv scaffolding, or non-Python languages.
license: MIT
---

# Python style conventions

`ruff` is the whole formatting and linting toolchain — it replaces black, isort, flake8, pylint,
pyupgrade, and autoflake. Apply these conventions to new code and match them when editing existing
code. For the rationale behind the rule selection and the idiom edge cases, see
[reference.md](reference.md).

## 1. ruff is the formatter and the linter

`ruff format` owns layout (it is black-compatible — do not also run black) and `ruff check` owns
linting and import sorting (do not also run isort or flake8). Run both through `uv run`:

```sh
uv run ruff format .          # format in place (the line-length authority)
uv run ruff check --fix .     # lint + sort imports + apply safe fixes
```

Let `ruff format` win every formatting argument — never hand-format around it or sprinkle
`# fmt: off`.

## 2. Select rules explicitly

Ruff's default is tiny (`E`, `F`). Opt into the families that catch real bugs and modernize code,
in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
    "E", "F",   # pycodestyle + pyflakes (the baseline)
    "I",        # import sorting (replaces isort)
    "UP",       # pyupgrade — modern syntax for the target-version
    "B",        # bugbear — likely bugs (mutable defaults, shadowing)
    "SIM",      # flake8-simplify — collapse needless complexity
    "C4",       # comprehension correctness/clarity
    "PTH",      # flag os.path usage in favor of pathlib
    "RUF",      # ruff's own rules
]
```

Set `target-version` (e.g. `py313`) so `UP` rewrites to syntax your floor supports, and a
`line-length`. Add `D` (docstrings) per the `python-docs` skill. Avoid `select = ["ALL"]`: it
silently enables new rules on every upgrade.

## 3. Idioms ruff cannot fully enforce

State these as rules; they need no example:

- **`pathlib.Path`, not `os.path` or string paths.** `Path(...) / "sub"`, `.read_text()`,
  `.exists()` — the `PTH` rules flag the old forms.
- **Logging, never `print`, in library and service code.** Module logger via
  `logging.getLogger(__name__)`; configure handlers/levels **only** at the application entry point,
  never at import time. Pass the exception with `logger.exception(...)` inside an `except`.
- **Specific exceptions, always chained.** Raise the narrowest built-in or a small custom
  hierarchy; re-raise with `raise NewError(...) from err` so the cause survives. No bare `except:`,
  no `except Exception: pass`.
- **Dataclasses for data.** `@dataclass(slots=True)` for records, `frozen=True` for value objects —
  not ad-hoc dicts or tuples passed between functions.
- **Comprehensions, context managers, and EAFP.** Prefer a comprehension to a `map`/`filter` +
  loop, a `with` block to manual open/close, and `try/except` to pre-checking when the happy path
  dominates.

## 4. Keep ruff clean

`uv run ruff format --check .` and `uv run ruff check .` must pass with no findings before every
commit — they run in `make pr` and in CI. Comments explain *why*, not *what* the next line does.

For type annotations and `ty` see the `python-typing` skill; for tests see `python-testing`; for
docstrings see `python-docs`; for the Makefile and project layout see `python-project`; for CI and
releases see `python-release`.
