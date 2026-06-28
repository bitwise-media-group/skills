---
name: dotnet-docs
description: .NET documentation conventions — XML doc comments (/// <summary>, <param>, <returns>, <exception>, <remarks>) on every public type and member, GenerateDocumentationFile with missing-doc warnings (CS1591) treated as errors, a README convention, and an optional DocFX site. Use when writing or reviewing XML doc comments or /// summaries in C#, documenting a public .NET API, type, or method, enabling the documentation file and doc warnings, choosing a doc-comment style, or generating an API reference site for a .NET library. For .NET/C# only — not OpenAPI/REST specs (see the dotnet-web skill).
license: MIT
---

# .NET documentation conventions

XML doc comments are the API's reference manual: IntelliSense, the generated documentation file, and
DocFX all render them, and LLM coding agents read them to learn an API. These rules say what they look
like and how to make them mandatory. For the code itself see the `dotnet-style` skill.

## 1. Every public API carries an XML doc comment

A `///` comment with `<summary>` on every public type, method, property, and event; add `<param>`,
`<returns>`, and `<exception>` where they apply, and `<remarks>` for invariants the caller relies on.
Document behavior, not implementation.

```csharp
/// <summary>Splits a <c>KEY=VALUE</c> line into its key and value, trimming whitespace.</summary>
/// <param name="line">A single key=value pair.</param>
/// <returns>The parsed key and value.</returns>
/// <exception cref="FormatException">The separator is missing or the key is empty.</exception>
public static (string Key, string Value) Parse(string line);
```

Begin a summary with a verb describing what the member does (`Splits…`, `Returns…`), not "This method".

## 2. Link with `<see cref>` and reuse with `<inheritdoc/>`

Reference other types and members with `<see cref="Parse"/>` — the compiler verifies the target, so a
rename that breaks the link fails the build. Pull base-class or interface documentation forward with
`<inheritdoc/>` instead of copy-pasting, so the doc has one source of truth.

## 3. Turn doc comments into a build gate

Set `<GenerateDocumentationFile>true</GenerateDocumentationFile>` on public and packable projects. With
`TreatWarningsAsErrors` (see the `dotnet-project` skill), CS1591 "missing XML comment for publicly
visible type or member" then fails the build, so undocumented public API can't ship. Scope it to shipped
assemblies — don't force docs on test or sample projects:

```xml
<PropertyGroup Condition="'$(IsTestProject)' == 'true'">
  <NoWarn>$(NoWarn);CS1591</NoWarn>
</PropertyGroup>
```

## 4. README is the front door

Every packable project sets `<PackageReadmeFile>README.md</PackageReadmeFile>` and ships the README in
the NuGet package (see the `dotnet-release` skill). The README states what the library is and why, a
quickstart, and one minimal end-to-end example — the things a reference of `///` comments can't convey.

## 5. An API reference site is optional — DocFX

Most libraries need only good `///` comments plus a README. When a library warrants a browsable
reference site, DocFX builds it from the same XML doc comments and the `<GenerateDocumentationFile>`
output. Pin DocFX as a local `dotnet tool` (see the `dotnet-project` skill) and commit its config, not
the generated site.
