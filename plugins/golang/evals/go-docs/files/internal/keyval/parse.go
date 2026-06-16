package keyval

import (
	"fmt"
	"strings"
)

func Parse(line string) (key, value string, err error) {
	k, v, ok := strings.Cut(line, "=")
	if !ok {
		return "", "", fmt.Errorf("parse line %q: missing '='", line)
	}
	return strings.TrimSpace(k), strings.TrimSpace(v), nil
}
