# Go style — rationale and extended examples

Companion to the `go-style` skill. Each section explains _why_ the rule exists and covers the edge cases the compact
rules omit.

## Errors: why wrap once with `%w`

`fmt.Errorf("operation: %w", err)` preserves the wrapped error so `errors.Is` and `errors.As` can inspect the chain;
`%v` flattens it to a string and severs it. The message convention — lowercase operation, no "failed to" — exists
because messages compose into chains. Each layer adds exactly one clause:

```text
load config: bind flags: unknown flag --prot
```

With "failed to" at every layer the same chain stutters: `failed to load config: failed to bind flags: …`. Wrap at the
boundary where you add information the caller cannot infer (which file, which client, which operation); pass through
errors whose message already carries that context. Double-wrapping shows up in logs as repeated clauses and is a
reliable sign the wrap belongs one layer down.

For aggregating independent failures (e.g. closing several resources), use `errors.Join` — it preserves every branch for
`errors.Is`.

## Sentinels and error types: why never match strings

Callers that branch on a failure mode need something stable to branch on. A package-level sentinel is the contract; the
message is documentation:

```go
var ErrUnknownClient = errors.New("unknown client")

// caller
if errors.Is(err, clientmap.ErrUnknownClient) {
	oauthErr(w, http.StatusUnauthorized, "invalid_client", "unknown client_id")
	return
}
```

String comparison (`strings.Contains(err.Error(), "unknown client")`) breaks the moment someone rewords the message, and
the compiler cannot help. Use a custom error type with `errors.As` when callers need data from the failure (an offset, a
status code), not just its identity.

## Logging: why `log/slog` and `LogAttrs`

Structured JSON on stdout is the lingua franca of log collectors — Cloud Run, Kubernetes, and systemd all capture it
natively, and the OpenTelemetry `otelslog` bridge can forward the same records to a logs pipeline without touching call
sites. Conventions that keep records useful:

- `log.LogAttrs(ctx, level, msg, attrs...)` over `log.Info(msg, "k", v)`: typed attrs, no interface boxing on disabled
  levels, and the context carries the active span so bridges can attach `trace_id`.
- Errors go in an attribute, `slog.Any("error", err)`, never interpolated into the message — collectors index the
  message as a low-cardinality event name.
- Inject `*slog.Logger` through constructors. A package-level logger hides the dependency and makes per-test silencing
  impossible. `slog.New(slog.DiscardHandler)` (Go 1.24+) is the no-op default for optional loggers.

## Context: why first-parameter and never stored

The `ctx context.Context` first parameter is the ecosystem-wide convention (`go vet` and reviewers expect it), and it
makes cancellation flow visible in every signature. Storing a context in a struct freezes whatever cancellation/deadline
existed at construction time and detaches the struct's operations from their callers' lifetimes — the documented
exception is a request-shaped struct (like `http.Request`) that _is_ one operation.

