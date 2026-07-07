package db

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/dillon/scriptureengine/go-srs/internal/fire"
	"github.com/dillon/scriptureengine/go-srs/internal/fsrs"
)

// DB wraps the SQLite connection and provides CRUD operations.
type DB struct {
	conn *sql.DB
}

// Schema definitions.
const schema = `
CREATE TABLE IF NOT EXISTS verses (
    id TEXT PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_num INTEGER NOT NULL,
    text TEXT NOT NULL,
    reference TEXT NOT NULL,
    language TEXT DEFAULT 'english',
    last_synced TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    card_type TEXT NOT NULL DEFAULT 'text',
    state INTEGER NOT NULL DEFAULT 0,
    stability REAL NOT NULL DEFAULT 0.0,
    difficulty REAL NOT NULL DEFAULT 0.0,
    elapsed_days REAL NOT NULL DEFAULT 0.0,
    scheduled_days REAL NOT NULL DEFAULT 0.0,
    reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    hint_level INTEGER NOT NULL DEFAULT 0,
    last_review TEXT,
    due TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(due);
CREATE INDEX IF NOT EXISTS idx_cards_verse ON cards(verse_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_verse_type ON cards(verse_id, card_type);

CREATE TABLE IF NOT EXISTS review_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES cards(id),
    rating INTEGER NOT NULL,
    elapsed_seconds REAL NOT NULL DEFAULT 0.0,
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_review_log_card ON review_log(card_id);

CREATE TABLE IF NOT EXISTS palaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    photo_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loci (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    palace_id INTEGER NOT NULL REFERENCES palaces(id),
    label TEXT NOT NULL DEFAULT '',
    x_pct REAL NOT NULL DEFAULT 0.5,
    y_pct REAL NOT NULL DEFAULT 0.5,
    verse_id TEXT REFERENCES verses(id)
);

CREATE INDEX IF NOT EXISTS idx_loci_palace ON loci(palace_id);

CREATE TABLE IF NOT EXISTS concept_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    file_path TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'openverse',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS composite_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    palace_id INTEGER NOT NULL REFERENCES palaces(id),
    locus_id INTEGER NOT NULL REFERENCES loci(id),
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audio_recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    file_path TEXT NOT NULL,
    duration_secs REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verse_connections (
    verse_id TEXT NOT NULL,
    connected_verse_id TEXT NOT NULL,
    connection_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.2,
    PRIMARY KEY (verse_id, connected_verse_id, connection_type)
);

CREATE INDEX IF NOT EXISTS idx_conn_verse ON verse_connections(verse_id);
CREATE INDEX IF NOT EXISTS idx_conn_target ON verse_connections(connected_verse_id);

CREATE TABLE IF NOT EXISTS user_xp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xp INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER NOT NULL DEFAULT 0,
    last_review_date TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL DEFAULT '',
    auth_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
`

// Open opens a SQLite database, creating it if needed.
func Open(path string) (*DB, error) {
	conn, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_foreign_keys=on")
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	if _, err := conn.Exec(schema); err != nil {
		return nil, fmt.Errorf("create schema: %w", err)
	}

	// Migrations for existing databases
	migrations := []string{
		"ALTER TABLE cards ADD COLUMN fi_re_credit REAL NOT NULL DEFAULT 0.0",
	}
	for _, m := range migrations {
		conn.Exec(m) // Ignore errors (column may already exist)
	}

	// Ensure user_xp has a row
	conn.Exec("INSERT OR IGNORE INTO user_xp (id, xp, streak_count) VALUES (1, 0, 0)")

	return &DB{conn: conn}, nil
}

// Close closes the database.
func (db *DB) Close() error {
	return db.conn.Close()
}

// ── Verse Operations ──

// VerseRow represents a verse to sync.
type VerseRow struct {
	ID        string
	Book      string
	Chapter   int
	Verse     int
	Text      string
	Reference string
	Language  string
}

