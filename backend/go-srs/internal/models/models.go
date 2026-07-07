package models

import "time"

// Verse mirrors a scripture verse from the main engine.
type Verse struct {
	ID        string `json:"id"`         // "gen.1.1"
	Book      string `json:"book"`       // "gen"
	Chapter   int    `json:"chapter"`    // 1
	Verse     int    `json:"verse_num"`  // 1
	Text      string `json:"text"`       // KJV text
	Reference string `json:"reference"`  // "Genesis 1:1"
	Language  string `json:"language"`   // "english", "hebrew", "greek"
}

// Card represents a memorization flashcard.
type Card struct {
	ID          int64     `json:"id"`
	VerseID     string    `json:"verse_id"`
	CardType    string    `json:"card_type"`     // "text", "first_letter", "audio"
	State       int       `json:"state"`         // 0=new, 1=learning, 2=review, 3=relearning
	Stability   float64   `json:"stability"`
	Difficulty  float64   `json:"difficulty"`
	ElapsedDays float64   `json:"elapsed_days"`
	ScheduledDays float64 `json:"scheduled_days"`
	Reps        int       `json:"reps"`
	Lapses      int       `json:"lapses"`
	HintLevel   int       `json:"hint_level"`    // 0-5 progressive hint level
	LastReview  time.Time `json:"last_review"`
	Due         time.Time `json:"due"`
	CreatedAt   time.Time `json:"created_at"`
}

// ReviewLog records a single card review.
type ReviewLog struct {
	ID        int64     `json:"id"`
	CardID    int64     `json:"card_id"`
	Rating    int       `json:"rating"`     // 1=again, 2=hard, 3=good, 4=easy
	Elapsed   float64   `json:"elapsed_seconds"`
	ReviewedAt time.Time `json:"reviewed_at"`
}

// Palace represents a memory palace.
type Palace struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	PhotoPath string    `json:"photo_path"`
	CreatedAt time.Time `json:"created_at"`
}

// Locus is a location within a palace.
type Locus struct {
	ID       int64   `json:"id"`
	PalaceID int64   `json:"palace_id"`
	Label    string  `json:"label"`
	XPercent float64 `json:"x_pct"`
	YPercent float64 `json:"y_pct"`
	VerseID  *string `json:"verse_id,omitempty"`
}

// ConceptImage stores an image associated with a verse.
type ConceptImage struct {
	ID       int64  `json:"id"`
	VerseID  string `json:"verse_id"`
	FilePath string `json:"file_path"`
	Source   string `json:"source"` // "ai", "openverse", "upload"
}

// CompositeImage stores a composited palace image.
type CompositeImage struct {
	ID       int64  `json:"id"`
	VerseID  string `json:"verse_id"`
	PalaceID int64  `json:"palace_id"`
	LocusID  int64  `json:"locus_id"`
	FilePath string `json:"file_path"`
}

// AudioRecording stores a user's recitation.
type AudioRecording struct {
	ID          int64  `json:"id"`
	VerseID     string `json:"verse_id"`
	FilePath    string `json:"file_path"`
	DurationSec float64 `json:"duration_secs"`
}

// QueueItem is a card due for review with verse text.
type QueueItem struct {
	CardID      int64   `json:"card_id"`
	VerseID     string  `json:"verse_id"`
	VerseText   string  `json:"verse_text"`
	Reference   string  `json:"reference"`
	CardType    string  `json:"card_type"`
	HintLevel   int     `json:"hint_level"`
	Stability   float64 `json:"stability"`
	Difficulty  float64 `json:"difficulty"`
	ScheduledDays float64 `json:"scheduled_days"`
}

// UserStats holds a user's memorization progress.
type UserStats struct {
	TotalCards     int            `json:"total_cards"`
	DueCards       int            `json:"due_cards"`
	MasteredCards  int            `json:"mastered_cards"` // stability > 30 days
	StreakDays     int            `json:"streak_days"`
	TotalXP        int            `json:"total_xp"`
	ReviewsToday   int            `json:"reviews_today"`
	MasteryByLayer map[string]float64 `json:"mastery_by_layer"`
}
