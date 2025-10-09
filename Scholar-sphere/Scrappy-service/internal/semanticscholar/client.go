package semanticscholar

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const semanticScholarAPIBaseURL = "https://api.semanticscholar.org/graph/v1"

// RequestBody defines the structure for the JSON we will send.
type RequestBody struct {
	IDs []string `json:"ids"`
}

// ExternalIDs matches the nested JSON object from the API.
type ExternalIDs struct {
	DOI string `json:"DOI"`
}

// PaperResponse matches the structure of a single paper object in the API response.
type PaperResponse struct {
	PaperID     string      `json:"paperId"`
	Title       string      `json:"title"`
	ExternalIDs ExternalIDs `json:"externalIds"`
	Abstract    string      `json:"abstract"`
}

// Client is a client for interacting with the Semantic Scholar API.
type Client struct {
	httpClient *http.Client
	apiKey     string
}

// NewClient creates a new API client.
func NewClient(apiKey string) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: 20 * time.Second},
		apiKey:     apiKey,
	}
}

// FetchPaperDetails fetches details for a batch of papers using their DOIs.
// Note: Renamed from FetchAbstracts for clarity.
func (c *Client) FetchAbstracts(dois []string) ([]*PaperResponse, error) { // Note the return type is a slice of pointers

	requestURL := fmt.Sprintf("%s/paper/batch", semanticScholarAPIBaseURL)

	// We can build the request body from the function arguments for more flexibility
	requestData := RequestBody{IDs: dois}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		// Return an error instead of crashing the program
		return nil, fmt.Errorf("failed to marshal request data: %w", err)
	}

	// Create the POST request
	req, err := http.NewRequest("POST", requestURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create http request: %w", err)
	}

	// Add query parameters and headers
	q := req.URL.Query()
	q.Add("fields", "title,externalIds,abstract") // You could also request 'abstract' here if needed
	req.URL.RawQuery = q.Encode()
	req.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		req.Header.Set("x-api-key", c.apiKey)
	}
	// Use the client from the struct for connection reuse and consistency
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("api request failed with status code %d: %s", resp.StatusCode, string(bodyBytes))
	}

	// Decode into a slice of POINTERS to correctly handle 'null' responses
	var papers []*PaperResponse
	if err := json.NewDecoder(resp.Body).Decode(&papers); err != nil {
		return nil, fmt.Errorf("failed to decode json response: %w", err)
	}

	// The function's responsibility is to return data, not print it.
	// The caller (e.g., your main function) can decide to print the results.
	return papers, nil
}
