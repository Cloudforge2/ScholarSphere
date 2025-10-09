// in cmd/main.go

package main

import (
	"context"
	"log"
	"net/http"

	// Make sure your import paths are correct for your project
	"github.com/Cloudforge2/scrappy/internal/api"
	"github.com/Cloudforge2/scrappy/internal/config"
	"github.com/Cloudforge2/scrappy/internal/openalex"
	"github.com/Cloudforge2/scrappy/internal/semanticscholar"
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

	// 1. Initialize the Neo4j Repository (the database connection)
	dbRepo, err := storage.NewNeo4jRepository(cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	if err != nil {
		log.Fatalf("FATAL: Could not connect to database: %v", err)
	}
	// In a real server, you'd handle graceful shutdown, but for now this is fine.
	defer dbRepo.Close(context.Background())

	// 2. Initialize the OpenAlex Client (for fetching data)
	alexClient := openalex.NewClient()
	semClient := semanticscholar.NewClient(cfg.SemanticScholarAPIKey)

	// 3. Initialize the API Handler, giving it the database and the client
	apiHandler := api.NewAPIHandler(dbRepo, alexClient, semClient)

	// 4. Set up the URL routes and connect them to your handler functions
	mux := http.NewServeMux()
	mux.HandleFunc("/api/fetch-authors-by-name", apiHandler.FetchAndSaveAuthorByNameHandler)
	mux.HandleFunc("/api/fetch-author-by-id", apiHandler.FetchAndSaveWorksByAuthorHandler)
	mux.HandleFunc("/api/fetch-works-by-name", apiHandler.FetchAndSaveWorkByNameHandler)
	// kc
	// mux.HandleFunc("/api/fetch-work-authorid/", apiHandler.GetAuthorWorksByIdHandler)
	mux.HandleFunc("/api/fetch-recent-works/", apiHandler.GetAuthorWorksHandler)
	mux.HandleFunc("/api/fetch-abstracts/", apiHandler.FetchAbstractsHandler)
	// 5. Start the web server and listen for requests
	port := ":8083"
	log.Printf("Starting interactive API server on http://localhost%s", port)
	if err := http.ListenAndServe(port, mux); err != nil {
		log.Fatalf("FATAL: Could not start server: %v", err)
	}

}
