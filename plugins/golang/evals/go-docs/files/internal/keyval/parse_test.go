package keyval

import "testing"

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
			name:      "basic key and value",
			input:     "key=value",
			wantKey:   "key",
			wantValue: "value",
		},
		{
			name:      "value contains equals",
			input:     "key=value=extra",
			wantKey:   "key",
			wantValue: "value=extra",
		},
		{
			name:      "empty value",
			input:     "key=",
			wantKey:   "key",
			wantValue: "",
		},
		{
			name:      "trim whitespace around key and value",
			input:     " key = value ",
			wantKey:   "key",
			wantValue: "value",
		},
		{
			name: "missing equals",
			input: "novalue",
			wantErr: true,
		},
		{
			name:      "empty key after trimming whitespace",
			input:     "  =  value",
			wantKey:   "",
			wantValue: "value",
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
