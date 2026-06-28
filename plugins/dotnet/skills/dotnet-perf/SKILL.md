---
name: dotnet-perf
description: .NET performance and diagnostics conventions (.NET 8+) — fixing async anti-patterns (sync-over-async deadlocks, async void), cutting allocations with Span<T>/Memory<T>/stackalloc and ArrayPool, building strings with StringBuilder/string.Create, avoiding LINQ and closures in hot paths, choosing struct vs class, benchmarking with BenchmarkDotNet, profiling with dotnet-trace/dotnet-counters/dotnet-dump, and Server GC / Native AOT awareness. Use when profiling or optimizing C#/.NET, fixing a sync-over-async deadlock or high allocations, reducing GC pressure, speeding up a hot path, writing a BenchmarkDotNet benchmark, or diagnosing CPU/memory with the dotnet diagnostic tools. For .NET/C# only — measure before optimizing.
license: MIT
---

# .NET performance and diagnostics

Performance work is measurement first, then targeted change. These rules cover the changes that pay off
once a benchmark or profile has found the hot path — and the tools that find it. Most code is not hot;
keep it readable (see the `dotnet-style` skill) and optimize the proven path. For the reference
catalogue of allocation, async, string, and LINQ anti-patterns, see [reference.md](reference.md).

## 1. Measure first

Don't optimize without a benchmark or a profile. A `BenchmarkDotNet` microbenchmark (rule 9) or a
`dotnet-trace`/`dotnet-counters` capture (rule 10) tells you where time and allocations actually go —
which is rarely where intuition says.

## 2. No sync-over-async

`.Result`, `.Wait()`, and `.GetAwaiter().GetResult()` on a `Task` block a thread and can deadlock under
a captured synchronization context. Make the call chain async to the entry point instead.

```csharp
var client = await store.GetAsync(id, ct);   // not store.GetAsync(id, ct).Result
```

See the `dotnet-style` skill for async correctness (`async void` is covered there).

## 3. Cut allocations in hot paths

Slice with `Span<T>`/`ReadOnlySpan<T>` instead of `Substring`/array copies; `stackalloc` small,
short-lived buffers; and avoid LINQ lambdas where a `foreach` allocates nothing.

```csharp
ReadOnlySpan<char> key = line.AsSpan(0, separator);   // no substring allocation
```

## 4. Pool reusable buffers

`ArrayPool<T>.Shared.Rent`/`Return` (in a `try`/`finally`) for transient large arrays, and
`RecyclableMemoryStream` over `new MemoryStream()` in throughput-sensitive code. Only in measured hot
paths — pooling adds lifetime complexity and a return-it-exactly-once obligation.

## 5. Build strings without quadratic copies

`StringBuilder` for accumulation (never `+=` in a loop, which is O(n²)), `string.Create` when the final
length is known, and `string.Concat`/interpolation for a one-shot join.

```csharp
var sb = new StringBuilder();
foreach (var part in parts)
    sb.Append(part).Append(',');
```

## 6. LINQ off the hot path

LINQ allocates an iterator and a closure per call; in a tight loop a plain `for`/`foreach` is
allocation-free and faster. Keep LINQ for readability in cold code (see the `dotnet-style` skill) and
drop to loops only where a profiler shows the cost.

## 7. `struct` vs `class`, deliberately

Small (≤16 bytes), short-lived, immutable value-like data is a `readonly struct` to avoid a heap
allocation; pass large structs by `in` to avoid copies. Default to `class` for anything with identity or
that escapes — a misused struct copies more than it saves.

## 8. `ValueTask` and `IAsyncEnumerable` where they pay

`ValueTask`/`ValueTask<T>` for hot async methods that usually complete synchronously (await it exactly
once, never twice). `IAsyncEnumerable<T>` to stream results without buffering the whole set into a list.
Don't reach for `ValueTask` by default — `Task` is simpler and its common results are cached.

## 9. Benchmark with BenchmarkDotNet

A `[MemoryDiagnoser]` benchmark, run in Release, quantifies time and allocations and compares
alternatives — the only credible basis for "X is faster than Y".

```csharp
[MemoryDiagnoser]
public class ParseBench
{
    [Benchmark]
    public (string, string) Parse() => KeyVal.Parse("key=value");
}
```

## 10. Diagnose with the dotnet tools; know your GC

`dotnet-counters` (live counters), `dotnet-trace` (sampling and events), and
`dotnet-dump`/`dotnet-gcdump` (heap analysis) — pin them as `dotnet tool`s (see the `dotnet-project`
skill). Enable Server GC (`<ServerGarbageCollection>true</ServerGarbageCollection>`) for throughput
services, and be Native-AOT/trimming-aware: avoid reflection-heavy patterns and prefer source-generated
JSON (see the `dotnet-style` skill) when targeting AOT. For data-layer performance see the `dotnet-data`
skill.
