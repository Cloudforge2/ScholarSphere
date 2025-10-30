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
	"github.com/Cloudforge2/scrappy/internal/domain"
	"github.com/Cloudforge2/scrappy/internal/openalex"
	"github.com/Cloudforge2/scrappy/internal/semanticscholar"
	"github.com/Cloudforge2/scrappy/internal/storage"
)

// APIHandler holds the dependencies for the API handlers.
type APIHandler struct {
	repo       storage.Repository
	alexClient *openalex.Client
	semClient  *semanticscholar.Client
}

func respondWithJSON(w http.ResponseWriter, code int, payload interface{}) {
	response, _ := json.Marshal(payload)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	w.Write(response)
}

func respondWithError(w http.ResponseWriter, code int, message string) {
	respondWithJSON(w, code, map[string]string{"error": message})
}

// NewAPIHandler creates a new handler with the necessary dependencies.
func NewAPIHandler(repo storage.Repository, alexClient *openalex.Client, semClient *semanticscholar.Client) *APIHandler {
	return &APIHandler{
		repo:       repo,
		alexClient: alexClient,
		semClient:  semClient,
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

	log.Printf("Received request to fetch authors with name: %s", authorName)

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

	// Just return the authors found by their name and ID
	type authorResponse struct {
		ID                   string `json:"id"`
		DisplayName          string `json:"displayName"`
		LastKnownInstitution string `json:"lastKnownInstitution,omitempty"`
		CitedByCount         int    `json:"citedByCount,omitempty"`
		UpdatedDate          string `json:"updatedDate,omitempty"`
		Orcid                string `json:"orcid,omitempty"`
	}

	var resp []authorResponse
	for _, a := range authors {
		var lastInst string
		if len(a.LastKnownInstitutions) > 0 && a.LastKnownInstitutions[0] != nil {
			lastInst = a.LastKnownInstitutions[0].DisplayName
		}
		resp = append(resp, authorResponse{
			ID:                   a.ID,
			DisplayName:          a.DisplayName,
			LastKnownInstitution: lastInst,
			CitedByCount:         a.CitedByCount,
			UpdatedDate:          a.UpdatedDate,
			Orcid:                a.Orcid,
		})
	}

	respondWithJSON(w, http.StatusOK, resp)
}

func (h *APIHandler) FetchAndSaveWorksByAuthorHandler(w http.ResponseWriter, r *http.Request) {
	// 1. Get author ID and fetch the author (same as before)
	authorID := r.URL.Query().Get("id")
	if authorID == "" {
		respondWithError(w, http.StatusBadRequest, "Missing 'id' query parameter")
		return
	}

	log.Printf("Received request to ingest all works for author ID: %s", authorID)
	author, err := h.alexClient.FetchAuthorById(authorID)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to fetch author from OpenAlex: %v", err))
		return
	}

	// 2. Save the author object itself synchronously. This is fast and should be done immediately.
	// We'll use the request's context for this part.
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	if err := h.repo.SaveAuthor(ctx, author); err != nil {
		respondWithError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to save author to database: %v", err))
		return
	}
	log.Printf("Successfully saved author: %s (ID: %s)", author.DisplayName, author.ID)

	// 3. Fetch ALL works for the author (same as before)
	works, err := h.alexClient.FetchAllWorksByAuthorID(authorID)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to fetch works from OpenAlex: %v", err))
		return
	}
	if len(works) == 0 {
		respondWithJSON(w, http.StatusOK, map[string]interface{}{"message": "Author has no works."})
		return
	}

	// --- NEW ASYNCHRONOUS LOGIC STARTS HERE ---

	const initialBatchSize = 30
	var initialWorks []domain.Work
	var backgroundWorks []domain.Work

	// 4. Split the works into an initial batch and a background batch.
	if len(works) > initialBatchSize {
		initialWorks = works[:initialBatchSize]
		backgroundWorks = works[initialBatchSize:]
	} else {
		initialWorks = works
		// backgroundWorks will be empty
	}

	// 5. Process the initial batch synchronously.
	var savedCount int
	for _, work := range initialWorks {
		if err := h.repo.SaveWork(ctx, work); err != nil {
			log.Printf("WARN: Could not save initial work %s: %v\n", work.Title, err)
			continue
		}
		savedCount++
	}
	log.Printf("Synchronously saved initial batch of %d works for author %s.", savedCount, authorID)

	// 6. Launch a goroutine to process the rest of the works in the background.
	if len(backgroundWorks) > 0 {
		log.Printf("Launching background task to save remaining %d works.", len(backgroundWorks))

		go func() {
			// IMPORTANT: We must create a new, independent context for the background task.
			// The original request's context (r.Context()) will be cancelled as soon as
			// this handler returns a response.
			backgroundCtx := context.Background()

			for _, work := range backgroundWorks {
				// Use a reasonable timeout per work in the background.
				workCtx, workCancel := context.WithTimeout(backgroundCtx, 30*time.Second)

				if err := h.repo.SaveWork(workCtx, work); err != nil {
					log.Printf("BACKGROUND ERROR: Could not save work %s: %v\n", work.Title, err)
				} else {
					log.Printf("BACKGROUND SUCCESS: Saved work: %s", work.Title)
				}

				workCancel() // Clean up the context for this single work
			}
			log.Printf("Background task finished for author %s. All %d works processed.", authorID, len(works))
		}()
	}

	// 7. Immediately respond to the user with a "202 Accepted" status.
	// This tells them the process has started successfully.
	responsePayload := map[string]interface{}{
		"message":          "Request accepted. Initial works are being processed. The rest will be ingested in the background.",
		"totalWorks":       len(works),
		"initialBatchSize": savedCount,
	}
	respondWithJSON(w, http.StatusAccepted, responsePayload)
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

