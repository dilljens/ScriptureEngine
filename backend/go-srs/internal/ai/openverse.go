package ai

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// OpenverseImage represents a search result from Openverse.
type OpenverseImage struct {
	Title       string `json:"title"`
	URL         string `json:"url"`
	Thumbnail   string `json:"thumbnail"`
	License     string `json:"license"`
	Creator     string `json:"creator"`
	CreatorURL  string `json:"creator_url"`
}

// openverseResponse is the API response structure.
type openverseResponse struct {
	Results []struct {
		Title       string `json:"title"`
		URL         string `json:"url"`
		Thumbnail   string `json:"thumbnail"`
		License     string `json:"license"`
		Creator     string `json:"creator"`
		CreatorURL  string `json:"creator_url"`
	} `json:"results"`
}

const (
	openverseAPI = "https://api.openverse.engineering/v1/images/"
	imageDir     = "data/images/concept"
	httpTimeout  = 10 * time.Second
)

// OpenverseClient searches for free Bible-related images.
type OpenverseClient struct {
	client  *http.Client
	imageDB ImageStore
}

// ImageStore is the interface for saving image metadata.
type ImageStore interface {
	SaveConceptImage(verseID, filePath, source string) (int64, error)
	GetConceptImage(verseID string) (path string, err error)
}

// NewOpenverseClient creates a new client.
func NewOpenverseClient(store ImageStore) *OpenverseClient {
	return &OpenverseClient{
		client: &http.Client{Timeout: httpTimeout},
		imageDB: store,
	}
}

// Search queries Openverse for an image matching the verse.
func (c *OpenverseClient) Search(verseID, query string) (*OpenverseImage, error) {
	// Build URL
	params := url.Values{}
	params.Set("q", query)
	params.Set("page_size", "5")
	// Don't filter by license — Openverse returns CC-licensed by default

	reqURL := openverseAPI + "?" + params.Encode()

	req, err := http.NewRequest("GET", reqURL, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("User-Agent", "ScriptureEngine/1.0 (memorization module)")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("openverse request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("openverse status %d: %s", resp.StatusCode, string(body[:min(len(body), 200)]))
	}

	var apiResp openverseResponse
	if err := json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	if len(apiResp.Results) == 0 {
		return nil, fmt.Errorf("no results for query: %s", query)
	}

	// Return first result
	r := apiResp.Results[0]
	return &OpenverseImage{
		Title:      r.Title,
		URL:        r.URL,
		Thumbnail:  r.Thumbnail,
		License:    r.License,
		Creator:    r.Creator,
		CreatorURL: r.CreatorURL,
	}, nil
}

// Download fetches an image and saves it locally, returning the local path.
func (c *OpenverseClient) Download(img *OpenverseImage, verseID string) (string, error) {
	// Create directory
	if err := os.MkdirAll(imageDir, 0755); err != nil {
		return "", fmt.Errorf("create image dir: %w", err)
	}

	// Determine extension from URL
	ext := ".jpg"
	if strings.Contains(img.URL, ".png") {
		ext = ".png"
	} else if strings.Contains(img.URL, ".svg") {
		ext = ".svg"
	}

	localPath := filepath.Join(imageDir, verseID+ext)

	// Download image
	resp, err := c.client.Get(img.URL)
	if err != nil {
		return "", fmt.Errorf("download image: %w", err)
	}
	defer resp.Body.Close()

	f, err := os.Create(localPath)
	if err != nil {
		return "", fmt.Errorf("create file: %w", err)
	}
	defer f.Close()

	if _, err := io.Copy(f, resp.Body); err != nil {
		return "", fmt.Errorf("write image: %w", err)
	}

	return localPath, nil
}

// EnsureConceptImage checks for an existing image, or searches + downloads one.
func (c *OpenverseClient) EnsureConceptImage(verseID, verseText, reference string) (string, error) {
	// Check if image already exists
	if path, err := c.imageDB.GetConceptImage(verseID); err == nil && path != "" {
		return path, nil
	}

	// Build search query
	query := BuildSearchQuery(verseText, reference)

	// Search Openverse
	img, err := c.Search(verseID, query)
	if err != nil {
		return "", fmt.Errorf("search failed: %w", err)
	}

	// Download
	path, err := c.Download(img, verseID)
	if err != nil {
		return "", fmt.Errorf("download failed: %w", err)
	}

	// Save to DB
	if _, err := c.imageDB.SaveConceptImage(verseID, path, "openverse"); err != nil {
		return "", fmt.Errorf("save metadata: %w", err)
	}

	return path, nil
}
