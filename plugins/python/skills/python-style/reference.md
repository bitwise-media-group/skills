# Python style — rationale and edge cases

Companion to the `python-style` skill. Why the rule selection is what it is, and the idiom edge cases the compact rules
omit.

## Why ruff replaces the old stack

A single Rust binary does what black + isort + flake8 + pylint + pyupgrade + autoflake used to, in a fraction of the
time and with one configuration surface. Running both ruff and one of the tools it subsumes means two formatters
fighting over the same lines or two linters disagreeing on imports — pick ruff and delete the rest, including their
config files (`.flake8`, `.isort.cfg`, `setup.cfg` lint sections) and pre-commit hooks.

`ruff format` is intentionally black-compatible, so adopting it on a black codebase is a no-op diff. Let it own line
length: configure `line-length` once and never hand-wrap or use `# fmt: off` except for genuinely tabular data (a
hand-aligned matrix), which is rare.

## Why this select set

The defaults (`E`, `F`) only catch syntax-level mistakes. The added families each pay for themselves:

- **`I`** sorts imports deterministically, ending the isort/CI churn.
- **`UP`** rewrites to the newest syntax the `target-version` allows — `X | None` over `Optional[X]`, `list[int]` over
  `List[int]`, f-strings over `%`/`.format`. It keeps a codebase from fossilizing at the version it was written in.
- **`B`** is the highest-signal family: mutable default arguments, loop-variable closures, `assert` on tuples, unused
  loop variables.
- **`SIM`** and **`C4`** remove needless complexity — collapsible `if`, redundant `dict()` calls, list-comprehensions
  that should be generators.
- **`PTH`** pushes `os.path` to `pathlib`.
- **`RUF`** carries ruff-native checks (e.g. mutable class defaults, unused `noqa`).

Avoid `select = ["ALL"]`: it enables every preview and stylistic rule, so each ruff upgrade can turn a green tree red,
and many families contradict each other (you immediately need a long `ignore`). Curate instead. Per-file ignores keep
tests pragmatic — `"tests/**" = ["S101"]` allows bare `assert` where pytest needs it.

## Logging edge cases

`logging.getLogger(__name__)` gives one logger per module, so consumers can raise or silence a subsystem by name. A
**library** must never call `basicConfig`, add handlers, or set a level at import time — that hijacks the application's
logging; add a `NullHandler` to the package logger if anything at all. Only the application entry point configures
handlers and levels.

Inside an `except`, `logger.exception("...")` records the traceback automatically — do not pass the exception as a
positional arg or format it into the message. Elsewhere use `logger.error("...", exc_info=err)` when you hold an
exception object.

## Exception edge cases

Re-raising with `raise NewError(...) from err` sets `__cause__`, so the traceback shows both the original and the
wrapping error — the analogue of Go's `%w`. Bare `raise` inside an `except` re-raises the current exception with its
traceback intact; use it when you only need to act on the error (log, clean up) and propagate. `raise X from None`
deliberately suppresses the cause — only when the original is noise. A small custom hierarchy (one base
`Error(Exception)` per package, with specific subclasses) lets callers catch broadly or narrowly without matching on
messages.

## Dataclasses vs alternatives

`@dataclass(slots=True)` for internal records (lower memory, no accidental attributes); `frozen=True` adds hashability
and immutability for value objects and dict/set keys. Reach for a `typing.NamedTuple` only when tuple-unpacking or
positional indexing is the point, and for an `Enum` instead of string or int constants. Validation-heavy boundaries
(config, request bodies) are where a third-party model library (e.g. Pydantic) earns its place — plain dataclasses do
not validate.
