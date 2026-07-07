package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/dillon/scriptureengine/go-srs/internal/db"
	"github.com/dillon/scriptureengine/go-srs/internal/fsrs"
)



// Handler holds dependencies for HTTP handlers.
type Handler struct {
	DB     *db.DB
	Params fsrs.FSRSParams
}

// New creates a new Handler.
func New(database *db.DB) *Handler {
	return &Handler{
		DB:     database,
		Params: fsrs.DefaultParams,
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
	parts := strings.Split(r.URL.Path, "/")
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing card_id")
		return
	}
	cardID, err := strconv.ParseInt(parts[len(parts)-1], 10, 64)
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

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":           true,
		"next_state":   nextCard,
		"xp_awarded":   10,
		"streak_days":  streak,
	})
}

// ── Cards by Verse ──

func (h *Handler) GetCardsByVerse(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	// /api/memorize/verses/{ref}/cards
	if len(parts) < 6 {
		errorResponse(w, http.StatusBadRequest, "missing verse reference")
		return
	}
	verseID := parts[len(parts)-2]

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

// RegisterRoutes sets up all HTTP routes on the given mux.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/api/memorize/verses/batch", h.SyncVerses)
	mux.HandleFunc("/api/memorize/queue", h.GetQueue)
	mux.HandleFunc("/api/memorize/review/", h.ReviewCard)
	mux.HandleFunc("/api/memorize/verses/", h.GetCardsByVerse)
	mux.HandleFunc("/api/memorize/cards", h.CreateCard)
	mux.HandleFunc("/api/memorize/stats", h.GetStats)
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
