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

	items, err := h.DB.GetDueCards(limit * 4) // fetch extra for interleaving pool
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	// Repetition compression: detect groups of connected due cards
	compress := r.URL.Query().Get("compress") != "false"
	hidden := 0
	if compress && len(items) > 1 {
		visible := make([]db.DueCardItem, 0, len(items))
		hiddenIDs := make(map[int64]bool)
		for _, item := range items {
			if hiddenIDs[item.CardID] {
				continue
			}
			// Check if this card has connected cards also due
			connected, err := h.DB.GetConnectedDueCards(item.VerseID, item.CardID)
			if err == nil && len(connected) > 0 {
				item.CompressedWith = make([]int64, 0, len(connected))
				for _, cc := range connected {
					item.CompressedWith = append(item.CompressedWith, cc.CardID)
					hiddenIDs[cc.CardID] = true
					hidden++
				}
			}
			visible = append(visible, item)
		}
		items = visible
	}

	// Interleave: mix verses from different passages
	interleave := r.URL.Query().Get("interleave") != "false"
	if interleave && len(items) > 2 {
		items = interleaveQueue(items, limit)
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"count": len(items),
		"cards": items,
		"hidden": hidden,
	})
}

// interleaveQueue rearranges cards so verses from the same passage
// are spread out — at most 2 consecutive from any passage.
func interleaveQueue(items []db.DueCardItem, limit int) []db.DueCardItem {
	if len(items) <= 2 {
		return items
	}

	// Group by passage (book.chapter)
	type group struct {
		passage string
		cards   []db.DueCardItem
	}
	groups := make(map[string]*group)
	order := []string{}

	for _, item := range items {
		// Extract passage from verse_id, e.g., "gen.1.1" → "gen.1"
		verseID := item.VerseID
		passage := verseID
		if lastDot := strings.LastIndex(verseID, "."); lastDot > 0 {
			passage = verseID[:lastDot]
		}

		if _, ok := groups[passage]; !ok {
			groups[passage] = &group{passage: passage}
			order = append(order, passage)
		}
		groups[passage].cards = append(groups[passage].cards, item)
	}

	// Interleave: take at most 2 from each passage, cycle through
	result := make([]db.DueCardItem, 0, limit)
	maxPerPassage := 2
	round := 0

	for len(result) < limit {
		addedThisRound := 0
		for _, passage := range order {
			g := groups[passage]
			if len(g.cards) == 0 {
				continue
			}
			take := maxPerPassage
			if len(g.cards) < take {
				take = len(g.cards)
			}
			if remaining := limit - len(result); remaining < take {
				take = remaining
			}
			result = append(result, g.cards[:take]...)
			g.cards = g.cards[take:]
			addedThisRound++
		}
		if addedThisRound == 0 {
			break
		}
		round++
	}

	return result
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

	// Compute XP based on hint level and rating
	baseXP := 10 + int(nextCard.HintLevel)*2
	ratingMult := map[int]float64{1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25}
	xp := int(float64(baseXP) * ratingMult[input.Rating])
	streak, _ := h.DB.AwardXP(xp)

	// Update hint level based on rating
	var newHintLevel int
	if nextCard.HintLevel > 0 {
		newHintLevel = nextCard.HintLevel
	} else {
		newHintLevel = 1 // default starting hint level
	}
	switch input.Rating {
	case 1: // Again — decrease hint level
		if newHintLevel > 0 {
			newHintLevel--
		}
	case 2: // Hard — keep same
	case 3, 4: // Good/Easy — increase hint level
		if newHintLevel < 5 {
			newHintLevel++
		}
	}
	if newHintLevel != int(nextCard.HintLevel) {
		h.DB.UpdateHintLevel(cardID, newHintLevel)
		nextCard.HintLevel = newHintLevel
	}

	// Compute FIRe boosts and penalties
	var fireBoosts []fire.Boost
	var fireApplied, firePenalties int
	var remediation []map[string]interface{}
	verseID := ""
	if len(parts) >= 4 {
		var vID string
		h.DB.ScanCardVerse(cardID, &vID)
		verseID = vID
	}
	if verseID != "" {
		if input.Rating >= 3 {
			// Credit flow: successful review boosts connected verses
			fireBoosts, _ = h.Fire.ComputeBoosts(
				verseID, input.Rating, h.DB.GetConnections, h.DB.HasCard,
			)
			fireApplied, _ = h.DB.ApplyFIREBoosts(fireBoosts)
		} else if input.Rating <= 2 {
			// Penalty flow: failed review penalizes connected verses
			penalties, _ := h.Fire.ComputePenalties(
				verseID, input.Rating, h.DB.GetConnections, h.DB.HasCard,
			)
			firePenalties, _ = h.DB.ApplyFIREPenalties(penalties)

			// Targeted remediation: find connected verses the user has studied
			if conns, err := h.DB.GetConnections(verseID); err == nil {
				for _, c := range conns {
					if cardID, exists := h.DB.HasCard(c.TargetVerse); exists {
						var stability float64
						var verseText string
						_ = h.DB.Conn().QueryRow(
							"SELECT c.stability, v.text FROM cards c JOIN verses v ON v.id = c.verse_id WHERE c.id = ?",
							cardID,
						).Scan(&stability, &verseText)
						if stability > 0 {
							remediation = append(remediation, map[string]interface{}{
								"verse_id":   c.TargetVerse,
								"conn_type":  c.Type,
								"conn_weight": fire.ConnectionWeight(c.Type),
								"text":       truncateText(verseText, 80),
							})
						}
					}
				}
			}
		}
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":              true,
		"next_state":      nextCard,
		"xp_awarded":      xp,
		"streak_days":     streak,
		"fire_boosts":     fireApplied,
		"fire_verses":     len(fireBoosts),
		"fire_penalties":  firePenalties,
		"remediation":     remediation,
	})
}

