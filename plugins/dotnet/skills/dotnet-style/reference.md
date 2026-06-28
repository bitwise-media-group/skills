# C# style — rationale and extended examples

Companion to the `dotnet-style` skill. Each section explains _why_ the rule exists and covers the edge cases the compact
rules omit.

## Nullable reference types: why `T?` over sentinels

With NRTs on, the type system tracks nullability: `string` is a promise the value is never null, `string?` admits null
and forces the compiler to make you check before you dereference. A sentinel (`""`, `-1`, `Guid.Empty`) re-implements
"absence" without compiler help, and every caller has to know the magic value. `T?` makes absence part of the signature,
and the flow analysis catches the dereference you forgot.

The `!` null-forgiving operator suppresses the warning without changing runtime behavior — it is a claim that you know
more than the analyzer. Legitimate uses are narrow: a field initialized by a framework after construction (`[Required]`
model binding, `MemberNotNull` patterns), or a test asserting non-null right after an act. Reaching for `!` to quiet a
warning you don't understand just moves the `NullReferenceException` to runtime. `#nullable disable` at file scope is
worse — it blinds the whole file. Prefer `ArgumentNullException.ThrowIfNull` at public boundaries so the failure is a
clear `ArgumentNullException` at the call, not a `NullReferenceException` three frames deep.

## Async: the correctness rules behind rule 8

- **Never sync-over-async.** `.Result`, `.Wait()`, and `.GetAwaiter().GetResult()` block the calling thread until the
  task completes. Under a context that marshals continuations back to a captured thread (legacy ASP.NET, WPF, WinForms),
  the continuation needs the very thread you blocked — a deadlock. Even without a sync context it ties up a thread-pool
  thread that could do work. Make the call chain async to the entry point instead; ASP.NET Core and modern console apps
  support async `Main`.
- **`async void` only for event handlers.** A `Task`-returning method lets the caller await and observe exceptions; an
  `async void` throws into the synchronization context, where it usually crashes the process. The only place the
  signature is forced on you is an event handler (`EventHandler`).
- **`ConfigureAwait(false)` in libraries.** A library cannot know whether its caller has a sync context, and capturing
  one it doesn't need costs a marshalling hop. `ConfigureAwait(false)` says "resume anywhere". Application and ASP.NET
  Core code has no ambient sync context, so the call is a no-op there — omit it for readability. (`ConfigureAwait(true)`
  is the default; you only ever write `false`.)
- **`CancellationToken` is threaded, not stored.** Take it as a parameter (conventionally last) and pass it down to
  every async call so a cancelled request actually stops work. Storing one in a field freezes the cancellation story at
  construction time.

For `ValueTask` and `IAsyncEnumerable` — performance-motivated async shapes — see the `dotnet-perf` skill; reach for
them only when a benchmark justifies the added care (a `ValueTask` may be awaited only once).

## Logging: why message templates, not interpolation

`log.LogInformation("loaded {Count} clients for {Tenant}", count, tenant)` keeps the template string constant and emits
`Count` and `Tenant` as structured fields a sink (Seq, Application Insights, OTLP) can index and filter. An interpolated
string — `log.LogInformation($"loaded {count} clients…")` — bakes the values into one opaque message: no fields to
query, a new distinct string per call (so log de-duplication and sampling break), and the formatting cost is paid even
when the level is disabled. The analyzer `CA2254` flags the interpolated form.

Inject `ILogger<T>` through the constructor; the `<T>` sets the category to the type's name for free. A `static` logger
or `Console.WriteLine` hides the dependency and makes per-test capture impossible. For hot paths, the `[LoggerMessage]`
source generator emits an allocation-free, strongly-typed log method — the `dotnet-perf` skill covers when it pays.

## Exceptions: design, not just syntax

