package ai

import (
	"fmt"
	"net/http"
	"time"
)

// ComfyUIClient connects to a local ComfyUI instance for AI image generation.
// This is optional — the system falls back to Openverse when ComfyUI is unavailable.
type ComfyUIClient struct {
	baseURL    string
	httpClient *http.Client
}

// NewComfyUIClient creates a client. If baseURL is empty, the client is
// considered unavailable and all calls return ErrNotAvailable.
func NewComfyUIClient(baseURL string) *ComfyUIClient {
	if baseURL == "" {
		baseURL = "http://localhost:8188"
	}
	return &ComfyUIClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: 5 * time.Second},
	}
}

// ErrNotAvailable is returned when ComfyUI is not running.
var ErrNotAvailable = fmt.Errorf("comfyui not available")

// IsAvailable checks if ComfyUI is reachable.
func (c *ComfyUIClient) IsAvailable() bool {
	resp, err := c.httpClient.Get(c.baseURL + "/")
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// GenerateConcept generates a concept image for a verse.
// Returns the local file path on success.
func (c *ComfyUIClient) GenerateConcept(verseID, text string) (string, error) {
	return "", ErrNotAvailable
}

// GenerateComposite generates a composited image for a palace locus.
func (c *ComfyUIClient) GenerateComposite(verseID string, palaceID, locusID int64, palacePhotoPath string) (string, error) {
	return "", ErrNotAvailable
}
