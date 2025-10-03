package openalex

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"time"

	"github.com/Cloudforge2/scrappy/internal/domain" // IMPORTANT: Adjust this import path
)

const openAlexAPIBaseURL = "https://api.openalex.org"

// Client is a client for interacting with the OpenAlex API.
type Client struct {
	httpClient *http.Client
	// politeMail string
}

// NewClient creates a new OpenAlex API client.
// The politeMail address is used for the "polite pool" for better performance.
func NewClient() *Client {
	return &Client{
		httpClient: &http.Client{Timeout: 20 * time.Second}, // Increased timeout for potentially large API responses
		// politeMail: politeMail,
	}
}

// FetchAuthor fetches a single, full author entity by their OpenAlex ID.
// This is an example of fetching a SINGLE entity.
func (c *Client) FetchAuthor(authorID string) (*domain.Author, error) {
	// Example URL: https://api.openalex.org/authors/A12345?mailto=...
	url := fmt.Sprintf("%s/authors/%s?mailto=%s", openAlexAPIBaseURL, authorID)

	var author domain.Author
	err := c.fetchAndDecode(url, &author)
	if err != nil {
		return nil, err
	}

	return &author, nil
}

func (c *Client) FetchAuthorsByName(name string) ([]domain.Author, error) {
	// We must URL-encode the name to handle spaces and special characters.
	encodedName := url.QueryEscape(name)

	// URL will look like: https://api.openalex.org/authors?search=marie%20curie&mailto=...
	requestURL := fmt.Sprintf("%s/authors?search=%s&mailto=%s", openAlexAPIBaseURL, encodedName)

	// The API response for a search is a paginated list, just like for filters.
	var apiResponse struct {
		Results []domain.Author `json:"results"`
	}

	// We can reuse our generic helper function!
	err := c.fetchAndDecode(requestURL, &apiResponse)
	if err != nil {
		return nil, err
	}

	return apiResponse.Results, nil
}

func (c *Client) FetchWorksByName(name string) ([]domain.Work, error) {
	// URL-encode the name to handle spaces and special characters.
	encodedName := url.QueryEscape(name)

	// URL will look like: https://api.openalex.org/works?search=...
	requestURL := fmt.Sprintf("%s/works?search=%s", openAlexAPIBaseURL, encodedName)

	// The API response for a search is a paginated list.
	var apiResponse struct {
		Results []domain.Work `json:"results"`
	}

	// Reuse the generic helper function.
	err := c.fetchAndDecode(requestURL, &apiResponse)
	if err != nil {
		return nil, err
	}

	return apiResponse.Results, nil
}

func (c *Client) FetchWorksByAuthorID(authorID string) ([]domain.Work, error) {
	// The OpenAlex API uses a filter syntax like this:
	// https://api.openalex.org/works?filter=author.id:A2043598041
	requestURL := fmt.Sprintf("%s/works?filter=author.id:%s", openAlexAPIBaseURL, authorID)

	// The API response for a filter is a paginated list, just like for searches.
	var apiResponse struct {
		Results []domain.Work `json:"results"`
	}

	// We can reuse our generic helper function!
	err := c.fetchAndDecode(requestURL, &apiResponse)
	if err != nil {
		return nil, err
	}

	return apiResponse.Results, nil
}

// fetchAndDecode is a generic helper function to perform a GET request
// and decode the JSON response into the target interface{}.
func (c *Client) fetchAndDecode(url string, target interface{}) error {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create new http request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad response from OpenAlex API (%s): %s", url, resp.Status)
	}

	// Decode the JSON from the response body into the 'target'
	// The target is a pointer, so this function modifies the original variable passed in.
	if err := json.NewDecoder(resp.Body).Decode(target); err != nil {
		return fmt.Errorf("failed to decode json response: %w", err)
	}

	return nil
}
