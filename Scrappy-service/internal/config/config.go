// in internal/config/config.go (assuming you have a file like this)

package config

import "os"

// Config stores all configuration for the application.
type Config struct {
	Neo4jURI      string
	Neo4jUsername string
	Neo4jPassword string
}

// LoadConfig reads configuration from environment variables.
func LoadConfig() *Config {
	return &Config{
		Neo4jURI:      getEnv("NEO4J_URI", "bolt://neo4j-scrappy:7687"),
		Neo4jUsername: getEnv("NEO4J_USERNAME", "neo4j"),
		Neo4jPassword: getEnv("NEO4J_PASSWORD", "test123!"),
	}
}

// Helper function to get an environment variable or return a default.
func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}