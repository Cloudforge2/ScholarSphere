package main

import (
	"context"
	"log"
	"net/http"

	"github.com/Cloudforge2/scrappy/internal/api"
	"github.com/Cloudforge2/scrappy/internal/config"
	"github.com/Cloudforge2/scrappy/internal/openalex"
	"github.com/Cloudforge2/scrappy/internal/storage"
	"github.com/joho/godotenv"
)

func main() {
	// Load config from .env file
	err := godotenv.Load()
	if err != nil {
		log.Println("Info: .env file not found, reading from OS environment")
	}
	cfg := config.LoadConfig()

	// Initialize the Neo4j repository using the exported interface type
	dbRepo, err := storage.NewNeo4jRepository(cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	if err != nil {
		log.Fatalf("FATAL: Could not connect to database: %v", err)
	}
	defer dbRepo.Close(context.Background())

	// Initialize the OpenAlex client
	alexClient := openalex.NewClient()

	// Initialize the API handler
	apiHandler := api.NewAPIHandler(dbRepo, alexClient)

	// Set up HTTP routes
	mux := http.NewServeMux()
	mux.HandleFunc("/api/fetch-author", apiHandler.FetchAndSaveAuthorByNameHandler)
	mux.HandleFunc("/api/fetch-works-by-author", apiHandler.FetchAndSaveWorksByAuthorHandler)
	mux.HandleFunc("/api/fetch-work", apiHandler.FetchAndSaveWorkByNameHandler)

	// Start the server
	port := ":8083"
	log.Printf("Starting interactive API server on http://localhost%s", port)
	if err := http.ListenAndServe(port, mux); err != nil {
		log.Fatalf("FATAL: Could not start server: %v", err)
	}
}