Derive the root context once, in `main`, from process signals:

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()
```

Everything downstream — server shutdown, in-flight RPCs, cache reloads — inherits one cancellation story, and a second
SIGINT kills the process because `stop()` restores default signal behavior after the first.

## Interfaces: why the consumer defines them

Go interfaces are satisfied implicitly, so the consumer can declare exactly the slice of behavior it uses — no producer
cooperation needed. A one-method interface defined next to its caller:

- documents what the caller actually depends on;
- lets tests substitute a five-line hand-written fake instead of a generated mock;
- lets `main` choose between implementations (e.g. a keyless impersonation minter in production, a key-file minter for
  local development) without either knowing about the other.

"Accept interfaces, return structs": producers return concrete types so callers keep access to the full API; consumers
narrow to what they need. Resist exporting an interface from the producer "for mocking" — that inverts the dependency
and grows god-interfaces.

## Constructors: why nil-tolerant dependencies

Optional dependencies — loggers, metrics, tracers — default to no-ops inside the constructor rather than forcing every
call site (and every test) to build them:

```go
func NewBroker(loader *clientmap.Loader, minter token.Minter, log *slog.Logger) *Broker {
	if log == nil {
		log = slog.New(slog.DiscardHandler)
	}
	return &Broker{loader: loader, minter: minter, log: log}
}
```

Tests construct `NewBroker(loader, fake, nil)` and stay focused on behavior. Required dependencies (the things the type
cannot function without) are _not_ nil-tolerant — passing nil for those should fail loudly and early.

## HTTP: why the stdlib mux and handler-wrapping middleware

Since Go 1.22 the stdlib mux routes by method and wildcard (`POST /token`, `GET /items/{id}`, `r.PathValue("id")`),
which removes the main historical reason for router frameworks. A service with a handful of routes needs zero
dependencies for routing.

Middleware as `func(http.Handler) http.Handler` composes with anything in the ecosystem (including `otelhttp`). The
canonical request logger wraps the writer to capture status and keeps probe noise out:

```go
func requestLogging(log *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path == "/healthz" || r.URL.Path == "/readyz" {
				next.ServeHTTP(w, r)
				return
			}
			start := time.Now()
			sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(sw, r)
			log.LogAttrs(r.Context(), slog.LevelInfo, "request",
				slog.String("method", r.Method),
				slog.String("path", r.URL.Path),
				slog.Int("status", sw.status),
				slog.Duration("duration", time.Since(start)))
		})
	}
}
```

`statusWriter` is the small `http.ResponseWriter` wrapper that records the first `WriteHeader` call.

## Configuration: why flag > env > default

Flags are self-documenting (`--help` is the reference) and explicit invocations beat ambient state; env vars are how
container platforms inject settings; defaults make local runs zero-config. Binding them in that precedence — each flag
auto-mapped to `FLAG_NAME` upper-cased with dashes as underscores — gives one table of knobs that works identically in a
terminal and a deployment manifest. Keep all of it in one `Config` struct with a single `Validate()` called at startup:
every misconfiguration is reported before the program does any work.

For a service or single-purpose binary the stdlib `flag` package plus `os.LookupEnv` fallbacks is enough.

## CLI tools: why cobra + viper

The dividing line is subcommands. The moment a program grows a command tree (`myapp serve`, `myapp migrate up`), the
stdlib `flag` package forces hand-rolled dispatch, per-command flag sets, and a help system you maintain yourself —
exactly the boilerplate `cobra` exists to own. Cobra contributes the command tree, persistent vs. local flags, generated
help/completions, and the metadata (`Short`, `Long`, `Example`, `GroupID`) that doc generators consume (see the
`go-docs` skill). `viper` complements it on the configuration side: `BindPFlags` merges each command's flags with
`AutomaticEnv` (prefixed, dashes→underscores) and optional config files into one lookup with the same flag > env >
config file > default precedence the stdlib pattern establishes.

Two rules keep the dependency contained: commands stay thin adapters — parse and validate input, then call `internal/`
packages, returning errors through `RunE` so `main` keeps the only `os.Exit` — and viper stays at the edge: resolve it
into a plain `Config` struct at startup and pass that down, so business logic never imports `viper` or reads ambient
state. A service with one entrypoint and a handful of flags does not need either library; don't add them until the
subcommands arrive.

## String building: why `strings.Builder` and not `+=`

Go strings are immutable, so `s += t` cannot append in place — it allocates a fresh string and copies both operands into
it. Inside a loop the copies compound: building an n-byte result one piece at a time copies O(n²) bytes and leaves a
trail of garbage for the collector. `strings.Builder` accumulates into an internal byte slice that grows
amortized-linearly (the same doubling strategy as `append`), and its `String()` returns the result without a final copy.

```go
var spec strings.Builder
for i, d := range defaults {
	if i > 0 {
		spec.WriteString(",")
	}
	spec.WriteString(d)
}
return spec.String()
```

Concatenating _inside_ a builder write smuggles the same allocation back in. `b.WriteString(prefix + l + "\n")` builds a
temporary string on the heap every iteration, copies it into the builder, then discards it — the builder was supposed to
be the destination, not a second copy. Sequential writes append each piece directly into the builder's buffer:

```go
func writeComment(b *strings.Builder, prefix string, lines []string) {
	for _, l := range lines {
		b.WriteString(prefix)
		b.WriteString(l)
		b.WriteString("\n")
	}
}
```

This isn't aesthetic — `WriteString` never fails (the returned error is always nil), so a chain of writes costs nothing
in error handling, and three appends into one growing buffer beat one allocate-copy-discard per iteration.

Choosing the right tool:

- **`strings.Join(parts, sep)`** when the pieces are already a `[]string` and you only need a separator — it
  preallocates the exact result size and reads as intent, not mechanics. The loop above is `strings.Join(defaults, ",")`
  when nothing else happens per element.
- **`strings.Builder`** when pieces arrive incrementally, are conditional, or mix types — `WriteString`, `WriteByte`,
  `WriteRune`, and `fmt.Fprintf(&b, ...)` all target it. Call `Grow(n)` first when the final size is known. One write
  per piece — never `+` inside the argument.
- **`+`** for a one-shot concatenation of a few operands in a single expression, outside any loop or builder — the
  compiler sizes that allocation correctly; the problem is _repeated_ appends and throwaway temporaries.
- **`fmt.Sprintf`** when you need formatting verbs, not as a concatenation operator.

A `Builder` must not be copied after first use (`go vet` flags it); pass `*strings.Builder` if it crosses a function
boundary.

## Iteration: why `Seq` variants over slice-returning splits

Go 1.24 added iterator (`iter.Seq[string]`) twins for the splitting functions: `strings.SplitSeq`,
`strings.SplitAfterSeq`, `strings.FieldsSeq`, `strings.FieldsFuncSeq`, and `strings.Lines` (with the same set in
`bytes`). `for _, w := range strings.Fields(s)` scans the whole input up front and allocates a `[]string` whose only
purpose is to be ranged over once and garbage-collected; the `Seq` form yields each piece lazily as the scan finds it:

```go
for w := range strings.FieldsSeq(s) {
	// ...
}
```

Beyond skipping the slice allocation, laziness means a `break` stops the scan early — `Fields` pays for the whole input
even if the loop returns on the first word. The individual words allocate nothing in either form (they are substrings
sharing the input's backing array); the slice header and its growth are the waste.

Keep the slice-returning forms when the slice itself is the point: you need `len(parts)`, random access by index, a
sort, multiple passes, or you hand the slice to another function. An iterator consumed exactly once by one loop is the
signal to switch.

## `slices` and `maps`: why not hand-rolled loops

Go 1.21 made the generic `slices` and `maps` packages stdlib. A scan-and-compare loop forces the reader to
reverse-engineer the intent (is it membership? first match? does the `break` matter?) and is where off-by-one and
forgotten-`break` bugs live; the named call is the intent, works for any element type, and gets the optimized
implementation:

| Hand-rolled loop                         | Stdlib call                                          |
| ---------------------------------------- | ---------------------------------------------------- |
| scan for `x == v`, `break`               | `slices.Contains(s, v)` / `slices.ContainsFunc`      |
| scan for index of first match            | `slices.Index(s, v)` / `slices.IndexFunc`            |
| element-wise compare two slices          | `slices.Equal` / `slices.EqualFunc`                  |
| track `min`/`max` through a loop         | `slices.Min` / `slices.Max` / `slices.MaxFunc`       |
| `sort.Slice(s, func(i, j int) bool {…})` | `slices.Sort` / `slices.SortFunc` (no interface box) |
| collect map keys/values into a slice     | `slices.Collect(maps.Keys(m))` / `slices.Sorted(…)`  |
| remove adjacent duplicates after sorting | `slices.Compact`                                     |

`slices.SortFunc` with `cmp.Compare` replaces `sort.Slice` outright — generics avoid the `interface{}` boxing and
reflection of the `sort` package, so it is both clearer and faster. `maps.Keys`/`maps.Values` return iterators (Go
1.23); range over them directly, and materialize with `slices.Collect` or `slices.Sorted` only when a slice is actually
needed — the same once-vs-keep test as the `Seq` rule above.

Keep the explicit loop when the body does real per-element work — transforming values, appending to multiple
collections, or interleaving effects — and when a helper would need contortions (a closure capturing three locals) to
express what a four-line loop says plainly.

## `min`/`max`: why the builtins beat comparison guards

Go 1.21 added `min` and `max` as predeclared builtins — distinct from the `slices.Min`/`slices.Max` functions, which
take a slice; the builtins take a variadic list of ordered arguments. They subsume one of the oldest idioms in
imperative code: declare a value, then nudge it back inside a bound with an `if`.

```go
paneH := d.h - footerH - headerH
if paneH < 3 {
	paneH = 3
}
```

That is four lines the reader has to execute mentally to learn one fact — `paneH` is at least 3.
`paneH := max(d.h-footerH-headerH, 3)` states the fact directly. Three shapes cover every clamp:

- `max(x, lo)` — raise to a floor; the result is never below `lo`.
- `min(x, hi)` — cap at a ceiling; the result is never above `hi`.
- `min(max(x, lo), hi)` — confine to the inclusive range `[lo, hi]`.

They are generic over `cmp.Ordered`, so the same calls work for `int`, `float64`, `time.Duration`, or `string`, and they
accept more than two arguments (`max(a, b, c)`) when several candidates compete. `gopls`'s `minmax` modernizer rewrites
the guard form for you — `gopls modernize` or the editor quick-fix applies it across a package, which is the diagnostic
("if statement can be modernized using max") you see in-editor.

One caveat for floating-point: the builtins follow the Go spec's NaN and signed-zero rules, which can differ in those
corner cases from a hand-rolled comparison. For integer clamps — the overwhelming majority of real uses — the builtin
and the guard are exactly equivalent, and the builtin is the one to write.

## Dependencies: stdlib-first

`net/http`, `log/slog`, `encoding/json`, `testing`, and `database/sql` cover most service needs. Every dependency is a
supply-chain exposure, an upgrade treadmill, and a reader's context switch. When a dependency genuinely earns its place
(cloud SDKs, OpenTelemetry), wrap it in a small `internal/` package so the rest of the codebase depends on your
interface, not the vendor's — swapping or upgrading then touches one package.
