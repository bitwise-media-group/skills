// Command myapp — replace this comment with one sentence on what the program does.
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	if err := run(ctx, log, os.Args[1:]); err != nil {
		log.LogAttrs(ctx, slog.LevelError, "fatal", slog.Any("error", err))
		os.Exit(1)
	}
}

// run owns the program lifecycle: parse configuration, wire dependencies, and
// serve until ctx is cancelled. Everything testable lives here or in internal/
// packages — main is the only place allowed to call os.Exit.
func run(ctx context.Context, log *slog.Logger, args []string) error {
	_ = args // parse flags into a Config here (precedence: flag > env > default)

	log.LogAttrs(ctx, slog.LevelInfo, "starting")
	<-ctx.Done()
	log.LogAttrs(ctx, slog.LevelInfo, "shutting down")
	return nil
}
