// in cmd/main.go

package main

import (
	"context"
	"log"
	"time"

	"github.com/Cloudforge2/scrappy/internal/config"   // Adjust path
	"github.com/Cloudforge2/scrappy/internal/openalex" // Adjust path
	"github.com/Cloudforge2/scrappy/internal/storage"  // Adjust path
	"github.com/joho/godotenv"
)

func load() {
	err := godotenv.Load()
	if err != nil {
		log.Println("Info: .env file not found, reading from OS environment")
	}

	cfg := config.LoadConfig()

	// 1. Initialize the Neo4j Repository
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	dbRepo, err := storage.NewNeo4jRepository(cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	if err != nil {
		log.Fatalf("FATAL: Could not connect to database: %v", err)
	}
	defer dbRepo.Close(ctx)

	// 2. Initialize the OpenAlex Client
	alexClient := openalex.NewClient()

	// --- EXAMPLE USAGE ---

	// 3. Fetch data from OpenAlex
	log.Println("Fetching authors for 'Yogesh Simmhan'...")
	authors, err := alexClient.FetchAuthorsByName("Yogesh Simmhan")
	if err != nil {
		log.Fatalf("Failed to fetch authors: %v", err)
	}

	// 4. Save the data to Neo4j
	for _, author := range authors {
		log.Printf("Saving author: %s (ID: %s)\n", author.DisplayName, author.ID)
		if err := dbRepo.SaveAuthor(ctx, author); err != nil {
			log.Printf("WARN: Could not save author %s: %v\n", author.DisplayName, err)
		}
	}
	log.Println("Author processing complete.")

	// Example for works
	for _, author := range authors {
		log.Printf("Fetching works for author: %s (ID: %s)...", author.DisplayName, author.ID)
		works, err := alexClient.FetchWorksByAuthorID(author.ID)
		if err != nil {
			log.Printf("WARN: Failed to fetch works for author %s: %v\n", author.DisplayName, err)
			continue
		}
		for _, work := range works {
			log.Printf("Saving work: %s (ID: %s)\n", work.Title, work.ID)
			if err := dbRepo.SaveWork(ctx, work); err != nil {
				log.Printf("WARN: Could not save work %s: %v\n", work.Title, err)
			}
		}
	}
	log.Println("Work processing complete.")

}

// With these changes, your application now has a complete pipeline: it loads configuration, connects to Neo4j, fetches data from the OpenAlex API, and stores that data as a graph. You can now run your `main` function to see it in action.