// SyncVerses bulk-inserts or updates verses.
func (db *DB) SyncVerses(verses []VerseRow) error {
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
		INSERT INTO verses (id, book, chapter, verse_num, text, reference, language)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
			text=excluded.text, reference=excluded.reference, last_synced=datetime('now')
	`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, v := range verses {
		if _, err := stmt.Exec(v.ID, v.Book, v.Chapter, v.Verse, v.Text, v.Reference, v.Language); err != nil {
			return err
		}
	}

	return tx.Commit()
}

// GetVerse fetches a single verse.
func (db *DB) GetVerse(id string) (text, reference string, err error) {
	err = db.conn.QueryRow("SELECT text, reference FROM verses WHERE id = ?", id).Scan(&text, &reference)
	return
}

// VerseCount returns the number of synced verses.
func (db *DB) VerseCount() (int, error) {
	var n int
	err := db.conn.QueryRow("SELECT COUNT(*) FROM verses").Scan(&n)
	return n, err
}

// ── Card Operations ──

// EnsureCard creates a card for a verse if it doesn't exist.
func (db *DB) EnsureCard(verseID, cardType string) (int64, error) {
	// Check if card exists
	var id int64
	err := db.conn.QueryRow("SELECT id FROM cards WHERE verse_id = ? AND card_type = ?",
		verseID, cardType).Scan(&id)
	if err == nil {
		return id, nil
	}

	// Create new card
	result, err := db.conn.Exec(
		"INSERT INTO cards (verse_id, card_type) VALUES (?, ?)",
		verseID, cardType)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// DueCardItem represents a card due for review.
type DueCardItem struct {
	CardID        int64   `json:"CardID"`
	VerseID       string  `json:"VerseID"`
	VerseText     string  `json:"VerseText"`
	Reference     string  `json:"Reference"`
	CardType      string  `json:"CardType"`
	HintLevel     int     `json:"HintLevel"`
	State         int     `json:"State"`
	Stability     float64 `json:"Stability"`
	Difficulty    float64 `json:"Difficulty"`
	ScheduledDays float64 `json:"ScheduledDays"`
}

// GetDueCards returns cards scheduled for review.
func (db *DB) GetDueCards(limit int) ([]DueCardItem, error) {
	rows, err := db.conn.Query(`
		SELECT c.id, c.verse_id, v.text, v.reference, c.card_type,
		       c.hint_level, c.state, c.stability, c.difficulty, c.scheduled_days
		FROM cards c
		JOIN verses v ON v.id = c.verse_id
		WHERE c.due <= datetime('now')
		ORDER BY c.due ASC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var items []DueCardItem
	for rows.Next() {
		var item DueCardItem
		if err := rows.Scan(&item.CardID, &item.VerseID, &item.VerseText, &item.Reference,
			&item.CardType, &item.HintLevel, &item.State, &item.Stability, &item.Difficulty,
			&item.ScheduledDays); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

// GetDueCount returns the number of cards due for review.
func (db *DB) GetDueCount() (int, error) {
	var n int
	err := db.conn.QueryRow(
		"SELECT COUNT(*) FROM cards WHERE due <= datetime('now')").Scan(&n)
	return n, err
}

// GetCardsByVerse returns all cards for a verse.
func (db *DB) GetCardsByVerse(verseID string) ([]struct {
	ID      int64
	Type    string
	State   int
	Due     time.Time
}, error) {
	rows, err := db.conn.Query(`
		SELECT id, card_type, state, due FROM cards WHERE verse_id = ?
	`, verseID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var cards []struct {
		ID      int64
		Type    string
		State   int
		Due     time.Time
	}
	for rows.Next() {
		var c struct {
			ID      int64
			Type    string
			State   int
			Due     time.Time
		}
		var dueStr string
		if err := rows.Scan(&c.ID, &c.Type, &c.State, &dueStr); err != nil {
			return nil, err
		}
		c.Due, _ = time.Parse("2006-01-02 15:04:05", dueStr)
		cards = append(cards, c)
	}
	return cards, nil
}

// ReviewCard applies an FSRS review to a card.
func (db *DB) ReviewCard(cardID int64, rating fsrs.Rating, params fsrs.FSRSParams) (*fsrs.Card, error) {
	// Fetch current card state
	var card fsrs.Card
	var lastReview string
	var lastReviewNull sql.NullString
	var due string

	err := db.conn.QueryRow(`
		SELECT state, stability, difficulty, elapsed_days, scheduled_days, reps, lapses,
		       hint_level, last_review, due
		FROM cards WHERE id = ?
	`, cardID).Scan(&card.State, &card.Stability, &card.Difficulty,
		&card.ElapsedDays, &card.ScheduledDays, &card.Reps, &card.Lapses,
		&card.HintLevel, &lastReviewNull, &due)
	if err != nil {
		return nil, err
	}
	if lastReviewNull.Valid {
		lastReview = lastReviewNull.String
	}
	if err != nil {
		return nil, err
	}

	if lastReview != "" {
		card.LastReview, _ = time.Parse("2006-01-02 15:04:05", lastReview)
	}

	// Compute next state
	nextCard, log := card.Next(rating, params)

	// Store review log
	db.conn.Exec(`
		INSERT INTO review_log (card_id, rating, elapsed_seconds)
		VALUES (?, ?, ?)
	`, cardID, int(rating), log.Elapsed)

	// Update card
	dueStr := nextCard.Due.Format("2006-01-02 15:04:05")
	lastReviewStr := nextCard.LastReview.Format("2006-01-02 15:04:05")

	_, err = db.conn.Exec(`
		UPDATE cards SET
			state=?, stability=?, difficulty=?, elapsed_days=?, scheduled_days=?,
			reps=?, lapses=?, last_review=?, due=?
		WHERE id=?
	`, nextCard.State, nextCard.Stability, nextCard.Difficulty,
		nextCard.ElapsedDays, nextCard.ScheduledDays,
		nextCard.Reps, nextCard.Lapses, lastReviewStr, dueStr, cardID)
	if err != nil {
		return nil, err
	}

	return &nextCard, nil
}

// ── Palace Operations ──

func (db *DB) CreatePalace(name, photoPath string) (int64, error) {
	result, err := db.conn.Exec("INSERT INTO palaces (name, photo_path) VALUES (?, ?)", name, photoPath)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

func (db *DB) ListPalaces() ([]Palace, error) {
	rows, err := db.conn.Query("SELECT id, name, photo_path, created_at FROM palaces ORDER BY created_at DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var palaces []Palace
	for rows.Next() {
		var p Palace
		var createdAt string
		if err := rows.Scan(&p.ID, &p.Name, &p.PhotoPath, &createdAt); err != nil {
			return nil, err
		}
		p.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
		palaces = append(palaces, p)
	}
	return palaces, nil
}

// Palace struct for listing
type Palace struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	PhotoPath string    `json:"photo_path"`
	CreatedAt time.Time `json:"created_at"`
}

// Locus struct for a palace location point.
type Locus struct {
	ID       int64   `json:"id"`
	PalaceID int64   `json:"palace_id"`
	Label    string  `json:"label"`
	XPercent float64 `json:"x_pct"`
	YPercent float64 `json:"y_pct"`
	VerseID  *string `json:"verse_id,omitempty"`
}

// GetPalaceWithLoci returns a palace with all its loci.
func (db *DB) GetPalaceWithLoci(palaceID int64) (*Palace, []Locus, error) {
	var p Palace
	var createdAt string
	err := db.conn.QueryRow(
		"SELECT id, name, photo_path, created_at FROM palaces WHERE id = ?", palaceID,
	).Scan(&p.ID, &p.Name, &p.PhotoPath, &createdAt)
	if err != nil {
		return nil, nil, err
	}
	p.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)

	rows, err := db.conn.Query(
		"SELECT id, palace_id, label, x_pct, y_pct, verse_id FROM loci WHERE palace_id = ? ORDER BY id",
		palaceID,
	)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()

	var loci []Locus
	for rows.Next() {
		var l Locus
		rows.Scan(&l.ID, &l.PalaceID, &l.Label, &l.XPercent, &l.YPercent, &l.VerseID)
		loci = append(loci, l)
	}
	return &p, loci, nil
}

// AddLocus adds a new locus to a palace.
func (db *DB) AddLocus(palaceID int64, label string, x, y float64) (int64, error) {
	result, err := db.conn.Exec(
		"INSERT INTO loci (palace_id, label, x_pct, y_pct) VALUES (?, ?, ?, ?)",
		palaceID, label, x, y,
	)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// AssignVerseToLocus assigns a verse to an existing locus.
func (db *DB) AssignVerseToLocus(locusID int64, verseID string) error {
	_, err := db.conn.Exec(
		"UPDATE loci SET verse_id = ? WHERE id = ?", verseID, locusID,
	)
	return err
}

// ── Image Operations ──

// SaveConceptImage records a concept image for a verse.
func (db *DB) SaveConceptImage(verseID, filePath, source string) (int64, error) {
	// Check if one already exists
	var existing int64
	err := db.conn.QueryRow(
		"SELECT id FROM concept_images WHERE verse_id = ?", verseID,
	).Scan(&existing)
	if err == nil {
		// Update existing
		_, err := db.conn.Exec(
			"UPDATE concept_images SET file_path = ?, source = ? WHERE id = ?",
			filePath, source, existing)
		return existing, err
	}

	result, err := db.conn.Exec(
		"INSERT INTO concept_images (verse_id, file_path, source) VALUES (?, ?, ?)",
		verseID, filePath, source)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// GetConceptImage returns the file path for a verse's concept image.
func (db *DB) GetConceptImage(verseID string) (string, error) {
	var path string
	err := db.conn.QueryRow(
		"SELECT file_path FROM concept_images WHERE verse_id = ?", verseID,
	).Scan(&path)
	return path, err
}

// ── XP Operations ──

func (db *DB) AwardXP(xp int) (int, error) {
	// Update XP and streak
	today := time.Now().Format("2006-01-02")
	
	var lastDate string
	db.conn.QueryRow("SELECT last_review_date FROM user_xp WHERE id=1").Scan(&lastDate)
	
	// Update streak
	var streak int
	if lastDate == today {
		// Already reviewed today, don't increment streak
	} else if lastDate == time.Now().Add(-24*time.Hour).Format("2006-01-02") {
		// Consecutive day
		db.conn.Exec("UPDATE user_xp SET streak_count = streak_count + 1 WHERE id=1")
	} else if lastDate != today {
		// Streak broken
		db.conn.Exec("UPDATE user_xp SET streak_count = 1 WHERE id=1")
	}

	_, err := db.conn.Exec(`
		UPDATE user_xp SET xp = xp + ?, last_review_date = ?, updated_at = datetime('now') WHERE id=1
	`, xp, today)
	if err != nil {
		return 0, err
	}

	db.conn.QueryRow("SELECT streak_count FROM user_xp WHERE id=1").Scan(&streak)
	return streak, nil
}

func (db *DB) GetStats() (struct {
	TotalCards  int
	DueCards    int
	Mastered    int
	Streak      int
	TotalXP     int
	ReviewsToday int
}, error) {
	var s struct {
		TotalCards  int
		DueCards    int
		Mastered    int
		Streak      int
		TotalXP     int
		ReviewsToday int
	}

	db.conn.QueryRow("SELECT COUNT(*) FROM cards").Scan(&s.TotalCards)
	db.conn.QueryRow("SELECT COUNT(*) FROM cards WHERE due <= datetime('now')").Scan(&s.DueCards)
	db.conn.QueryRow("SELECT COUNT(*) FROM cards WHERE stability > 30 AND state = 2").Scan(&s.Mastered)
	db.conn.QueryRow("SELECT xp, streak_count FROM user_xp WHERE id=1").Scan(&s.TotalXP, &s.Streak)

	today := time.Now().Format("2006-01-02")
	db.conn.QueryRow(
		"SELECT COUNT(*) FROM review_log WHERE date(reviewed_at) = ?", today,
	).Scan(&s.ReviewsToday)

	return s, nil
}

// ScanCardVerse retrieves the verse_id for a card (used for FIRe).
func (db *DB) ScanCardVerse(cardID int64, verseID *string) error {
	return db.conn.QueryRow("SELECT verse_id FROM cards WHERE id = ?", cardID).Scan(verseID)
}

// UpdateHintLevel updates a card's progressive hint level.
func (db *DB) UpdateHintLevel(cardID int64, level int) error {
	_, err := db.conn.Exec("UPDATE cards SET hint_level = ? WHERE id = ?", level, cardID)
	return err
}

// ── Connection Operations (for FIRe) ──

// SyncConnections bulk-inserts or updates verse connections.
type ConnectionRow struct {
	SourceVerse string
	TargetVerse string
	ConnType    string
}

func (db *DB) SyncConnections(conns []ConnectionRow) error {
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
		INSERT INTO verse_connections (verse_id, connected_verse_id, connection_type, weight)
		VALUES (?, ?, ?, ?)
		ON CONFLICT(verse_id, connected_verse_id, connection_type) DO UPDATE SET weight=excluded.weight
	`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, c := range conns {
		w := fire.ConnectionWeight(c.ConnType)
		if _, err := stmt.Exec(c.SourceVerse, c.TargetVerse, c.ConnType, w); err != nil {
			return err
		}
		// Also store reverse direction
		if _, err := stmt.Exec(c.TargetVerse, c.SourceVerse, c.ConnType, w); err != nil {
			return err
		}
	}

	return tx.Commit()
}

// GetConnections returns all connections from a verse.
func (db *DB) GetConnections(verseID string) ([]fire.Connection, error) {
	rows, err := db.conn.Query(
		"SELECT verse_id, connected_verse_id, connection_type FROM verse_connections WHERE verse_id = ?",
		verseID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var conns []fire.Connection
	for rows.Next() {
		var c fire.Connection
		if err := rows.Scan(&c.SourceVerse, &c.TargetVerse, &c.Type); err != nil {
			return nil, err
		}
		conns = append(conns, c)
	}
	return conns, nil
}

// HasCard checks if a verse has any memorization cards and returns the first card ID.
func (db *DB) HasCard(verseID string) (int64, bool) {
	var id int64
	err := db.conn.QueryRow("SELECT id FROM cards WHERE verse_id = ? LIMIT 1", verseID).Scan(&id)
	return id, err == nil
}

// ApplyFIREBoosts applies FIRe credit to connected cards.
// Returns the number of cards that were boosted.
func (db *DB) ApplyFIREBoosts(boosts []fire.Boost) (int, error) {
	if len(boosts) == 0 {
		return 0, nil
	}

	applied := 0
	for _, b := range boosts {
		if b.Boost <= 0 {
			continue
		}

		// Get current card state
		var stability, scheduledDays float64
		var lastReview string
		err := db.conn.QueryRow(
			"SELECT stability, scheduled_days, last_review FROM cards WHERE id = ?",
			b.CardID,
		).Scan(&stability, &scheduledDays, &lastReview)
		if err != nil {
			continue
		}

		// Only boost cards in review state (not new cards)
		if stability <= 0 {
			continue
		}

		// Apply boost: new_stability = stability * (1 + boost)
		newStability := stability * (1.0 + b.Boost)

		// Compute new due date
		var newDue string
		if lastReview != "" {
			t, err := time.Parse("2006-01-02 15:04:05", lastReview)
			if err == nil {
				newDueTime := t.Add(time.Duration(newStability*24) * time.Hour)
				newDue = newDueTime.Format("2006-01-02 15:04:05")
			}
		}
		if newDue == "" {
			newDue = time.Now().Add(time.Duration(newStability*24) * time.Hour).Format("2006-01-02 15:04:05")
		}

		_, err = db.conn.Exec(
			"UPDATE cards SET stability = ?, scheduled_days = ?, due = ? WHERE id = ?",
			newStability, newStability, newDue, b.CardID,
		)
		if err == nil {
	applied++
	}
}
return applied, nil
}

// ── Push Notification Operations ──

// PushSubscription represents a Web Push subscription.
type PushSubscription struct {
	Endpoint       string `json:"endpoint"`
	P256DHKey      string `json:"p256dh_key"`
	AuthKey        string `json:"auth_key"`
}

// SavePushSubscription stores a push subscription.
func (db *DB) SavePushSubscription(sub PushSubscription) error {
	_, err := db.conn.Exec(
		`INSERT INTO push_subscriptions (endpoint, p256dh_key, auth_key)
		 VALUES (?, ?, ?)
		 ON CONFLICT(endpoint) DO UPDATE SET p256dh_key=excluded.p256dh_key, auth_key=excluded.auth_key`,
		sub.Endpoint, sub.P256DHKey, sub.AuthKey,
	)
	return err
}

// RemovePushSubscription removes a push subscription.
func (db *DB) RemovePushSubscription(endpoint string) error {
	_, err := db.conn.Exec("DELETE FROM push_subscriptions WHERE endpoint = ?", endpoint)
	return err
}

// GetAllPushSubscriptions returns all push subscriptions.
func (db *DB) GetAllPushSubscriptions() ([]PushSubscription, error) {
	rows, err := db.conn.Query("SELECT endpoint, p256dh_key, auth_key FROM push_subscriptions")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var subs []PushSubscription
	for rows.Next() {
		var s PushSubscription
		if err := rows.Scan(&s.Endpoint, &s.P256DHKey, &s.AuthKey); err != nil {
			return nil, err
		}
		subs = append(subs, s)
	}
	return subs, nil
}
