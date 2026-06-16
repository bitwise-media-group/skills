// Package clamp provides bounded integer helpers.
package clamp

// Clamp limits v to the inclusive range [lo, hi].
func Clamp(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}
