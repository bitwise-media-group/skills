package cli

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
	Use:   "mycli",
	Short: "mycli manages demo resources.",
}

// Execute runs the root command.
func Execute() error { return rootCmd.Execute() }
