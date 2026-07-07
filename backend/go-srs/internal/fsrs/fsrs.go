// FSRS-5 (Free Spaced Repetition Scheduler) Go implementation.
//
// Ported from fsrs-rs (https://github.com/open-spaced-repetition/fsrs-rs)
// Verified against published test vectors.

package fsrs

import (
	"math"
	"time"
)

// FSRS-5 uses 21 parameters.
// FSRSParams contains the 21 learned parameters plus scheduling configuration.
type FSRSParams struct {
	RequestRetention float64    // desired retention rate (default 0.9)
	MaximumInterval  float64    // max interval in days (default 36500)
	W                [21]float64 // 21 FSRS-5 parameters
	EnableShortTerm  bool       // whether to use short-term stability
}

// Default W-parameters (FSRS-5, trained on 30M+ reviews).
// From fsrs-rs DEFAULT_PARAMETERS.
var DefaultW = [21]float64{
	0.212,   // w[0]:  initial stability for rating=1 (Again)
	1.2931,  // w[1]:  initial stability for rating=2 (Hard)
	2.3065,  // w[2]:  initial stability for rating=3 (Good)
	8.2956,  // w[3]:  initial stability for rating=4 (Easy)
	6.4133,  // w[4]:  initial difficulty offset
	0.8334,  // w[5]:  initial difficulty multiplier
	3.0194,  // w[6]:  difficulty increment/decrement
	0.001,   // w[7]:  mean reversion strength
	1.8722,  // w[8]:  stability increment multiplier
	0.1666,  // w[9]:  stability decay exponent
	0.796,   // w[10]: retrievability decay exponent
	1.4835,  // w[11]: failure stability multiplier
	0.0614,  // w[12]: failure difficulty exponent
	0.2629,  // w[13]: failure stability exponent
	1.6483,  // w[14]: failure retrievability exponent
	0.6014,  // w[15]: hard penalty (rating==2 multiplier)
	1.8729,  // w[16]: easy bonus (rating==4 multiplier)
	0.5425,  // w[17]: short-term stability — delta
	0.0912,  // w[18]: short-term stability — offset
	0.0658,  // w[19]: short-term stability — decay
	0.1542,  // w[20]: forgetting curve decay (FSRS6_DEFAULT_DECAY)
}

// DefaultParams with sensible values for general use.
var DefaultParams = FSRSParams{
	RequestRetention: 0.9,
	MaximumInterval:  36500,
	W:                DefaultW,
	EnableShortTerm:  false,
}

// CardState tracks where a card is in the learning process.
type CardState int

const (
	StateNew        CardState = 0
	StateLearning   CardState = 1
	StateReview     CardState = 2
	StateRelearning CardState = 3
)

// Rating values (Anki convention: Again=1, Hard=2, Good=3, Easy=4).
type Rating int

const (
	RatingAgain Rating = 1
	RatingHard  Rating = 2
	RatingGood  Rating = 3
	RatingEasy  Rating = 4
)

// MemoryState holds the core FSRS state.
type MemoryState struct {
	Stability  float64 `json:"stability"`
	Difficulty float64 `json:"difficulty"`
}

// Card represents a flashcard with its FSRS state and scheduling info.
type Card struct {
	State        CardState `json:"state"`
	Stability    float64   `json:"stability"`
	Difficulty   float64   `json:"difficulty"`
	ElapsedDays  float64   `json:"elapsed_days"`
	ScheduledDays float64  `json:"scheduled_days"`
	Reps         int       `json:"reps"`
	Lapses       int       `json:"lapses"`
	LastReview   time.Time `json:"last_review"`
	Due          time.Time `json:"due"`
}

// ReviewLog records a single review event.
type ReviewLog struct {
	Rating    Rating    `json:"rating"`
	Elapsed   float64   `json:"elapsed_seconds"`
	Date      time.Time `json:"date"`
}

// NewCard creates a fresh card.
func NewCard() Card {
	return Card{State: StateNew}
}

// Next computes the next state given a rating.
func (c Card) Next(rating Rating, params FSRSParams) (Card, ReviewLog) {
	now := time.Now()
	elapsed := 0.0
	if !c.LastReview.IsZero() {
		elapsed = now.Sub(c.LastReview).Hours() / 24.0
	}

	card := c
	card.LastReview = now
	card.ElapsedDays = elapsed

	// Build memory state from current card
	state := MemoryState{Stability: c.Stability, Difficulty: c.Difficulty}

	// Skip initial state for brand-new cards (will be initialized in step)
	nth := 0
	if c.State != StateNew {
		nth = c.Reps
	}

	// Run the FSRS step function
	nextState := step(params.W[:], float64(elapsed), float64(rating), state, nth)

	card.Stability = nextState.Stability
	card.Difficulty = nextState.Difficulty

	// Compute next interval from stability and desired retention
	interval := nextInterval(params.W[:], nextState.Stability, params.RequestRetention)
	if interval < 0.001 {
		interval = 0.001
	}

	card.ScheduledDays = interval
	if card.ScheduledDays > params.MaximumInterval {
		card.ScheduledDays = params.MaximumInterval
	}
	card.Due = now.Add(time.Duration(card.ScheduledDays*24) * time.Hour)

	// Update reps and state
	switch rating {
	case RatingAgain:
		card.Lapses++
		card.State = StateRelearning
	case RatingHard, RatingGood, RatingEasy:
		if c.State == StateNew || c.State == StateLearning {
			card.State = StateReview
		}
	}
	card.Reps++

	log := ReviewLog{
		Rating:  rating,
		Elapsed: elapsed * 86400,
		Date:    now,
	}

	return card, log
}

