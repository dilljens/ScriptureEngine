package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/dillon/scriptureengine/go-srs/internal/ai"
	"github.com/dillon/scriptureengine/go-srs/internal/db"
	"github.com/dillon/scriptureengine/go-srs/internal/fire"
	"github.com/dillon/scriptureengine/go-srs/internal/fsrs"
)



// Handler holds dependencies for HTTP handlers.
type Handler struct {
	DB            *db.DB
	Params        fsrs.FSRSParams
	Openverse     *ai.OpenverseClient
	ComfyUI       *ai.ComfyUIClient
	Fire          *fire.Engine
}

// New creates a new Handler.
func New(database *db.DB) *Handler {
	return &Handler{
		DB:        database,
		Params:    fsrs.DefaultParams,
		Openverse: ai.NewOpenverseClient(database),
		ComfyUI:   ai.NewComfyUIClient(""),
		Fire:      fire.New(),
	}
}

// jsonResponse writes a JSON response.
func jsonResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

// errorResponse writes a JSON error.
func errorResponse(w http.ResponseWriter, status int, msg string) {
	jsonResponse(w, status, map[string]string{"error": msg})
}

// ── Health ──

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	count, _ := h.DB.VerseCount()
	dueCount, _ := h.DB.GetDueCount()
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"status":     "ok",
		"verses":     count,
		"due_cards":  dueCount,
	})
}

// ── Verse Sync ──

func (h *Handler) SyncVerses(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Verses []struct {
			ID        string `json:"id"`
			Book      string `json:"book"`
			Chapter   int    `json:"chapter"`
			Verse     int    `json:"verse"`
			Text      string `json:"text"`
			Reference string `json:"reference"`
			Language  string `json:"language"`
		} `json:"verses"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	rows := make([]db.VerseRow, len(input.Verses))
	for i, v := range input.Verses {
		lang := v.Language
		if lang == "" {
			lang = "english"
		}
		rows[i] = db.VerseRow{
			ID:        v.ID,
			Book:      v.Book,
			Chapter:   v.Chapter,
			Verse:     v.Verse,
			Text:      v.Text,
			Reference: v.Reference,
			Language:  lang,
		}
	}

	if err := h.DB.SyncVerses(rows); err != nil {
		errorResponse(w, http.StatusInternalServerError, "sync failed: "+err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":     true,
		"synced": len(input.Verses),
	})
}

// ── Queue ──

func (h *Handler) GetQueue(w http.ResponseWriter, r *http.Request) {
	limitStr := r.URL.Query().Get("limit")
	limit := 20
	if limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 {
			limit = l
		}
	}

	items, err := h.DB.GetDueCards(limit)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"count": len(items),
		"cards": items,
	})
}

// ── Review ──

func (h *Handler) ReviewCard(w http.ResponseWriter, r *http.Request) {
	// Extract card ID from path: /api/memorize/review/{card_id}
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 4 {
		errorResponse(w, http.StatusBadRequest, "missing card_id")
		return
	}
	cardID, err := strconv.ParseInt(parts[3], 10, 64)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid card_id")
		return
	}

	var input struct {
		Rating int `json:"rating"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if input.Rating < 1 || input.Rating > 4 {
		errorResponse(w, http.StatusBadRequest, "rating must be 1-4")
		return
	}

	nextCard, err := h.DB.ReviewCard(cardID, fsrs.Rating(input.Rating), h.Params)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	// Award XP
	streak, _ := h.DB.AwardXP(10) // base XP per review

	// Compute FIRe boosts for connected verses
	var fireBoosts []fire.Boost
	var fireApplied int
	verseID := ""
	if len(parts) >= 4 {
		// Get the verse ID for the card being reviewed
		var vID string
		h.DB.ScanCardVerse(cardID, &vID)
		verseID = vID
	}
	if verseID != "" && input.Rating >= 3 {
		fireBoosts, _ = h.Fire.ComputeBoosts(
			verseID,
			input.Rating,
			h.DB.GetConnections,
			h.DB.HasCard,
		)
		fireApplied, _ = h.DB.ApplyFIREBoosts(fireBoosts)
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":           true,
		"next_state":   nextCard,
		"xp_awarded":   10,
		"streak_days":  streak,
		"fire_boosts":  fireApplied,
		"fire_verses":  len(fireBoosts),
	})
}

// ── Cards by Verse ──

