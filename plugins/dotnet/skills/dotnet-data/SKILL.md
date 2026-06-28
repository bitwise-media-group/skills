---
name: dotnet-data
description: EF Core data-access conventions (.NET 8+) — DbContext registered scoped (or via a pooled factory), avoiding N+1 with Include and projections to DTOs, AsNoTracking for read-only queries, async query methods threading CancellationToken, the migrations workflow with dotnet ef, compiled queries and split queries for hot paths, and never enabling lazy loading. Use when writing or reviewing EF Core data access — querying with LINQ, projecting to DTOs, fixing N+1 or slow queries, registering or scoping a DbContext, adding or applying migrations, choosing AsNoTracking or split queries, or threading CancellationToken through data calls. For EF Core on .NET/C# only — not Dapper, raw ADO.NET, or other ORMs.
license: MIT
---

# EF Core data-access conventions

Entity Framework Core conventions for correct, predictable, allocation-aware data access. Read-only
queries skip tracking, navigations load explicitly, and every query is async and cancellable. For the C#
itself see the `dotnet-style` skill; for measuring and tuning hot paths see the `dotnet-perf` skill.

## 1. Register the DbContext scoped; pool for hot paths

`AddDbContext<T>` gives a per-request scoped context, which matches a web request's lifetime (see the
`dotnet-web` skill). Use `AddDbContextPool<T>` for high-throughput services, or `AddDbContextFactory<T>`
when you need to control the lifetime yourself (background workers, parallel work). Never share one
context across threads — a `DbContext` is not thread-safe.

```csharp
builder.Services.AddDbContext<BillingContext>(o => o.UseNpgsql(connectionString));
```

## 2. `AsNoTracking` for read-only queries

A query that only reads and returns data should skip the change tracker — less allocation, no identity
resolution, faster. Track only when you intend to mutate and `SaveChanges`.

```csharp
var items = await db.Items.AsNoTracking()
    .Where(i => i.Active)
    .ToListAsync(ct);
```

## 3. Kill N+1 with `Include` or projections

Loading a list and then touching each row's navigation property issues one query per row — the N+1
trap. Either `Include` the navigation, or — better for reads — project straight to a DTO so EF emits a
single join and selects only the columns you need.

```csharp
var dtos = await db.Orders.AsNoTracking()
    .Select(o => new OrderDto(o.Id, o.Customer.Name, o.Lines.Count))
    .ToListAsync(ct);
```

Hand-written projections like this are also why the house style avoids AutoMapper (see the
`dotnet-style` skill) — the projection is the mapping, and it shapes the SQL.

## 4. Async query methods, CancellationToken threaded

`ToListAsync`, `FirstOrDefaultAsync`, `SingleOrDefaultAsync`, `SaveChangesAsync` — each passed the
request's `CancellationToken` so a cancelled request stops the query. Never block on a query with
`.Result`/`.Wait()` (see the `dotnet-perf` skill).

## 5. Never enable lazy loading

Lazy-loading proxies turn an innocent property access into a surprise round-trip — hidden N+1 that
doesn't show up in the query you wrote. Leave `UseLazyLoadingProxies` off and load explicitly with
`Include` or a projection.

## 6. Split queries for multiple collection includes

A single query that includes more than one collection navigation produces a cartesian explosion (rows
multiplied across collections). `AsSplitQuery()` issues one query per collection instead. Use it when
including multiple collections; keep the default single query otherwise.

```csharp
var order = await db.Orders
    .Include(o => o.Lines)
    .Include(o => o.Payments)
    .AsSplitQuery()
    .FirstOrDefaultAsync(o => o.Id == id, ct);
```

## 7. Compiled queries for measured hot paths

`EF.CompileAsyncQuery` caches the translated query so a frequently-run query skips re-translation on
each call. Reserve it for paths a profiler has shown to be hot (see the `dotnet-perf` skill) — most
queries don't need it, and it adds a static field and ceremony.

## 8. Migrations workflow with `dotnet ef`

`dotnet ef migrations add <Name>`, review the generated migration, `dotnet ef database update` locally,
and apply on deploy via a migration bundle or an explicit migration step — not `EnsureCreated` (which
bypasses migrations) and not auto-migrate-on-startup in production (which races across instances). Pin
`dotnet-ef` in the tool manifest (see the `dotnet-project` skill).

```sh
dotnet ef migrations add AddOrders
dotnet ef database update
```

## 9. Keep EF out of the domain seams

Entities are plain classes the context maps; query logic lives in repository or service methods that
return DTOs. Handlers (see the `dotnet-web` skill) and tests (see the `dotnet-testing` skill, against
SQLite or the in-memory provider) then depend on those methods, not on `DbContext` internals leaking
through the codebase.