// Retrievability returns the probability of recall after elapsed_days.
func (c Card) Retrievability(elapsedDays float64) float64 {
	if c.Stability < 1e-8 {
		return 0.0
	}
	return powerForgettingCurve(DefaultW[:], float64(elapsedDays), c.Stability)
}

// ── Core FSRS-5 functions (direct port from Rust) ──

// Constants matching Rust implementation
const S_MIN = 0.0
const S_MAX = 36500.0
const D_MIN = 1.0
const D_MAX = 10.0

func powerForgettingCurve(w []float64, t, s float64) float64 {
	decay := -w[20]
	factor := math.Exp(math.Log(0.9)/decay) - 1.0
	return math.Pow(t/s*factor+1.0, decay)
}

func nextInterval(w []float64, stability, desiredRetention float64) float64 {
	decay := -w[20]
	factor := math.Exp(math.Log(0.9)/decay) - 1.0
	return stability / factor * (math.Pow(desiredRetention, 1.0/decay) - 1.0)
}

func initStability(w []float64, rating int) float64 {
	// w[0..3] for ratings 1..4
	idx := rating - 1
	if idx < 0 {
		idx = 0
	}
	if idx > 3 {
		idx = 3
	}
	return w[idx]
}

func initDifficulty(w []float64, rating int) float64 {
	// D0(rating) = w[4] - exp(w[5] * (rating - 1)) + 1.0
	return w[4] - math.Exp(w[5]*float64(rating-1)) + 1.0
}

func meanRevision(w []float64, newD float64) float64 {
	// w[7] * (init_difficulty(4) - new_d) + new_d
	return w[7]*(initDifficulty(w, 4)-newD) + newD
}

func linearDamping(deltaD, oldD float64) float64 {
	return (10.0 - oldD) * deltaD / 9.0
}

func nextDifficulty(w []float64, difficulty, rating float64) float64 {
	deltaD := -w[6] * (rating - 3.0)
	return difficulty + linearDamping(deltaD, difficulty)
}

func stabilityAfterSuccess(w []float64, lastS, lastD, r, rating float64) float64 {
	hardPenalty := 1.0
	if rating == 2.0 {
		hardPenalty = w[15]
	}
	easyBonus := 1.0
	if rating == 4.0 {
		easyBonus = w[16]
	}

	return lastS * (math.Exp(w[8])*
		(11.0-lastD)*
		math.Pow(lastS, -w[9])*
		(math.Exp((1.0-r)*w[10])-1.0)*
		hardPenalty*
		easyBonus + 1.0)
}

func stabilityAfterFailure(w []float64, lastS, lastD, r float64) float64 {
	newS := w[11] *
		math.Pow(lastD, -w[12]) *
		(math.Pow(lastS+1.0, w[13]) - 1.0) *
		math.Exp((1.0-r)*w[14])
	// min(new_s, last_s / exp(w[17]*w[18]))
	newSMin := lastS / math.Exp(w[17]*w[18])
	if newS > newSMin {
		newS = newSMin
	}
	return newS
}

func stabilityShortTerm(w []float64, lastS, rating float64) float64 {
	sinc := math.Exp(w[17]*(rating-3.0+w[18])) * math.Pow(lastS, -w[19])
	if rating >= 2.0 {
		if sinc < 1.0 {
			sinc = 1.0
		}
	}
	return lastS * sinc
}

func step(w []float64, deltaT, rating float64, state MemoryState, nth int) MemoryState {
	lastS := state.Stability
	if lastS < S_MIN {
		lastS = S_MIN
	}
	if lastS > S_MAX {
		lastS = S_MAX
	}
	lastD := state.Difficulty
	if lastD < D_MIN {
		lastD = D_MIN
	}
	if lastD > D_MAX {
		lastD = D_MAX
	}

	retrievability := powerForgettingCurve(w, deltaT, lastS)
	sAfterSuccess := stabilityAfterSuccess(w, lastS, lastD, retrievability, rating)
	sAfterFailure := stabilityAfterFailure(w, lastS, lastD, retrievability)
	sShortTerm := stabilityShortTerm(w, lastS, rating)

	var newS float64
	if rating == 1.0 {
		newS = sAfterFailure
	} else {
		newS = sAfterSuccess
	}
	if deltaT == 0.0 {
		newS = sShortTerm
	}

	newD := nextDifficulty(w, lastD, rating)
	newD = meanRevision(w, newD)
	if newD < D_MIN {
		newD = D_MIN
	}
	if newD > D_MAX {
		newD = D_MAX
	}

	// If this is the first review and no initial state provided
	if nth == 0 && state.Stability == 0.0 {
		initRating := int(rating)
		if initRating < 1 {
			initRating = 1
		}
		if initRating > 4 {
			initRating = 4
		}
		newS = initStability(w, initRating)
		newD = initDifficulty(w, initRating)
		if newD < D_MIN {
			newD = D_MIN
		}
		if newD > D_MAX {
			newD = D_MAX
		}
	}

	// Handle rating=0 (manual reschedule) — keep state unchanged
	if rating == 0.0 {
		newS = lastS
		newD = lastD
	}

	if newS < S_MIN {
		newS = S_MIN
	}
	if newS > S_MAX {
		newS = S_MAX
	}

	return MemoryState{Stability: newS, Difficulty: newD}
}