func (h *Handler) GetCardsByVerse(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	// /api/memorize/verses/{ref}/cards
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing verse reference")
		return
	}
	verseID := parts[3]

	cards, err := h.DB.GetCardsByVerse(verseID)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"count": len(cards),
		"cards": cards,
	})
}

// ── Stats ──

func (h *Handler) GetStats(w http.ResponseWriter, r *http.Request) {
	stats, err := h.DB.GetStats()
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"stats": stats,
	})
}

// ── Create Card ──

func (h *Handler) CreateCard(w http.ResponseWriter, r *http.Request) {
	var input struct {
		VerseID  string `json:"verse_id"`
		CardType string `json:"card_type"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if input.CardType == "" {
		input.CardType = "text"
	}

	cardID, err := h.DB.EnsureCard(input.VerseID, input.CardType)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":      true,
		"card_id": cardID,
	})
}

// ── Connection Sync (for FIRe) ──

func (h *Handler) SyncConnections(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Connections []struct {
			Source string `json:"source"`
			Target string `json:"target"`
			Type   string `json:"type"`
		} `json:"connections"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	rows := make([]db.ConnectionRow, len(input.Connections))
	for i, c := range input.Connections {
		rows[i] = db.ConnectionRow{
			SourceVerse: c.Source,
			TargetVerse: c.Target,
			ConnType:    c.Type,
		}
	}

	if err := h.DB.SyncConnections(rows); err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"synced": len(rows),
	})
}

// ── Palace Operations ──

// HandlePalaces dispatches based on path and method.
//   GET  /api/memorize/palaces         — list
//   POST /api/memorize/palaces         — create
//   GET  /api/memorize/palaces/:id     — get with loci
//   POST /api/memorize/palaces/:id/loci — add locus
func (h *Handler) HandlePalaces(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	// parts[0]=api, parts[1]=memorize, parts[2]=palaces, parts[3]=id (optional), parts[4]=loci (optional)

	if len(parts) >= 4 && parts[3] != "" {
		// /api/memorize/palaces/:id or /api/memorize/palaces/:id/loci
		if len(parts) >= 5 && parts[4] == "loci" {
			if r.Method == "POST" {
				h.AddLocus(w, r)
			} else {
				errorResponse(w, http.StatusMethodNotAllowed, "use POST to add locus")
			}
			return
		}
		if r.Method == "GET" {
			h.GetPalace(w, r)
		} else {
			errorResponse(w, http.StatusMethodNotAllowed, "use GET for palace details")
		}
		return
	}

	// /api/memorize/palaces (no id)
	switch r.Method {
	case "GET":
		h.ListPalaces(w, r)
	case "POST":
		h.CreatePalace(w, r)
	default:
		errorResponse(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// HandleLoci dispatches to add locus (POST /api/memorize/palaces/:id/loci)
// or assign verse (POST /api/memorize/loci/:id/assign).
func (h *Handler) HandleLoci(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		errorResponse(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	// Determine if this is /palaces/:id/loci or /loci/:id/assign
	if strings.Contains(r.URL.Path, "/palaces/") {
		h.AddLocus(w, r)
	} else {
		h.AssignVerse(w, r)
	}
}

func (h *Handler) CreatePalace(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Name      string `json:"name"`
		PhotoPath string `json:"photo_path"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	id, err := h.DB.CreatePalace(input.Name, input.PhotoPath)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true, "palace_id": id})
}

func (h *Handler) ListPalaces(w http.ResponseWriter, r *http.Request) {
	palaces, err := h.DB.ListPalaces()
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true, "palaces": palaces})
}

func (h *Handler) GetPalace(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 4 {
		errorResponse(w, http.StatusBadRequest, "missing palace_id")
		return
	}
	palaceID, err := strconv.ParseInt(parts[3], 10, 64)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid palace_id")
		return
	}

	palace, loci, err := h.DB.GetPalaceWithLoci(palaceID)
	if err != nil {
		errorResponse(w, http.StatusNotFound, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":     true,
		"palace": palace,
		"loci":   loci,
	})
}

func (h *Handler) AddLocus(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 4 {
		errorResponse(w, http.StatusBadRequest, "missing palace_id")
		return
	}
	palaceID, err := strconv.ParseInt(parts[3], 10, 64)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid palace_id")
		return
	}

	var input struct {
		Label string  `json:"label"`
		X     float64 `json:"x_pct"`
		Y     float64 `json:"y_pct"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	locusID, err := h.DB.AddLocus(palaceID, input.Label, input.X, input.Y)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true, "locus_id": locusID})
}

func (h *Handler) AssignVerse(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 4 {
		errorResponse(w, http.StatusBadRequest, "missing locus_id")
		return
	}
	locusID, err := strconv.ParseInt(parts[3], 10, 64)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid locus_id")
		return
	}

	var input struct {
		VerseID string `json:"verse_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if err := h.DB.AssignVerseToLocus(locusID, input.VerseID); err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true})
}

func (h *Handler) UploadPalacePhoto(w http.ResponseWriter, r *http.Request) {
	file, header, err := r.FormFile("file")
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "file required")
		return
	}
	defer file.Close()

	dir := "data/images/palaces"
	os.MkdirAll(dir, 0755)
	ext := filepath.Ext(header.Filename)
	localPath := filepath.Join(dir, "palace_"+fmt.Sprint(time.Now().Unix())+ext)

	dst, err := os.Create(localPath)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "save failed")
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		errorResponse(w, http.StatusInternalServerError, "write failed")
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":   true,
		"path": localPath,
	})
}

// ── Image Generation ──

func (h *Handler) GenerateConcept(w http.ResponseWriter, r *http.Request) {
	var input struct {
		VerseID   string `json:"verse_id"`
		VerseText string `json:"verse_text"`
		Reference string `json:"reference"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	// Auto-select source: Openverse (always works)
	path, err := h.Openverse.EnsureConceptImage(input.VerseID, input.VerseText, input.Reference)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "no image available: "+err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":       true,
		"verse_id": input.VerseID,
		"path":     path,
	})
}