`throw;` rethrows the caught exception with its original stack trace intact; `throw ex;` throws the same object but
resets the trace to the rethrow line, erasing where it actually came from — always the former. Wrap only to add context
the caller lacks (which client, which file), and always pass the original as `innerException` so `.InnerException` and
the logged trace keep the full chain. Custom exception types earn their place when callers branch on the failure
(`catch (ClientLoadException)`); otherwise a BCL type (`InvalidOperationException`, `ArgumentException`) is fine. Catch
narrowly — `catch (IOException)`, not `catch (Exception)` — except at a process boundary (a request handler, `Main`)
where a top-level handler logs and converts to a response. Never catch-and-swallow: an empty `catch` block turns a bug
into silent data loss. To rethrow a captured exception from a different thread, use
`ExceptionDispatchInfo.Capture(ex).Throw()`.

## JSON: why `System.Text.Json` and source generation

`System.Text.Json` (STJ) is the BCL serializer: it is what ASP.NET Core, `Microsoft.Extensions.*`, and the configuration
system already use, so a project on STJ has one serializer and one set of conventions. It is `Span`-based and
allocation-light, and — unlike reflection-based Newtonsoft — it has a source generator (`JsonSerializerContext`) that
emits the (de)serialization code at build time, which is both faster and required for Native AOT / trimming (see the
`dotnet-perf` skill).

```csharp
[JsonSerializable(typeof(ClientDto))]
public partial class AppJsonContext : JsonSerializerContext;

var dto = JsonSerializer.Deserialize(body, AppJsonContext.Default.ClientDto);
```

Cache `JsonSerializerOptions` — constructing one per call rebuilds and re-caches metadata and is a known performance
footgun (`CA1869`). Newtonsoft.Json remains the answer for a few genuine gaps (`JsonPath` queries, some `JObject`
dynamic scenarios, certain legacy polymorphism); when you need it, confine it to one boundary type rather than threading
it through the codebase.

## Records vs class vs struct

| Use                                              | Type                        |
| ------------------------------------------------ | --------------------------- |
| Immutable data / DTO with value equality         | `record` (class)            |
| Small (≤16 bytes) immutable value, no identity   | `readonly record struct`    |
| Entity with identity / mutable persistence state | `class` (see `dotnet-data`) |
| Reference type needing reference equality        | `class`                     |

Records give you value equality, `with`-expressions, and a deconstructor for free, which is exactly what a DTO wants and
exactly what an entity with identity does not (two customers with the same fields are not the same customer). A
`record struct` avoids a heap allocation for a genuinely small value; a large `struct` copies on every pass and usually
costs more than it saves — see the `dotnet-perf` skill.

## Collection expressions and the `var` decision

C# 12+ collection expressions unify collection construction: `int[] xs = [1, 2, 3];`, `List<int> ys = [.. xs, 4];` (the
`..` spread). Prefer them over `new[] { … }` / `new List<int> { … }` for new code. For `var`, the line that decides is
whether the type is _apparent from the right-hand side_: `var c = new Client();` and `var c = (Client)obj;` are obvious;
`var c = Resolve(id);` is not — write `Client c = Resolve(id);` there. Encode the rule in `.editorconfig`
(`csharp_style_var_when_type_is_apparent = true`, `csharp_style_var_elsewhere = false:suggestion`) so it is enforced,
not argued.

## Dependencies: stdlib-first

The BCL plus `Microsoft.Extensions.*` (DI, logging, configuration, options, HTTP) covers the spine of most services;
`System.Text.Json` covers serialization; the built-in `IServiceCollection` covers composition. Every added package is a
supply-chain exposure, an upgrade treadmill, and a reader's context switch — and several popular ones have non-obvious
costs (AutoMapper's runtime mapping hides allocations and breaks AOT, MediatR adds indirection for no behavior,
FluentValidation duplicates DataAnnotations). When a dependency genuinely earns its place (a cloud SDK, OpenTelemetry, a
specialized serializer), wrap it behind an internal interface so the rest of the codebase depends on your abstraction,
not the vendor's, and swapping or upgrading touches one file.
