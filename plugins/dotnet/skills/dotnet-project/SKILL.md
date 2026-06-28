---
name: dotnet-project
description: Scaffold and modernize a .NET solution with the canonical layout — src/ and tests/, SDK-style .csproj, a Directory.Build.props sharing Nullable/ImplicitUsings/TreatWarningsAsErrors and Roslyn analyzers, Central Package Management in Directory.Packages.props, a global.json pinning the SDK, an .editorconfig, a dotnet-tools.json manifest, and a .slnx solution. Use when creating a new .NET project, library, service, or repo; restructuring to src/+tests; enabling nullable, implicit usings, or analyzers; adopting Central Package Management or Directory.Build.props; pinning the SDK with global.json; or adding a dotnet tool manifest. For .NET/C# only — not other languages.
license: MIT
---

# Scaffold a .NET project

Creates a .NET repository with the canonical layout, shared build properties, Central Package
Management, and pinned tooling. Apply the `dotnet-style` and `dotnet-testing` skills while filling in
real code, and wire releases with the `dotnet-release` skill. Templates for every file below live in
[templates/](templates/) — copy them and replace the `App`/`Acme` placeholders.

## 1. Lay out the tree

```text
src/<Project>/<Project>.csproj   # one project per assembly; the host holds no business logic
tests/<Project>.Tests/...        # mirrors src/, one test project per src project
Directory.Build.props            # MSBuild properties every project inherits
Directory.Packages.props         # Central Package Management — every version lives here
global.json                      # pins the SDK band
.editorconfig                    # formatting + analyzer severities
.config/dotnet-tools.json        # pinned local dotnet tools
App.slnx                         # the solution
```

Name projects for what they provide (`Acme.Billing`, `Acme.Billing.Api`) — never `Common`, `Utils`,
or `Shared`.

## 2. SDK-style `.csproj`, minimal and declarative

`<Project Sdk="Microsoft.NET.Sdk">` (or `Microsoft.NET.Sdk.Web` for a service). No `packages.config`,
no hand-written `AssemblyInfo.cs`, no per-file `<Compile>` items — the SDK globs sources implicitly.
Start from `dotnet new`, keep `TargetFramework` and package-specific metadata in the csproj, and push
everything shared up to `Directory.Build.props`.

## 3. `Directory.Build.props` for shared properties

One file at the repo root sets the defaults every project inherits — the single place to turn on
nullable, implicit usings, analyzers, and warnings-as-errors.

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <EnableNETAnalyzers>true</EnableNETAnalyzers>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  </PropertyGroup>
</Project>
```

## 4. Central Package Management

Set `<ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>` in
`Directory.Packages.props` and declare every version once as a `<PackageVersion>` there. Project files
then carry bare `<PackageReference Include="..." />` with **no** `Version` attribute — one source of
truth for the whole solution, so two projects can never drift onto different versions.

## 5. Pin the SDK with `global.json`

Pin the SDK band so CI and every developer build on the same toolchain; `rollForward: latestFeature`
takes patch/feature updates inside the pinned major without surprise minor jumps.

```json
{ "sdk": { "version": "10.0.100", "rollForward": "latestFeature" } }
```

## 6. `.editorconfig` is the formatting and style contract

Encoding, indentation, the `var` policy, naming rules, and `dotnet_diagnostic.*` severities all live in
`.editorconfig`. `dotnet format`, the IDE, and — because rule 3 sets `EnforceCodeStyleInBuild` — the
build all read the same file, so style is enforced identically everywhere.

## 7. Roslyn analyzers, warnings as errors

`EnableNETAnalyzers` + `AnalysisLevel` turn on the first-party analyzers; `TreatWarningsAsErrors` makes
every analyzer and compiler warning block the build. Suppress a specific diagnostic narrowly — a scoped
`<NoWarn>`, a justified `[SuppressMessage]`, or a local `#pragma warning disable` with a reason — never
blanket-disable a category.

## 8. Pin local tools in a manifest

`dotnet new tool-manifest` then `dotnet tool install <tool>` writes `.config/dotnet-tools.json`;
`dotnet tool restore` reproduces them on any machine. Pin the CLIs you actually run (`dotnet-ef`,
`dotnet-format` if not in-box, a coverage reporter) — never a global install, which drifts per machine.

## 9. Use a `.slnx` solution

The new XML `.slnx` format is terser and merge-friendly compared with the legacy `.sln`; manage it with
`dotnet sln`. (Fall back to `.sln` only if your toolchain predates `.slnx` support.) Finish by writing
the first project and its tests (`dotnet-style`, `dotnet-testing`), documenting as you go
(`dotnet-docs`), and wiring releases (`dotnet-release`); make `dotnet build` and
`dotnet format --verify-no-changes` pass before committing.
