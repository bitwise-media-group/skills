package main

import (
	"os"

	"example.com/clidemo/internal/cli"
)

func main() {
	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