// func (h *APIHandler) GetAuthorWorksByIdHandler(w http.ResponseWriter, r *http.Request) {
// 	// Path should be registered as /api/authors/{author_id}/works
// 	authorID := r.URL.Query().Get("id")
// 	if authorID == "" {
// 		http.Error(w, "Missing 'id' query parameter", http.StatusBadRequest)
// 		return
// 	}
// 	additionalFilters := r.URL.Query().Get("filters")
// 	pageNsort := r.URL.Query().Get("filters")

// 	log.Printf("Request received: Fetch recent works for author ID %s", authorID)
// 	// The Python script defaults to 30 results. We can make this a query param later if needed.
// 	works, err := h.alexClient.FetchWorksByAuthorID(authorID, additionalFilters, pageNsort)
// 	if err != nil {
// 		respondWithError(w, http.StatusInternalServerError, err.Error())
// 		return
// 	}

// 	respondWithJSON(w, http.StatusOK, works)
// }

func (h *APIHandler) GetAuthorWorksHandler(w http.ResponseWriter, r *http.Request) {
	// Path should be registered as /api/authors/{author_id}/works
	authorID := r.URL.Query().Get("id")
	if authorID == "" {
		http.Error(w, "Missing 'id' query parameter", http.StatusBadRequest)
		return
	}

	log.Printf("Request received: Fetch recent works for author ID %s", authorID)
	// The Python script defaults to 30 results. We can make this a query param later if needed.
	works, err := h.alexClient.FetchRecentWorksByAuthorID(authorID, 30)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondWithJSON(w, http.StatusOK, works)
}

type fetchAbstractsRequest struct {
	DOIs []string `json:"dois"`
}

func (h *APIHandler) FetchAbstractsHandler(w http.ResponseWriter, r *http.Request) {
	// Path should be registered as /api/authors/{author_id}/works
	authorID := r.URL.Query().Get("id")
	if authorID == "" {
		http.Error(w, "Missing 'id' query parameter", http.StatusBadRequest)
		return
	}
	// var reqPayload fetchAbstractsRequest
	// if err := json.NewDecoder(r.Body).Decode(&reqPayload); err != nil {
	// 	respondWithError(w, http.StatusBadRequest, "Invalid request payload")
	// 	return
	// }
	// //  Basic validation: ensure some DOIs were provided
	// if len(reqPayload.DOIs) == 0 {
	// 	respondWithError(w, http.StatusBadRequest, "Request must contain a 'dois' array")
	// 	return
	// }

	abstracts, err := h.alexClient.FetchAbstractByAuthorID(authorID, 30)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, err.Error())
		return
	}

	// abstracts, err := h.semClient.FetchAbstracts(reqPayload.DOIs)
	// if err != nil {
	// 	respondWithError(w, http.StatusInternalServerError, err.Error())
	// 	return
	// }

	respondWithJSON(w, http.StatusOK, abstracts)
}
