---
name: dotnet-release
description: Release engineering for .NET projects — NuGet packaging from csproj metadata (PackageId, Authors, license expression, RepositoryUrl), deterministic builds with ContinuousIntegrationBuild and SourceLink, git-tag-driven SemVer via MinVer (or Nerdbank.GitVersioning), publishing to NuGet.org with Trusted Publishing (OIDC, no API key) from a tag-triggered GitHub Actions workflow, CI running build/format/test with SHA-pinned actions, and Dependabot for nuget and github-actions. Use when packaging or publishing a NuGet package, configuring dotnet pack metadata, setting up SourceLink or deterministic builds, versioning from git tags, writing CI or a tag-triggered release workflow for a .NET repo, or adding Dependabot. Not for scaffolding a new .NET project. For .NET/C# only.
license: MIT
---

# .NET release engineering

Tag-driven releases: pushing a `vX.Y.Z` tag packs the NuGet package — versioned from the tag,
deterministic, with embedded source links — and publishes it to NuGet.org over OIDC with no stored API
key. CI gates every push; Dependabot keeps dependencies and the action pins fresh. This layers on the
project layout from the `dotnet-project` skill. For the rationale behind each knob, see
[reference.md](reference.md).

## 1. Package metadata lives in the csproj (or Directory.Build.props)

Set `PackageId`, `Authors`, `Description`, `PackageLicenseExpression` (an SPDX id like `MIT`, not a
license file), `RepositoryUrl`, `PackageReadmeFile`, and `PackageTags`. Shared values go up to
`Directory.Build.props` (see the `dotnet-project` skill).

```xml
<PropertyGroup>
  <PackageId>Acme.Billing</PackageId>
  <Description>Billing primitives for the Acme platform.</Description>
  <PackageLicenseExpression>MIT</PackageLicenseExpression>
  <RepositoryUrl>https://github.com/OWNER/REPO</RepositoryUrl>
  <PublishRepositoryUrl>true</PublishRepositoryUrl>
</PropertyGroup>
```

## 2. Deterministic builds and SourceLink

`<ContinuousIntegrationBuild>true</ContinuousIntegrationBuild>` (in CI), `<Deterministic>true</Deterministic>`,
`<EmbedUntrackedSources>true</EmbedUntrackedSources>`, and the `Microsoft.SourceLink.GitHub` package so
consumers can step into your source and symbols resolve. Ship symbols as a `.snupkg`:

```xml
<PropertyGroup>
  <IncludeSymbols>true</IncludeSymbols>
  <SymbolPackageFormat>snupkg</SymbolPackageFormat>
</PropertyGroup>
```

## 3. Version from git tags with MinVer

A single `MinVer` `PackageReference` makes the package version the nearest `vX.Y.Z` tag; untagged builds
get a height-based prerelease (`1.2.3-alpha.0.4`). Tag and artifact can never drift — cutting a release
is pushing a `vX.Y.Z` tag, nothing more. (For `version.json` and build-height control, use
Nerdbank.GitVersioning instead — see [reference.md](reference.md).)

## 4. CI workflow

Copy [templates/ci.yaml](templates/ci.yaml) to `.github/workflows/ci.yaml`. On every push and pull
request it runs `dotnet restore`, `dotnet build --no-restore`, `dotnet format --verify-no-changes`, and
`dotnet test --no-build`. Conventions:

- The SDK comes from `global.json` (`setup-dotnet` with `global-json-file`), never hard-coded.
- Every action is pinned to a full commit SHA with the tag in a trailing comment — a moved tag can
  never change what runs. Dependabot keeps the pins fresh.
- `permissions: contents: read` — the default token does nothing else.

## 5. Release workflow and Dependabot

Copy [templates/release.yaml](templates/release.yaml) to `.github/workflows/release.yaml`. It triggers
on `v*` tags, checks out with `fetch-depth: 0` (MinVer needs full history and tags), runs
`dotnet pack -c Release`, and pushes to NuGet.org via **Trusted Publishing**: the `NuGet/login` action
exchanges the workflow's OIDC token (`permissions: id-token: write`) for a short-lived API key, so there
is no long-lived secret to store or rotate. Configure the trusted-publisher policy on NuGet.org once
first. Copy [templates/dependabot.yaml](templates/dependabot.yaml) to `.github/dependabot.yaml`: daily
checks, 7-day cooldown, minor + patch grouped per ecosystem (`nuget` and `github-actions`), majors
arriving alone. For the Trusted-Publishing setup, the MinVer-vs-Nerdbank choice, and the full ecosystem
matrix (`dotnet-sdk` for global.json, `docker`, `npm`), see [reference.md](reference.md).
