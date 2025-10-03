// in internal/api/handler.go

package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	// Use your actual module paths here
	"github.com/Cloudforge2/scrappy/internal/openalex"
	"github.com/Cloudforge2/scrappy/internal/storage"
)

// APIHandler holds the dependencies for the API handlers.
type APIHandler struct {
	repo       storage.Repository
	alexClient *openalex.Client
}

// NewAPIHandler creates a new handler with the necessary dependencies.
func NewAPIHandler(repo storage.Repository, alexClient *openalex.Client) *APIHandler {
	return &APIHandler{
		repo:       repo,
		alexClient: alexClient,
	}
}

// FetchAndSaveAuthorByNameHandler is an HTTP handler that fetches an author from OpenAlex
// and saves them to the Neo4j database.
func (h *APIHandler) FetchAndSaveAuthorByNameHandler(w http.ResponseWriter, r *http.Request) {
	// 1. Get the author name from the query parameters (e.g., ?name=stephen+hawking)
	authorName := r.URL.Query().Get("name")
	if authorName == "" {
		http.Error(w, "Missing 'name' query parameter", http.StatusBadRequest)
		return
	}

	log.Printf("Received request to fetch and save author: %s", authorName)

	// 2. Use the OpenAlex client to fetch the data
	authors, err := h.alexClient.FetchAuthorsByName(authorName)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to fetch authors from OpenAlex: %v", err), http.StatusInternalServerError)
		return
	}

	if len(authors) == 0 {
		http.Error(w, fmt.Sprintf("No authors found with the name: %s", authorName), http.StatusNotFound)
		return
	}

	// For this example, we'll just process the first author found.
	// In a real app, you might process all of them.
	author := authors[0]

	// 3. Use the repository to save the data
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()
	var savedCount int
	for _, a := range authors {
		if err := h.repo.SaveAuthor(ctx, a); err != nil {
			log.Printf("WARN: Could not save author %s: %v\n", a.DisplayName, err)
			continue
		}
		savedCount++
		log.Printf("Successfully saved author: %s (ID: %s)", a.DisplayName, a.ID)

		// Fetch works for this author and save them
		works, err := h.alexClient.FetchWorksByAuthorID(a.ID)
		if err != nil {
			log.Printf("WARN: Could not fetch works for author %s: %v\n", a.DisplayName, err)
			continue
		}
		for _, work := range works {
			if err := h.repo.SaveWork(ctx, work); err != nil {
				log.Printf("WARN: Could not save work %s: %v\n", work.Title, err)
				continue
			}
			log.Printf("Successfully saved work: %s (ID: %s)", work.Title, work.ID)
		}
	}
	if savedCount == 0 {
		http.Error(w, "Failed to save any authors to database", http.StatusInternalServerError)
		return
	}

	log.Printf("Successfully saved author: %s (ID: %s)", author.DisplayName, author.ID)

	// 4. Send a success response back to the client
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"message":     "Author successfully fetched and saved",
		"id":          author.ID,
		"displayName": author.DisplayName,
	})
}

func (h *APIHandler) FetchAndSaveWorksByAuthorHandler(w http.ResponseWriter, r *http.Request) {
	// 1. Get the author ID from the query parameters (e.g., ?id=A2043598041)
	authorID := r.URL.Query().Get("id")
	if authorID == "" {
		http.Error(w, "Missing 'id' query parameter", http.StatusBadRequest)
		return
	}

	log.Printf("Received request to fetch works for author ID: %s", authorID)

	// 2. Use the OpenAlex client to fetch the data
	works, err := h.alexClient.FetchWorksByAuthorID(authorID)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to fetch works from OpenAlex: %v", err), http.StatusInternalServerError)
		return
	}

	if len(works) == 0 {
		// It's not an error if an author has no works, so we return a success response.
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"message":        "Author has no works, or author not found.",
			"worksProcessed": 0,
		})
		return
	}

	// 3. Loop through all fetched works and save each one to the database.
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second) // Increased timeout for potentially many works
	defer cancel()

	var savedCount int
	for _, work := range works {
		if err := h.repo.SaveWork(ctx, work); err != nil {
			// Log the error but continue trying to save other works
			log.Printf("WARN: Could not save work %s: %v\n", work.Title, err)
			continue
		}
		savedCount++
		log.Printf("Successfully saved work: %s (ID: %s)", work.Title, work.ID)
	}

	log.Printf("Finished processing. Saved %d out of %d works for author %s.", savedCount, len(works), authorID)

	// 4. Send a success response back to the client
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message":        "Successfully fetched and processed works",
		"worksFetched":   len(works),
		"worksProcessed": savedCount,
	})
}

func (h *APIHandler) FetchAndSaveWorkByNameHandler(w http.ResponseWriter, r *http.Request) {
	// 1. Get the work name from the query parameters (e.g., ?name=principia+mathematica)
	workName := r.URL.Query().Get("name")
	if workName == "" {
		http.Error(w, "Missing 'name' query parameter", http.StatusBadRequest)
		return
	}

	log.Printf("Received request to fetch and save work: %s", workName)

	// 2. Use the OpenAlex client to fetch the data
	works, err := h.alexClient.FetchWorksByName(workName)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to fetch works from OpenAlex: %v", err), http.StatusInternalServerError)
		return
	}

	if len(works) == 0 {
		http.Error(w, fmt.Sprintf("No works found with the name: %s", workName), http.StatusNotFound)
		return
	}

	// For this example, we'll just process the first work found.
	work := works[0]

	// 3. Use the repository to save the data.
	// NOTE: The SaveWork function is already designed to also save the author nodes
	// and the AUTHORED relationships, so no extra steps are needed.
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	if err := h.repo.SaveWork(ctx, work); err != nil {
		http.Error(w, fmt.Sprintf("Failed to save work to database: %v", err), http.StatusInternalServerError)
		return
	}

	log.Printf("Successfully saved work: %s (ID: %s)", work.Title, work.ID)

	// 4. Send a success response back to the client
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Work and its authors successfully fetched and saved",
		"id":      work.ID,
		"title":   work.Title,
	})
}