// ReviewBatch handles a compressed group review — applies the same rating
// to all cards in the group (the primary card + its compressed companions).
func (h *Handler) ReviewBatch(w http.ResponseWriter, r *http.Request) {
	var input struct {
		CardIDs []int `json:"card_ids"`
		Rating  int   `json:"rating"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if input.Rating < 1 || input.Rating > 4 {
		errorResponse(w, http.StatusBadRequest, "rating must be 1-4")
		return
	}

	totalXP := 0
	reviewsDone := 0
	for _, cid := range input.CardIDs {
		card, err := h.DB.ReviewCard(int64(cid), fsrs.Rating(input.Rating), h.Params)
		if err != nil {
			continue
		}
		// Award XP for each card in the group (discounted for companions)
		xp := 10 + int(card.HintLevel)*2
		if reviewsDone > 0 {
			xp = int(float64(xp) * 0.5) // 50% for compressed cards
		}
		h.DB.AwardXP(xp)
		totalXP += xp
		reviewsDone++
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":          true,
		"total_xp":    totalXP,
		"reviews_done": reviewsDone,
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

// ── Push Notifications ──

func (h *Handler) PushSubscribe(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Endpoint       string `json:"endpoint"`
		P256DHKey      string `json:"p256dh_key"`
		AuthKey        string `json:"auth_key"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := h.DB.SavePushSubscription(db.PushSubscription{
		Endpoint:  input.Endpoint,
		P256DHKey: input.P256DHKey,
		AuthKey:   input.AuthKey,
	}); err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true})
}

func (h *Handler) PushUnsubscribe(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Endpoint string `json:"endpoint"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	h.DB.RemovePushSubscription(input.Endpoint)
	jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true})
}

func (h *Handler) PushVapidKey(w http.ResponseWriter, r *http.Request) {
	publicKey := os.Getenv("VAPID_PUBLIC_KEY")
	if publicKey == "" {
		publicKey = "BC-mZ7kPA4xQJ0YHIxQJ0YHIxQJ0YHIxQJ0YHIxQJ0Y"
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":         true,
		"public_key": publicKey,
	})
}

// truncateText truncates a string to maxLen characters.
func truncateText(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

// ── FIRe Credit API (for assessment engine integration) ──

// FireCredit accepts a verse ID and rating, computes FIRe boosts/penalties,
// and applies them. Used by the assessment engine to give implicit credit
// when a user demonstrates understanding of a connection.
func (h *Handler) FireCredit(w http.ResponseWriter, r *http.Request) {
	var input struct {
		VerseID string `json:"verse_id"`
		Rating  int    `json:"rating"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if input.VerseID == "" {
		errorResponse(w, http.StatusBadRequest, "verse_id required")
		return
	}

	var fireApplied, firePenalties int
	if input.Rating >= 3 {
		boosts, _ := h.Fire.ComputeBoosts(input.VerseID, input.Rating, h.DB.GetConnections, h.DB.HasCard)
		fireApplied, _ = h.DB.ApplyFIREBoosts(boosts)
	} else if input.Rating <= 2 && input.Rating > 0 {
		penalties, _ := h.Fire.ComputePenalties(input.VerseID, input.Rating, h.DB.GetConnections, h.DB.HasCard)
		firePenalties, _ = h.DB.ApplyFIREPenalties(penalties)
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":            true,
		"verse_id":      input.VerseID,
		"fire_boosts":   fireApplied,
		"fire_penalties": firePenalties,
	})
}

// ── Hebrew Knowledge Graph ──

// HebrewGraph returns the full Hebrew concept graph.
func (h *Handler) HebrewGraph(w http.ResponseWriter, r *http.Request) {
	nodes, edges, err := h.DB.GetHebrewGraph()
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"nodes": nodes,
		"edges": edges,
	})
}

