package spec

import "strings"

// ModelSpec renders the default model names as a comma-separated spec string.
func ModelSpec(defaults []string) string {
	spec := ""
	for i, d := range defaults {
		if i > 0 {
			spec += ","
		}
		spec += d
	}
	return spec
}

// WriteComment writes each line into b as a comment line with the given prefix.
func WriteComment(b *strings.Builder, prefix string, lines []string) {
	for _, l := range lines {
		b.WriteString(prefix + l + "\n")
	}
}

// LongestWord returns the longest whitespace-separated word in s.
func LongestWord(s string) string {
	longest := ""
	for _, w := range strings.Fields(s) {
		if len(w) > len(longest) {
			longest = w
		}
	}
	return longest
}

// HasDefault reports whether name is one of the default model names.
func HasDefault(defaults []string, name string) bool {
	for _, d := range defaults {
		if d == name {
			return true
		}
	}
	return false
}
