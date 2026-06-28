# Python typing — edge cases

Companion to the `python-typing` skill. The bits the compact rules leave out.

## `Any` vs `object` vs a type variable

`Any` is compatible with everything in both directions, so it switches checking _off_ at every boundary it touches — one
`Any` parameter erases the types of everything derived from it. Use `object` when you truly accept anything but will
narrow before use (the checker forces the narrowing); use a type variable `[T]` when input and output types are linked;
use a `Protocol` when you need specific methods. Reserve `Any` for genuinely dynamic edges (deserialized JSON you
validate immediately) and annotate it explicitly so it is visible in review.

## Narrowing and `cast`

Prefer runtime narrowing the checker understands — `isinstance`, `is None`, an early `return`, an `assert` — over
`typing.cast`. `cast` asserts a type to the checker with no runtime check, so a wrong cast is an unchecked lie; use it
only at boundaries the checker cannot see (a plugin registry, a `__getattr__` facade) and keep it to one expression.

## `TYPE_CHECKING` and import cycles

Imports needed only for annotations go under `if TYPE_CHECKING:`, which is `False` at runtime but `True` for the type
checker. Combined with `from __future__ import annotations` (annotations stay strings), this breaks import cycles that
exist purely for typing and trims import-time cost. The names are still resolved by the checker, so referencing them in
annotations is fine.

## When deferred annotations bite

`from __future__ import annotations` (PEP 563) turns every annotation into a string. Anything that reads annotations at
runtime — `typing.get_type_hints()`, and libraries that build behavior from them — must resolve those strings, which
fails if the referenced names are not importable at call time (e.g. they live under `TYPE_CHECKING`). Most modern
libraries handle this, but if a serializer or validator needs concrete annotation objects, either drop the future import
in that module or keep the referenced types importable at runtime. PEP 649 (Python 3.14) replaces this with lazy
evaluation and removes the trade-off.

## Variance and mutable containers

A function that only reads a list of `Derived` should accept `Sequence[Base]`, not `list[Base]` — `list` is invariant,
so `list[Derived]` is **not** a `list[Base]`, and the checker will reject it. Annotate parameters with the read-only
abstract types (`Sequence`, `Mapping`, `Iterable`, `Collection`) and reserve the concrete mutable types (`list`, `dict`)
for what you own and mutate. This is the typing analogue of accepting the narrowest interface you need.