// HebrewFire computes FIRe credits/penalties for the Hebrew knowledge graph.
// POST /api/memorize/hebrew/fire/{node_id}
func (h *Handler) HebrewFire(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		errorResponse(w, http.StatusMethodNotAllowed, "use POST")
		return
	}
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing node_id")
		return
	}
	nodeID := parts[4]

	var input struct {
		Rating int `json:"rating"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	graph := fire.KnowledgeGraph{
		GetConnections: h.DB.GetHebrewConnections,
		HasCard:        func(id string) (int64, bool) { return 0, true }, // all concepts are tracked
	}

	credits, penalties, err := h.Fire.ComputeCredits(nodeID, input.Rating, graph)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, err.Error())
		return
	}

	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":            true,
		"node_id":       nodeID,
		"credits":       credits,
		"penalties":     penalties,
		"credit_count":  len(credits),
		"penalty_count": len(penalties),
	})
}

// ── Hebrew Lessons ──

// HebrewLesson returns lesson content for a node.
func (h *Handler) HebrewLesson(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing node_id")
		return
	}
	nodeID := parts[4]
	content, err := h.DB.GetHebrewLesson(nodeID)
	if err != nil {
		errorResponse(w, http.StatusNotFound, "lesson not found")
		return
	}
	// Parse JSON content for structured response
	var lessonData interface{}
	if err := json.Unmarshal([]byte(content), &lessonData); err != nil {
		jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":      true,
			"node_id": nodeID,
			"content": content,
		})
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":      true,
		"node_id": nodeID,
		"lesson":  lessonData,
	})
}

// HebrewPractice returns practice items for a node.
func (h *Handler) HebrewPractice(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing node_id")
		return
	}
	nodeID := parts[4]
	items, err := h.DB.GetHebrewPracticeItems(nodeID, 10)
	if err != nil {
		errorResponse(w, http.StatusNotFound, "no practice items")
		return
	}
	jsonResponse(w, http.StatusOK, map[string]interface{}{
		"ok":    true,
		"node_id": nodeID,
		"items": items,
	})
}

// HebrewProgress returns or updates user progress.
func (h *Handler) HebrewProgress(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 5 {
		errorResponse(w, http.StatusBadRequest, "missing user_id")
		return
	}
	userID := parts[4]

	switch r.Method {
	case "GET":
		progress, err := h.DB.GetHebrewProgress(userID)
		if err != nil {
			errorResponse(w, http.StatusInternalServerError, err.Error())
			return
		}
		jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":       true,
			"user_id":  userID,
			"progress": progress,
		})
	case "POST":
		var input struct {
			NodeID string `json:"node_id"`
			Correct bool  `json:"correct"`
		}
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			errorResponse(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if err := h.DB.UpdateHebrewProgress(userID, input.NodeID, input.Correct); err != nil {
			errorResponse(w, http.StatusInternalServerError, err.Error())
			return
		}
		// Give FIRe credit via KnowledgeGraph
		graph := fire.KnowledgeGraph{
			GetConnections: h.DB.GetHebrewConnections,
			HasCard:        func(id string) (int64, bool) { return 0, true },
		}
		rating := 3
		if !input.Correct {
			rating = 1
		}
		credits, penalties, _ := h.Fire.ComputeCredits(input.NodeID, rating, graph)
		jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":            true,
			"node_id":       input.NodeID,
			"correct":       input.Correct,
			"credits":       len(credits),
			"penalties":     len(penalties),
		})
	default:
		errorResponse(w, http.StatusMethodNotAllowed, "use GET or POST")
	}
}

// RegisterRoutes sets up all HTTP routes on the given mux.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/api/memorize/verses/batch", h.SyncVerses)
	mux.HandleFunc("/api/memorize/queue", h.GetQueue)
	mux.HandleFunc("/api/memorize/review/", h.ReviewCard)
	mux.HandleFunc("/api/memorize/review-batch", h.ReviewBatch)
	mux.HandleFunc("/api/memorize/verses/", h.GetCardsByVerse)
	mux.HandleFunc("/api/memorize/cards", h.CreateCard)
	mux.HandleFunc("/api/memorize/stats", h.GetStats)
	mux.HandleFunc("/api/memorize/fire/credit", h.FireCredit)
	mux.HandleFunc("/api/memorize/hebrew/graph", h.HebrewGraph)
	mux.HandleFunc("/api/memorize/hebrew/fire/", h.HebrewFire)
	mux.HandleFunc("/api/memorize/hebrew/lesson/", h.HebrewLesson)
	mux.HandleFunc("/api/memorize/hebrew/practice/", h.HebrewPractice)
	mux.HandleFunc("/api/memorize/hebrew/progress/", h.HebrewProgress)
	mux.HandleFunc("/api/memorize/connections/batch", h.SyncConnections)
	mux.HandleFunc("/api/memorize/push/subscribe", h.PushSubscribe)
	mux.HandleFunc("/api/memorize/push/unsubscribe", h.PushUnsubscribe)
	mux.HandleFunc("/api/memorize/push/vapid-public-key", h.PushVapidKey)
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
