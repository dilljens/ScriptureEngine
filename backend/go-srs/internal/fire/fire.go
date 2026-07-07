// FIRe — Fractional Implicit Repetition.
//
// Adapted from plcourse (MIT): https://github.com/moaaz-ae/plcourse
// And Skycak's "The Math Academy Way" (Chapter 29).
//
// When a verse is reviewed successfully (Good/Easy), connected verses
// get fractional implicit repetition credit. This boosts their stability
// and extends their due date without requiring an explicit review.
//
// Connection weights determine how much credit flows:
//   direct_quotation:  0.8  (nearly identical text)
//   same_lemma:        0.4  (shared vocabulary)
//   parallel:          0.5  (same idea, different words)
//   allusion:          0.3  (thematic echo)
//   default:           0.2  (any other connection)

package fire

// Engine computes FIRe boosts using DFS through the connection graph.
type Engine struct{}

// Boost represents implicit repetition credit for a connected verse.
type Boost struct {
	VerseID string  `json:"verse_id"`
	CardID  int64   `json:"card_id"`
	Boost   float64 `json:"boost"`
}

// New creates a FIRe engine.
func New() *Engine {
	return &Engine{}
}

// ConnectionWeight returns the encompassing weight for a connection type.
func ConnectionWeight(connType string) float64 {
	switch connType {
	case "direct_quotation":
		return 0.8
	case "modified_quotation":
		return 0.7
	case "type_antitype":
		return 0.6
	case "chiastic":
		return 0.6
	case "parallel_synonymous":
		return 0.5
	case "parallel_antithetic":
		return 0.5
	case "parallel_synthetic":
		return 0.5
	case "parallel_step":
		return 0.5
	case "same_lemma":
		return 0.4
	case "keyword_linking":
		return 0.4
	case "merismus":
		return 0.4
	case "emblematic_parallelism":
		return 0.4
	case "allusion":
		return 0.3
	case "echo":
		return 0.2
	case "shared_symbol":
		return 0.3
	default:
		return 0.2
	}
}

// RatingMultiplier returns how much of the chain weight counts as credit.
// Good = 0.5 (moderate boost), Easy = 1.0 (full boost).
func RatingMultiplier(rating int) float64 {
	switch rating {
	case 4: // Easy
		return 1.0
	case 3: // Good
		return 0.5
	default:
		return 0.0
	}
}

// ComputeBoosts runs DFS through the connection graph starting from sourceVerseID.
// It finds all reachable verses and computes FIRe credit for each.
//
// Args:
//   sourceVerseID: the verse being reviewed
//   rating: review rating (1-4)
//   getConnections: function that returns connections for a verse
//   hasCard: function that checks if a verse has a memorization card
//
// Returns:
//   boosts: list of (verseID, cardID, boost) for connected verses with cards
func (e *Engine) ComputeBoosts(
	sourceVerseID string,
	rating int,
	getConnections func(verseID string) ([]Connection, error),
	hasCard func(verseID string) (cardID int64, exists bool),
) ([]Boost, error) {
	multiplier := RatingMultiplier(rating)
	if multiplier <= 0 {
		return nil, nil
	}

	// DFS through the connection graph
	type node struct {
		verseID     string
		chainWeight float64
	}

	bestBoost := make(map[string]float64) // verseID -> best chain weight
	bestCardID := make(map[string]int64)   // verseID -> card ID
	visited := make(map[string]bool)
	stack := []node{{verseID: sourceVerseID, chainWeight: 1.0}}

	for len(stack) > 0 {
		current := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		if current.chainWeight < 0.001 {
			continue
		}
		if visited[current.verseID] {
			continue
		}
		visited[current.verseID] = true

		conns, err := getConnections(current.verseID)
		if err != nil {
			return nil, err
		}

		for _, conn := range conns {
			weight := ConnectionWeight(conn.Type)
			if weight <= 0 {
				continue
			}

			chainWeight := current.chainWeight * weight
			if chainWeight < 0.001 {
				continue
			}

			// Don't boost the source verse itself
			if conn.TargetVerse == sourceVerseID {
				continue
			}

			// Check if this path gives a better boost
			if chainWeight <= bestBoost[conn.TargetVerse] {
				continue
			}

			// Check if the target verse has a card
			if cardID, exists := hasCard(conn.TargetVerse); exists {
				bestBoost[conn.TargetVerse] = chainWeight
				bestCardID[conn.TargetVerse] = cardID
			}

			// Continue DFS
			stack = append(stack, node{
				verseID:     conn.TargetVerse,
				chainWeight: chainWeight,
			})
		}
	}

	// Convert to result
	var boosts []Boost
	for verseID, chainWeight := range bestBoost {
		boosts = append(boosts, Boost{
			VerseID: verseID,
			CardID:  bestCardID[verseID],
			Boost:   chainWeight * multiplier,
		})
	}

	return boosts, nil
}

// Connection represents an edge in the scripture connection graph.
type Connection struct {
	SourceVerse string `json:"source_verse"`
	TargetVerse string `json:"target_verse"`
	Type        string `json:"type"`
}
