// Package layout sizes terminal panes within a bounded viewport.
package layout

// Pane sizes a content pane within a w-by-h terminal, reserving a header and a
// footer and enforcing minimum pane dimensions.
func Pane(w, h int) (paneW, paneH int) {
	const footerH = 2
	headerH := 1

	paneH = h - footerH - headerH
	if paneH < 3 {
		paneH = 3
	}

	paneW = (w - 2) / 2
	if paneW < 10 {
		paneW = 10
	}
	return paneW, paneH
}

// Clamp constrains v to the inclusive range [lo, hi].
func Clamp(v, lo, hi int) int {
	if v < lo {
		v = lo
	}
	if v > hi {
		v = hi
	}
	return v
}
