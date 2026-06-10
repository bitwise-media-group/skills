---
name: go-testing
description: Go testing conventions — table-driven tests with t.Run subtests, plain stdlib assertions (no testify or assertion frameworks), hand-written fakes behind small interfaces, t.Helper() helpers, httptest for HTTP handlers, and native fuzz targets (testing.F) with seed corpora. Use when writing or reviewing Go tests (_test.go files), testing a Go HTTP handler, adding a fuzz test or seed corpus to a Go package, or choosing go test flags for a Makefile or CI (-race, -fuzz, -fuzztime).
license: MIT
---

# Go testing conventions

The standard `testing` package is the whole toolkit: table-driven tests, hand-written fakes,
`httptest` for handlers, and native fuzzing. No assertion libraries, no mock generators.

## 1. Table-driven tests with subtests

One slice of cases, one `t.Run` per case named for the behavior it pins down:

```go
func TestParse(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		wantKey string
		wantErr bool
	}{
		{"simple pair", "a=b", "a", false},
		{"missing separator", "ab", "", true},
		{"empty key", "=b", "", true},
		{"empty value ok", "a=", "a", false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			key, _, err := Parse(c.in)
			if (err != nil) != c.wantErr {
				t.Fatalf("Parse(%q) error = %v, wantErr %v", c.in, err, c.wantErr)
			}
			if key != c.wantKey {
				t.Errorf("Parse(%q) key = %q, want %q", c.in, key, c.wantKey)
			}
		})
	}
}
```

Adding a behavior means adding a row, not a function.

## 2. Plain stdlib assertions

`if got != want { t.Errorf(...) }` — no testify, gomega, or other assertion DSLs. Failure
messages follow `f(input) = got, want want` so the log reads as the broken contract. Use
`t.Fatalf` when continuing is pointless (setup failed, wrong status code); `t.Errorf` to keep
collecting independent mismatches.

## 3. Fakes over mocks

Tests substitute a hand-written fake for the small consumer-defined interface (see the `go-style`
skill) — a struct with canned returns, not a generated mock with expectations:

```go
type fakeMinter struct {
	token     string
	expiresIn int64
	err       error
}

func (f *fakeMinter) Mint(_ context.Context, _ string, _ []string) (string, int64, error) {
	return f.token, f.expiresIn, f.err
}
```

Assert on observable behavior (responses, state), not on which methods were called.

## 4. Helpers take `t` and call `t.Helper()`

Shared setup is a function taking `t *testing.T`, calling `t.Helper()` first so failures point at
the caller, and using `t.Cleanup` for teardown. Helpers fail the test themselves (`t.Fatalf`)
rather than returning errors.

## 5. Test HTTP handlers with `httptest`

No network, no test server — build a request, record the response:

```go
req := httptest.NewRequest(http.MethodPost, "/token", strings.NewReader(form.Encode()))
req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
rr := httptest.NewRecorder()
broker.Handler().ServeHTTP(rr, req)
if rr.Code != http.StatusUnauthorized {
	t.Fatalf("status = %d, want %d (body: %s)", rr.Code, http.StatusUnauthorized, rr.Body.String())
}
```

## 6. Fuzz targets assert properties, with seed corpora

Every parser or validator handling untrusted input gets a `Fuzz*` target. Seed the interesting
shapes with `f.Add`, then assert the properties that must hold for *any* input — no panics, and
the security-critical invariants:

```go
func FuzzParse(f *testing.F) {
	f.Add("a=b")
	f.Add("")
	f.Add("=value")
	f.Fuzz(func(t *testing.T, s string) {
		key, _, err := Parse(s) // must not panic on any input
		if err == nil && key == "" {
			t.Errorf("Parse(%q) accepted an empty key", s)
		}
	})
}
```

`go test ./...` replays the seed corpus on every run, so fuzz targets double as regression tests.

## 7. Invocations

```sh
go test ./...                                              # unit tests + fuzz seed corpora
go test -race ./...                                        # CI always runs with the race detector
go test -run '^$' -fuzz '^FuzzParse$' -fuzztime 20s ./internal/keyval   # fuzz one target
```

Only one fuzz target can run per package invocation, so the Makefile parameterizes it
(`make fuzz FUZZ=FuzzParse FUZZTIME=20s`) — see the `go-project` skill for the Makefile and the
`go-release` skill for the CI wiring.
