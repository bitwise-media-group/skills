package config

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
)

// Config holds the service settings.
type Config struct {
	Addr string `json:"addr"`
}

// Load reads and parses the config file at path.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("Failed to read config: %v", err)
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("Failed to parse config: %v", err)
	}
	log.Printf("loaded config from %s", path)
	return &cfg, nil
}
