// FIRe — Fractional Implicit Repetition.
//
// Adapted from plcourse (MIT): https://github.com/moaaz-ae/plcourse
// And Skycak's "The Math Academy Way" (Chapter 29).
//
// FIRe generalizes spaced repetition to connected knowledge:
//   1. CREDIT flows downward — reviewing a verse gives implicit
//      repetition credit to connected verses (already implemented).
//   2. PENALTIES flow upward — failing a foundational verse
//      penalizes the verses that depend on it.
//   3. EARLY DISCOUNT — implicit credit is discounted when the
//      review was done early (retrievability still high).

package fire

// Engine computes FIRe boosts and penalties using DFS through
// the verse connection graph.
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
// These represent what fraction of the target verse is practiced when
// reviewing the source verse.
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

// PenaltyMultiplier returns how much of the chain weight counts as penalty.
// Again = 1.0 (full penalty), Hard = 0.3 (weak penalty).
func PenaltyMultiplier(rating int) float64 {
	switch rating {
	case 1: // Again
		return 1.0
	case 2: // Hard
		return 0.3
	default:
		return 0.0
	}
}

// EarlyDiscount reduces FIRe credit when the review was too early.
//
// From Math Academy Way (Ch 29):
//   "rawDelta is discounted if the repetition was completed early
//    relative to the desired interval, i.e., if memory is sufficiently high."
//
// When retrievability is still high (the review was premature), the
// implicit credit is discounted because the brain didn't have to work
// as hard to recall the information. When retrievability is low (the
// review was well-timed or late), full credit is given.
//
// Formula: effective = boost * (1 - R^2)
//
//	R=0.0 (forgotten):    1.0 × boost  (full credit)
//	R=0.5 (moderate):     0.75 × boost
//	R=0.8 (strong):       0.36 × boost
//	R=0.95 (fresh):       0.10 × boost  (heavily discounted)
func EarlyDiscount(boost, retrievability float64) float64 {
	if retrievability <= 0 {
		return boost
	}
	if retrievability >= 1 {
		return 0
	}
	discount := retrievability * retrievability // 0 to 1
	return boost * (1.0 - discount)
}

// ── Credit Flow (downward) ──

// ComputeBoosts runs DFS through the connection graph starting from
// sourceVerseID. It finds all reachable verses and computes FIRe credit
// for each — the "lightning bolts" of credit flowing downward.
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

	bestBoost := make(map[string]float64)
	bestCardID := make(map[string]int64)
	visited := make(map[string]bool)

	type node struct {
		verseID     string
		chainWeight float64
	}
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

			if conn.TargetVerse == sourceVerseID {
				continue
			}

			if chainWeight <= bestBoost[conn.TargetVerse] {
				continue
			}

			if cardID, exists := hasCard(conn.TargetVerse); exists {
				bestBoost[conn.TargetVerse] = chainWeight
				bestCardID[conn.TargetVerse] = cardID
			}

			stack = append(stack, node{
				verseID:     conn.TargetVerse,
				chainWeight: chainWeight,
			})
		}
	}

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

// ── Penalty Flow (upward) ──

// ComputePenalties runs DFS from sourceVerseID to find connected verses
// that should be penalized when the source verse is failed.
//
// From Math Academy Way (Ch 29):
//   "If you fail a repetition on a simpler topic, the failed repetition
//    flows forward to penalize more advanced topics that depend on it."
//
// For scripture memorization: failing a foundational verse suggests that
// verses building on it may also be shaky. Penalty flows along the same
// connection paths but in the opposite direction of credit.
//
// Returns:
//   penalties: list of (verseID, cardID, penalty) where penalty ∈ [0, 1]
func (e *Engine) ComputePenalties(
	sourceVerseID string,
	rating int,
	getConnections func(verseID string) ([]Connection, error),
	hasCard func(verseID string) (cardID int64, exists bool),
) ([]Boost, error) {
	multiplier := PenaltyMultiplier(rating)
	if multiplier <= 0 {
		return nil, nil
	}

	bestPenalty := make(map[string]float64)
	bestCardID := make(map[string]int64)
	visited := make(map[string]bool)

	type node struct {
		verseID     string
		chainWeight float64
	}
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

			if conn.TargetVerse == sourceVerseID {
				continue
			}

			if chainWeight <= bestPenalty[conn.TargetVerse] {
				continue
			}

			if cardID, exists := hasCard(conn.TargetVerse); exists {
				bestPenalty[conn.TargetVerse] = chainWeight
				bestCardID[conn.TargetVerse] = cardID
			}

			stack = append(stack, node{
				verseID:     conn.TargetVerse,
				chainWeight: chainWeight,
			})
		}
	}

	var penalties []Boost
	for verseID, chainWeight := range bestPenalty {
		penalties = append(penalties, Boost{
			VerseID: verseID,
			CardID:  bestCardID[verseID],
			Boost:   chainWeight * multiplier, // penalty value (positive)
		})
	}

	return penalties, nil
}

// Connection represents an edge in the scripture connection graph.
type Connection struct {
	SourceVerse string `json:"source_verse"`
	TargetVerse string `json:"target_verse"`
	Type        string `json:"type"`
}
