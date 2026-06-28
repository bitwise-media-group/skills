// Package keyval parses key=value pairs.
package keyval

import (
	"fmt"
	"strings"
)

// Parse splits "key=value" into its parts. The key must be non-empty.
func Parse(s string) (key, value string, err error) {
	key, value, ok := strings.Cut(s, "=")
	if !ok {
		return "", "", fmt.Errorf("parse %q: missing '='", s)
	}
	if key == "" {
		return "", "", fmt.Errorf("parse %q: empty key", s)
	}
	return key, value, nil
}
