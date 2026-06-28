# .NET performance — anti-pattern catalogue

Companion to the `dotnet-perf` skill. A categorized catalogue of the allocation, async, string, LINQ, collection, and
value-type anti-patterns worth scanning for once a profile points at a hot path. Each is a "fix it _here_, where it's
measured" — not a blanket rewrite. Measure first (skill rule 1).

## Async

- **Sync-over-async** — `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` block a thread and can deadlock under a
  captured context. Go async to the entry point.
- **`async void`** — exceptions throw into the sync context and crash the process; the caller can't await. Only ever an
  event handler.
- **Unawaited fire-and-forget** — a `Task` discarded without `await` swallows exceptions and races shutdown. Await it,
  or hand it to a managed background runner.
- **Missing `CancellationToken`** — an async method that ignores cancellation can't be stopped; thread the token through
  every call.
- **`await` in a tight loop where the work is independent** — serializes parallel work. Collect the tasks and
  `await Task.WhenAll`.
- **Async over trivial sync work** — wrapping CPU-bound work in `Task.Run` on the request path adds a thread hop for no
  concurrency win.

## Allocation and GC pressure

- **`Substring` / `Split` for parsing** — allocates strings and arrays; slice with `ReadOnlySpan<char>` and
  `MemoryExtensions` (`AsSpan`, `IndexOf`, `Split` over spans) instead.
- **Boxing value types** — passing a `struct` as `object`/non-generic interface, or `int` into a `params object[]`,
  allocates. Use generics, and interpolated-string handlers that avoid boxing.
- **LINQ on hot paths** — each operator allocates an iterator; closures capture and allocate. Drop to `for`/`foreach`.
- **Per-call `new` of reusable objects** — `JsonSerializerOptions`, `Regex`, `HttpClient`, `StringBuilder` recreated per
  call. Cache or pool them; use a static compiled `[GeneratedRegex]`.
- **Large transient arrays** — rent from `ArrayPool<T>.Shared` and return in `finally`.
- **`MemoryStream` churn** — use `RecyclableMemoryStreamManager` in throughput code.
- **Closures capturing loop variables** — allocate a display class per iteration; hoist invariants out of the lambda or
  avoid the lambda.

## Strings

- **`+=` in a loop** — O(n²) copies. `StringBuilder`, or `string.Join`/`string.Concat` for a one-shot.
- **`string.Format`/interpolation as a concatenation operator** — formats and allocates even when not needed;
  concatenate small fixed pieces directly.
- **Building known-length strings via `StringBuilder`** — `string.Create(length, state, span => …)` writes once into the
  final buffer with no intermediate.
- **Culture-sensitive comparison by default** — `==`/`ToLower()` for keys and identifiers; use
  `StringComparison.Ordinal`/`OrdinalIgnoreCase` to skip culture tables and avoid bugs.
- **`ToLower()`/`ToUpper()` to compare** — allocates a new string; use the `IgnoreCase` comparison.

## Collections

- **No capacity hint** — `new List<T>()` / `new Dictionary<,>()` that grows in a loop reallocates and rehashes. Pass the
  known capacity to the constructor.
- **`Count()` on an `IEnumerable`** — enumerates the whole sequence; use `.Count` on a materialized collection or
  `TryGetNonEnumeratedCount`.
- **`ContainsKey` then indexer** — two lookups; use `TryGetValue` or `CollectionsMarshal` for one.
- **Re-enumerating a query** — each `foreach`/`Count`/`Any` re-runs it; materialize once with `ToList`/`ToArray`.
- **`List<T>` where a `HashSet<T>`/`Dictionary` fits** — O(n) membership checks in a loop become O(n²).

## Value types and the JIT

- **Large mutable structs** — copy on every assignment, parameter pass, and collection store. Keep structs small (≤16
  bytes) and immutable, or use a `class`.
- **`readonly struct` not marked `readonly`** — defensive copies on every member access through a `readonly` field. Mark
  the struct (and members) `readonly`.
- **Passing big structs by value** — pass by `in` to avoid the copy; return by `ref`/`ref readonly` where appropriate.
- **Interface dispatch on a struct** — boxes it. Constrain a generic to the interface (`where T : IShape`) so the JIT
  specializes without boxing.

## Logging and serialization

- **Interpolated log messages** — formatting happens even at disabled levels and breaks structured fields; use message
  templates (see the `dotnet-style` skill) and `[LoggerMessage]` source-gen on hot paths.
- **Reflection-based JSON on hot/AOT paths** — use a source-generated `JsonSerializerContext` (see the `dotnet-style`
  skill).

## Data access

EF Core has its own hot-path traps — N+1, tracking read-only queries, cartesian explosion from multiple collection
includes, missing `CancellationToken`. They live in the `dotnet-data` skill; treat that skill as the data-layer section
of this catalogue.

## Confirm with tools

Every entry above is a hypothesis until a `[MemoryDiagnoser]` BenchmarkDotNet run or a `dotnet-trace`/`dotnet-gcdump`
capture confirms the cost and the fix. Optimize the path the tools point at, re-measure, and stop when the numbers say
you're done.
