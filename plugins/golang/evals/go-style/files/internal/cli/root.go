package cli

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
	Use:   "mycli",
	Short: "mycli manages demo resources.",
}

// Root exposes the root command for main and doc generators.
func Root() *cobra.Command { return rootCmd }
