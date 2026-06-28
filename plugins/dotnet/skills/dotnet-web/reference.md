# ASP.NET Core minimal APIs — rationale and extended examples

Companion to the `dotnet-web` skill. Each section explains _why_ the rule exists and covers the depth the compact rules
omit. Backend HTTP APIs only — Blazor and MVC views are out of scope.

## Middleware ordering — the full pipeline

Middleware runs in registration order on the way in and reverse order on the way out, so position is behavior, not
style. The canonical order:

```csharp
app.UseExceptionHandler();        // outermost: catches everything below
app.UseHsts();                    // (production)
app.UseHttpsRedirection();
app.UseRouting();                 // implicit in minimal hosting, but explicit if you insert before it
app.UseCors();
app.UseAuthentication();          // must precede authorization
app.UseAuthorization();
app.UseOutputCache();             // if used
app.UseRateLimiter();             // if used
app.MapGroup("/items");           // endpoints last
```

Common failures from wrong order: authorization that always denies or always allows because it ran before authentication
populated the user; CORS headers missing because `UseCors` ran after the endpoint short-circuited; exceptions escaping
as bare 500s because the handler was registered after the throwing middleware.

## Minimal APIs vs Controllers

Minimal APIs are the default: less ceremony, explicit dependencies in the handler signature, and a direct path from
request to typed result. Controllers still earn their place for large APIs that benefit from convention-based routing,
action filters applied broadly, model binding from multiple sources with `[ApiController]` conventions, or teams with
heavy existing MVC investment. The two coexist in one app; don't convert a working controller API wholesale, but write
new endpoints as minimal APIs.

## Endpoint filters and validation

An endpoint filter runs around a handler — the minimal-API analog of an action filter — and is where cross-cutting
validation belongs:

```csharp
items.MapPost("/", CreateItem).AddEndpointFilter<ValidationFilter<CreateItemRequest>>();
```

In .NET 10, `builder.Services.AddValidation()` wires DataAnnotations validation into the pipeline so
`[Required]`/`[Range]` on a bound parameter are enforced automatically, returning a `ValidationProblem`. For cross-field
rules implement `IValidatableObject`. FluentValidation duplicates this with a separate DSL and dependency; prefer the
built-in path and reach for it only when validation logic genuinely outgrows DataAnnotations.

## IOptions, IOptionsSnapshot, IOptionsMonitor

- **`IOptions<T>`** — singleton, bound once at startup. The default; inject it anywhere.
- **`IOptionsSnapshot<T>`** — scoped, re-bound per request; use when config can change between requests and a request
  should see a consistent snapshot.
- **`IOptionsMonitor<T>`** — singleton with change notifications (`OnChange`); use in singletons or background services
  that must react to live config reloads.

Always `ValidateDataAnnotations().ValidateOnStart()` so a missing or malformed setting fails at boot, not on the first
request that reads it.

## ProblemDetails customization

`AddProblemDetails()` makes the framework emit RFC 9457 responses for error status codes. Customize the payload (add a
`traceId`, an `instance`, or extension members) via the `CustomizeProblemDetails` callback, and map specific exceptions
to specific status codes in the exception handler so clients get `409 Conflict` or `422 Unprocessable Entity` rather
than a blanket 500. Never serialize a raw exception message or stack trace to the client.

## OpenAPI document and transformers

`Microsoft.AspNetCore.OpenApi` generates the document from the endpoint metadata, so accurate typed results and
`.WithName`/`.WithSummary`/`.WithTags` annotations directly improve the spec. Use document and operation transformers to
add server URLs, security schemes, or shared response shapes. The built-in package produces the JSON document only; if
you want an interactive UI, serve Swagger UI or Scalar on top of the generated document rather than switching the
generator to Swashbuckle.

## Output caching and rate limiting

Both are built-in middleware (`AddOutputCache`, `AddRateLimiter`) and both are ordering-sensitive — they must sit after
routing/auth so cache keys and limiter partitions can use the authenticated identity, and before the endpoints they
protect. Define named policies and apply them per endpoint (`.CacheOutput("policy")`, `.RequireRateLimiting("policy")`)
rather than globally, so each route opts in to the behavior it needs.
