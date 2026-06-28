package keyval

import (
	"strings"
	"testing"
)

func TestParse(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		input     string
		wantKey   string
		wantValue string
		wantErr   bool
	}{
		{
			name:      "basic key/value",
			input:     "key=value",
			wantKey:   "key",
			wantValue: "value",
		},
		{
			name:      "key with empty value",
			input:     "key=",
			wantKey:   "key",
			wantValue: "",
		},
		{
			name:      "value with equals",
			input:     "key=value=extra",
			wantKey:   "key",
			wantValue: "value=extra",
		},
		{
			name:    "missing equals",
			input:   "key",
			wantErr: true,
		},
		{
			name:    "empty key",
			input:   "=value",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			gotKey, gotValue, err := Parse(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("Parse(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
			if tt.wantErr {
				return
			}
			if gotKey != tt.wantKey {
				t.Fatalf("Parse(%q) key = %q, want %q", tt.input, gotKey, tt.wantKey)
			}
			if gotValue != tt.wantValue {
				t.Fatalf("Parse(%q) value = %q, want %q", tt.input, gotValue, tt.wantValue)
			}
		})
	}
}

func FuzzParse(f *testing.F) {
	f.Add("key=value")
	f.Add("")
	f.Add("key")
	f.Add("=value")
	f.Add("key=")
	f.Add("key=value=extra")
	f.Add(" spaced key = spaced value ")
	f.Add("\x00=\xff")

	f.Fuzz(func(t *testing.T, s string) {
		key, value, err := Parse(s)
		if err != nil {
			return
		}

		if key == "" {
			t.Fatalf("Parse(%q) accepted an empty key", s)
		}
		if !strings.Contains(s, "=") {
			t.Fatalf("Parse(%q) accepted input without '='", s)
		}

		wantKey, wantValue, _ := strings.Cut(s, "=")
		if key != wantKey {
			t.Errorf("Parse(%q) key = %q, want %q", s, key, wantKey)
		}
		if value != wantValue {
			t.Errorf("Parse(%q) value = %q, want %q", s, value, wantValue)
		}
	})
}
