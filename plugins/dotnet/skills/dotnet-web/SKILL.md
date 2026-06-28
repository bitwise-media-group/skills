---
name: dotnet-web
description: ASP.NET Core minimal-API conventions (.NET 8+) — MapGet/MapPost endpoints, route groups with MapGroup, typed results via Results<T> and TypedResults, model binding and validation, DI lifetimes (AddSingleton/Scoped/Transient), the options pattern with IOptions, ProblemDetails error responses, correct middleware ordering, health checks, and built-in OpenAPI via Microsoft.AspNetCore.OpenApi. Use when building or reviewing an ASP.NET Core HTTP API or service — adding a minimal-API endpoint or route group, returning typed results, registering services in DI, binding configuration with the options pattern, wiring middleware, adding health checks, or exposing an OpenAPI document. Backend HTTP APIs only — not Blazor, MVC views, or UI. For .NET/C# only.
license: MIT
---

# ASP.NET Core minimal-API conventions

Backend HTTP APIs on the stdlib-first stack: minimal APIs, the built-in DI container, the options
pattern, `ProblemDetails`, and the in-box OpenAPI document — no MVC controllers, no third-party
mediator/validation/mapping libraries unless the framework genuinely falls short. This covers HTTP APIs
only; **not** Blazor, Razor Pages, or MVC views. For the C# itself see the `dotnet-style` skill; for the
rationale and the full middleware/options depth see [reference.md](reference.md).

## 1. Minimal APIs, grouped by resource

`app.MapGet`/`MapPost` with `MapGroup` route groups; handlers are named methods, not fat lambdas — they
parse and validate, then call a service.

```csharp
var items = app.MapGroup("/items");
items.MapGet("/{id}", GetItem);
items.MapPost("/", CreateItem);
```

## 2. Return typed results

Declare the status codes in the signature with `Results<T1, T2>` and produce them with `TypedResults`,
so the contract is explicit and the OpenAPI document is accurate.

```csharp
static async Task<Results<Ok<Item>, NotFound>> GetItem(string id, IItemStore store, CancellationToken ct)
    => await store.FindAsync(id, ct) is { } item ? TypedResults.Ok(item) : TypedResults.NotFound();
```

## 3. Register services with the right lifetime

`AddSingleton` for stateless, thread-safe services; `AddScoped` for per-request services (a DbContext —
see the `dotnet-data` skill); `AddTransient` for cheap, stateless helpers. Never inject a scoped service
into a singleton (a captive dependency that outlives its scope). Use constructor or primary-constructor
injection — never a service locator.

## 4. Configuration through the options pattern

Bind a configuration section to a typed record and inject `IOptions<T>` (`IOptionsSnapshot<T>` when you
need per-request reload); validate at startup so misconfiguration fails fast.

```csharp
builder.Services.AddOptions<SmtpOptions>()
    .Bind(builder.Configuration.GetSection("Smtp"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

Don't read `IConfiguration["..."]` scattered through handlers.

## 5. Validate input and reject early

Validate with DataAnnotations and the built-in minimal-API validation (`AddValidation()` /
`[FromBody]` validation in .NET 10), or `IValidatableObject` for cross-field rules — not FluentValidation
by default. Return `TypedResults.ValidationProblem(errors)` on failure.

## 6. Errors as ProblemDetails

Call `builder.Services.AddProblemDetails()` and return `TypedResults.Problem(...)` /
`ValidationProblem(...)` so every error is RFC 9457 (formerly RFC 7807) JSON. A top-level exception
handler maps unhandled exceptions to a 500 ProblemDetails without leaking internals.

```csharp
app.UseExceptionHandler();
app.UseStatusCodePages();
```

## 7. Middleware order is load-bearing

Exception handler → HSTS/HTTPS redirect → routing → CORS → authentication → authorization → endpoints.
`UseAuthentication` must come before `UseAuthorization`, and the exception handler is outermost. Wrong
order silently breaks auth or error handling — see [reference.md](reference.md) for the full table.

## 8. Health checks

`AddHealthChecks()` and map `/healthz` for liveness and `/readyz` for readiness (with dependency checks);
keep probe traffic out of request logging.

```csharp
app.MapHealthChecks("/healthz");
app.MapHealthChecks("/readyz", new() { Predicate = c => c.Tags.Contains("ready") });
```

## 9. OpenAPI via the built-in package

`builder.Services.AddOpenApi()` + `app.MapOpenApi()` (`Microsoft.AspNetCore.OpenApi`) — not Swashbuckle
by default. Typed results (rule 2) make the document accurate; add `.WithName`/`.WithSummary`/`.WithTags`
metadata so the spec reads well for clients and LLMs. Reach for Swashbuckle or NSwag only when you
specifically need Swagger UI or client generation, layered on the built-in document.

## 10. Thin endpoints, testable host

Endpoints adapt HTTP to services and return; business logic lives in injected services (apply the
`dotnet-style` skill). Keep `Program.cs` composition-only and expose the `Program` class so
`WebApplicationFactory<Program>` can host it in integration tests (see the `dotnet-testing` skill).
