---
name: dotnet-style
description: Modern C# code style for stdlib-first .NET (C# 14 / .NET 8+) — file-scoped namespaces, nullable reference types, records and primary constructors for data, pattern matching, async/await with CancellationToken threading and ConfigureAwait, ILogger structured logging over Console.WriteLine, System.Text.Json over Newtonsoft, collection expressions, and exception wrapping. Use when writing, reviewing, or refactoring any C#/.NET code (.cs files, libraries, services): handling exceptions, adding logging, threading cancellation, making a method async, shaping a record or DTO, choosing var vs explicit types, serializing JSON, or modernizing LINQ. For C#/.NET only — not other languages.
license: MIT
---

# C# style conventions

Stdlib-first conventions for modern C# (C# 14 / .NET 8+): the BCL, `Microsoft.Extensions.*`,
`System.Text.Json`, and the built-in DI container cover most needs — reach for a third-party package
only when the framework genuinely cannot do the job. Apply these to new code and match them when
editing existing code. For the rationale behind each rule and the edge cases, see
[reference.md](reference.md).

## 1. File-scoped namespace, one top-level type per file

A file-scoped `namespace` (no brace block) and one public type per file; let `ImplicitUsings` and
`global using` carry the common namespaces (configured in the `dotnet-project` skill).

```csharp
namespace Acme.Billing;

public sealed class Invoice { }
```

Seal classes that are not designed for inheritance — it documents intent and lets the JIT devirtualize.

## 2. Nullable reference types on; express absence with `T?`

NRTs are enabled solution-wide (the project knob lives in the `dotnet-project` skill). Model "no
value" as `T?`, never a sentinel like `""` or `-1`, and guard arguments at the boundary:

```csharp
public Client Get(string id)
{
    ArgumentNullException.ThrowIfNull(id);
    return _store[id];
}
```

Never sprinkle `#nullable disable` or the `!` null-forgiving operator to silence a warning — fix the
nullability instead. `!` is for the rare case where you genuinely know more than the compiler.

## 3. `record` / `readonly record struct` for immutable data

DTOs and domain values are `record` types with `init`-only members and value equality; small value
types are `readonly record struct`.

```csharp
public record Money(decimal Amount, string Currency);
```

Mutable persistence entities (EF Core) stay plain classes — see the `dotnet-data` skill.

## 4. Primary constructors capture dependencies

Services take their collaborators through a primary constructor and use them directly — no boilerplate
fields or assignments.

```csharp
public sealed class Broker(IClientStore store, ILogger<Broker> log)
{
    public Task<Client> GetAsync(string id, CancellationToken ct) => store.FindAsync(id, ct);
}
```

## 5. Pattern matching over type-test cascades

`switch` expressions, property patterns, and `is` declarations replace chains of `if`/cast and
`switch` statements that fall through.

```csharp
string tier = status switch
{
    >= 500 => "server-error",
    >= 400 => "client-error",
    _ => "ok",
};
```

## 6. Expression-bodied members where they read cleanly

Use `=>` for one-line properties, methods, and constructors; keep a block body when there is real
logic. Don't contort a multi-statement method into one expression to save a brace.

## 7. `var` when the type is apparent

Use `var` when the right-hand side names the type (`new`, casts, `as`, a factory whose name says the
type); use the explicit type when the call is opaque and the type aids the reader. This is enforced by
`.editorconfig` (`csharp_style_var_when_type_is_apparent`), not by taste.

```csharp
var invoice = new Invoice();          // type is on the line
Client client = store.Resolve(id);    // explicit — Resolve's return type isn't obvious
```

## 8. Async: `Task`-returning, `CancellationToken` threaded, no `async void`

Every method that does I/O is `async Task`/`Task<T>`, takes a `CancellationToken`, and forwards it.
`async void` is only ever an event handler. In library code add `ConfigureAwait(false)`; app and
ASP.NET Core code may omit it (no ambient synchronization context).

```csharp
public async Task<Client> GetAsync(string id, CancellationToken ct) =>
    await _store.FindAsync(id, ct).ConfigureAwait(false);
```

Never block on a task with `.Result`/`.Wait()` — see the `dotnet-perf` skill for the deadlock.

## 9. Structured logging with `ILogger<T>`, never `Console.WriteLine`

Inject `ILogger<T>` and log with message templates and named placeholders — not interpolated strings,
which defeat structured sinks. The exception is the first argument, not part of the message.

```csharp
log.LogError(ex, "client map load failed for {ClientId}", id);
```

For hot paths use the `LoggerMessage` source generator (see the `dotnet-perf` skill). `Console.Write*`
is for CLI program output, never for diagnostics.

## 10. Wrap exceptions with context; preserve the chain

Catch only what you can act on, wrap it in a domain exception passing the original as `innerException`,
and re-throw with a bare `throw;` (never `throw ex;`, which resets the stack trace). Don't catch
`Exception` broadly except at a top-level boundary, and never swallow.

```csharp
try
{
    return await _store.FindAsync(id, ct);
}
catch (IOException ex)
{
    throw new ClientLoadException($"load client {id}", ex);
}
```

## 11. `System.Text.Json`, not Newtonsoft.Json

Serialize with `System.Text.Json`; cache a single `JsonSerializerOptions` instance and prefer a
source-generated `JsonSerializerContext` for AOT and hot paths. Reach for `Newtonsoft.Json` only for a
genuine feature gap, and isolate it behind one type.

```csharp
private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
var dto = JsonSerializer.Deserialize<ClientDto>(body, Json);
```

## 12. Readable LINQ; keep `dotnet format` clean

Method-syntax LINQ for transforms, named locals over deeply nested lambdas; materialize once with
`ToList()`/`ToArray()` and don't re-enumerate a query. Code is always `dotnet format`-clean and
warning-free (analyzers configured in the `dotnet-project` skill). Comments state invariants the code
cannot — never narrate the next line. Keep LINQ off measured hot paths (see the `dotnet-perf` skill).

For tests and fakes see the `dotnet-testing` skill; for project layout, analyzers, and `.editorconfig`
see the `dotnet-project` skill; for HTTP APIs see the `dotnet-web` skill; for data access see the
`dotnet-data` skill; for doc comments see the `dotnet-docs` skill.
