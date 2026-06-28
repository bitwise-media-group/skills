---
name: dotnet-testing
description: Test authoring and review with xUnit on .NET (C# 14 / .NET 8+). Use when writing, adding, generating, or reviewing C#/.NET tests for a class, method, or service; using [Fact] and [Theory] with [InlineData] or [MemberData] for table-driven cases; setting up fixtures with the constructor, IDisposable, IClassFixture, or IAsyncLifetime; choosing between hand-written fakes and Moq; asserting with the built-in Assert (not FluentAssertions); testing an ASP.NET Core endpoint with WebApplicationFactory; measuring coverage with coverlet; or running dotnet test. Covers xUnit conventions, theories, fixtures, fakes over mocks, and integration tests. For .NET/C# only — not Jest, pytest, or Go testing.
license: MIT
---

# .NET testing conventions

xUnit is the whole toolkit: theories for table-driven cases, the test class itself for fixtures,
hand-written fakes for collaborators, and `WebApplicationFactory` for endpoints. No assertion DSLs, no
mock generators. For the code under test see the `dotnet-style` skill; for project and test-project
layout see the `dotnet-project` skill.

## 1. Theories are the table-driven pattern

`[Theory]` with `[InlineData]` for literal cases, `[MemberData]`/`[ClassData]` when cases need objects
or computation. Adding a behavior is adding a row, not a method. Use `[Fact]` for a single-case
behavior. Name tests `Method_state_expectation`.

```csharp
[Theory]
[InlineData("a=b", "a", false)]
[InlineData("ab", null, true)]
public void Parse_givenLine_returnsKeyOrThrows(string input, string? key, bool throws)
{
    if (throws)
    {
        Assert.Throws<FormatException>(() => KeyVal.Parse(input));
        return;
    }

    var (parsedKey, _) = KeyVal.Parse(input);
    Assert.Equal(key, parsedKey);
}
```

## 2. Built-in `Assert`, no assertion DSL

`Assert.Equal`, `Assert.True`, `Assert.Throws<T>`, `Assert.Collection`, `Assert.Contains` state the
contract and add no dependency. Don't introduce FluentAssertions (commercial-licensed since v8) or
Shouldly — a project that already owns a FluentAssertions ≤7 license may keep it, but never add it to
new projects.

## 3. Fixtures: the constructor for per-test, `IClassFixture<T>` for shared

xUnit constructs a fresh test-class instance per test, so the constructor is per-test setup and
`IDisposable.Dispose` (or `IAsyncLifetime` for async setup/teardown) is per-test cleanup. Share
expensive context — a database, a `WebApplicationFactory` — across a class with `IClassFixture<T>`, and
across classes with a collection fixture.

```csharp
public sealed class StoreTests(DbFixture fx) : IClassFixture<DbFixture>
{
    [Fact]
    public async Task Save_persistsRow() { /* uses fx.Context */ }
}
```

## 4. Hand-written fakes over Moq

Substitute a small class implementing the consumer's interface with canned returns, and assert on
observable behavior (return values, recorded state) — not on which methods were called.

```csharp
sealed class FakeClock : IClock
{
    public DateTimeOffset Now { get; init; }
    public DateTimeOffset UtcNow() => Now;
}
```

Reserve generated mocks (Moq, NSubstitute) for wide third-party seams you don't own — and even then,
prefer asserting outcomes over verifying call sequences, which couples the test to the implementation.

## 5. Async tests return `Task` and await

`async Task` test methods that await the system under test; assert async throws with
`await Assert.ThrowsAsync<T>(...)`. Never `.Result` or `.Wait()` in a test — it deadlocks under some
runners and masks the real exception behind an `AggregateException`.

## 6. Integration-test endpoints with `WebApplicationFactory`

`WebApplicationFactory<TProgram>` hosts the app in memory — no sockets — so you exercise the real
pipeline (routing, model binding, filters, DI) through an `HttpClient`. See the `dotnet-web` skill for
the endpoint side.

```csharp
var client = factory.CreateClient();
var res = await client.PostAsJsonAsync("/items", new { name = "x" });
Assert.Equal(HttpStatusCode.Created, res.StatusCode);
```

For data tests, run against a real provider over SQLite (or the in-memory provider for pure logic) — see
the `dotnet-data` skill.

## 7. Coverage with coverlet; keep tests independent

`dotnet test --collect:"XPlat Code Coverage"` (coverlet ships with the test template) produces Cobertura
coverage. Keep each test independent and deterministic: no shared mutable static state, no ordering
assumptions, one behavior per test.

## 8. Invocations

```sh
dotnet test                                       # the whole solution
dotnet test --filter "FullyQualifiedName~Parse"   # one class or method
dotnet test --collect:"XPlat Code Coverage"       # with coverage
```

Microsoft Testing Platform (MTP) is the direction of travel — xUnit v3 runs on it — so prefer the MTP
runner where a project has adopted it. CI runs the same `dotnet test` (see the `dotnet-project` and
`dotnet-release` skills).
