package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"example.com/clidemo/internal/cli"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := cli.Root().ExecuteContext(ctx); err != nil {
		os.Exit(1)
	}
}