// ServeImage serves a concept image file.
func (h *Handler) ServeImage(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	// /api/memorize/images/{verse_id}
	if len(parts) < 4 {
		errorResponse(w, http.StatusBadRequest, "missing verse_id")
		return
	}
	verseID := parts[3]

	path, err := h.DB.GetConceptImage(verseID)
	if err != nil {
		errorResponse(w, http.StatusNotFound, "no image for verse")
		return
	}

	// Determine content type
	ext := filepath.Ext(path)
	contentTypes := map[string]string{
		".jpg":  "image/jpeg",
		".jpeg": "image/jpeg",
		".png":  "image/png",
		".svg":  "image/svg+xml",
		".webp": "image/webp",
	}
	ct := contentTypes[ext]
	if ct == "" {
		ct = "application/octet-stream"
	}

	w.Header().Set("Content-Type", ct)
	http.ServeFile(w, r, path)
}

// UploadImage handles multipart image upload.
func (h *Handler) UploadImage(w http.ResponseWriter, r *http.Request) {
	verseID := r.FormValue("verse_id")
	if verseID == "" {
		errorResponse(w, http.StatusBadRequest, "verse_id required")
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "file required: "+err.Error())
		return
	}
	defer file.Close()

	dir := "data/images/concept"
	os.MkdirAll(dir, 0755)
	ext := filepath.Ext(header.Filename)
	localPath := filepath.Join(dir, verseID+ext)

	dst, err := os.Create(localPath)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "save failed")
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		errorResponse(w, http.StatusInternalServerError, "write failed")
		return
	}

	h.DB.SaveConceptImage(verseID, localPath, "upload")

	fmt.Fprintf(w, `{"ok":true,"verse_id":"%s","path":"%s"}`, verseID, localPath)
}

// RegisterRoutes sets up all HTTP routes on the given mux.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/api/memorize/verses/batch", h.SyncVerses)
	mux.HandleFunc("/api/memorize/queue", h.GetQueue)
	mux.HandleFunc("/api/memorize/review/", h.ReviewCard)
	mux.HandleFunc("/api/memorize/verses/", h.GetCardsByVerse)
	mux.HandleFunc("/api/memorize/cards", h.CreateCard)
	mux.HandleFunc("/api/memorize/stats", h.GetStats)
	mux.HandleFunc("/api/memorize/connections/batch", h.SyncConnections)
	mux.HandleFunc("/api/memorize/palaces/upload", h.UploadPalacePhoto)
	mux.HandleFunc("/api/memorize/palaces/", h.HandlePalaces)
	mux.HandleFunc("/api/memorize/palaces", h.HandlePalaces)
	mux.HandleFunc("/api/memorize/loci/", h.HandleLoci)
	mux.HandleFunc("/api/memorize/generate/concept", h.GenerateConcept)
	mux.HandleFunc("/api/memorize/images/", h.ServeImage)
	mux.HandleFunc("/api/memorize/upload", h.UploadImage)
}

// ── CORS Middleware ──

func CORSMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// LoggingMiddleware logs requests.
func LoggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
