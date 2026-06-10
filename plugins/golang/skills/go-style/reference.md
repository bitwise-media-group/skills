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

For a small program the stdlib `flag` package plus `os.LookupEnv` fallbacks is enough; `pflag` + `viper` earn their
place once the flag table grows or config files enter the picture.

## Dependencies: stdlib-first

`net/http`, `log/slog`, `encoding/json`, `testing`, and `database/sql` cover most service needs. Every dependency is a
supply-chain exposure, an upgrade treadmill, and a reader's context switch. When a dependency genuinely earns its place
(cloud SDKs, OpenTelemetry), wrap it in a small `internal/` package so the rest of the codebase depends on your
interface, not the vendor's — swapping or upgrading then touches one package.
