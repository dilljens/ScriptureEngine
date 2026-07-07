package fire

import (
	"math"
	"testing"
)

func TestConnectionWeights(t *testing.T) {
	tests := []struct {
		connType string
		want     float64
	}{
		{"direct_quotation", 0.8},
		{"same_lemma", 0.4},
		{"allusion", 0.3},
		{"echo", 0.2},
		{"unknown_type", 0.2},
	}
	for _, tc := range tests {
		got := ConnectionWeight(tc.connType)
		if got != tc.want {
			t.Errorf("ConnectionWeight(%q) = %f, want %f", tc.connType, got, tc.want)
		}
	}
}

func TestRatingMultiplier(t *testing.T) {
	tests := []struct {
		rating int
		want   float64
	}{
		{1, 0.0},
		{2, 0.0},
		{3, 0.5},
		{4, 1.0},
	}
	for _, tc := range tests {
		got := RatingMultiplier(tc.rating)
		if got != tc.want {
			t.Errorf("RatingMultiplier(%d) = %f, want %f", tc.rating, got, tc.want)
		}
	}
}

func TestPenaltyMultiplier(t *testing.T) {
	tests := []struct {
		rating int
		want   float64
	}{
		{1, 1.0},
		{2, 0.3},
		{3, 0.0},
		{4, 0.0},
	}
	for _, tc := range tests {
		got := PenaltyMultiplier(tc.rating)
		if got != tc.want {
			t.Errorf("PenaltyMultiplier(%d) = %f, want %f", tc.rating, got, tc.want)
		}
	}
}

func TestEarlyDiscount(t *testing.T) {
	tests := []struct {
		boost         float64
		retrievability float64
		want          float64
	}{
		{1.0, 0.0, 1.0},    // forgotten → full credit
		{1.0, 0.5, 0.75},   // moderate → 75% credit
		{1.0, 0.8, 0.36},   // strong → 36% credit
		{1.0, 0.95, 0.0975}, // fresh → ~10% credit
		{1.0, 1.0, 0.0},    // perfect → no credit
		{0.5, 0.5, 0.375},  // partial boost at moderate retrievability
	}
	for _, tc := range tests {
		got := EarlyDiscount(tc.boost, tc.retrievability)
		if math.Abs(got-tc.want) > 0.001 {
			t.Errorf("EarlyDiscount(%.2f, %.2f) = %.4f, want %.4f", tc.boost, tc.retrievability, got, tc.want)
		}
	}
}

func TestNoCreditForAgainOrHard(t *testing.T) {
	eng := New()
	boosts, err := eng.ComputeBoosts("gen.1.1", 1, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(boosts) != 0 {
		t.Errorf("Again should give 0 boosts, got %d", len(boosts))
	}

	boosts, err = eng.ComputeBoosts("gen.1.1", 2, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(boosts) != 0 {
		t.Errorf("Hard should give 0 boosts, got %d", len(boosts))
	}
}

func TestNoPenaltyForGoodOrEasy(t *testing.T) {
	eng := New()
	pens, err := eng.ComputePenalties("gen.1.1", 3, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(pens) != 0 {
		t.Errorf("Good should give 0 penalties, got %d", len(pens))
	}

	pens, err = eng.ComputePenalties("gen.1.1", 4, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(pens) != 0 {
		t.Errorf("Easy should give 0 penalties, got %d", len(pens))
	}
}

func TestPenaltyOnAgain(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	pens, err := eng.ComputePenalties("gen.1.1", 1, getConns, hasCard)
	if err != nil {
		t.Fatal(err)
	}

	if len(pens) != 1 {
		t.Fatalf("Expected 1 penalty, got %d", len(pens))
	}

	// chainWeight = 1.0 * 0.8 = 0.8, multiplier = 1.0 (Again)
	// penalty = 0.8 * 1.0 = 0.8
	want := 0.8
	if pens[0].Boost != want {
		t.Errorf("Penalty = %f, want %f", pens[0].Boost, want)
	}
	if pens[0].VerseID != "john.1.1" {
		t.Errorf("Target = %s, want john.1.1", pens[0].VerseID)
	}
	if pens[0].CardID != 2 {
		t.Errorf("CardID = %d, want 2", pens[0].CardID)
	}
}

func TestPenaltyOnHard(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	pens, _ := eng.ComputePenalties("gen.1.1", 2, getConns, hasCard)

	// Hard: multiplier = 0.3, so penalty = 0.8 * 0.3 = 0.24
	if len(pens) > 0 && math.Abs(pens[0].Boost-0.24) > 0.001 {
		t.Errorf("Hard penalty = %f, want 0.24", pens[0].Boost)
	}
}

func TestEarlyDiscountInCreditFlow(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	// Without discount: boost = 0.8 * 0.5 = 0.4
	// With discount at R=0.8: 0.4 * (1 - 0.64) = 0.4 * 0.36 = 0.144
	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)

	if len(boosts) > 0 {
		rawBoost := boosts[0].Boost
		discountedBoost := EarlyDiscount(rawBoost, 0.8)
		t.Logf("Raw boost: %.4f, discounted (R=0.8): %.4f", rawBoost, discountedBoost)
		if discountedBoost >= rawBoost {
			t.Errorf("Discounted boost (%.4f) should be < raw (%.4f)", discountedBoost, rawBoost)
		}
	}
}

func TestSingleHopBoost(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)

	want := 0.4 // 0.8 chain * 0.5 Good multiplier
	if len(boosts) > 0 && boosts[0].Boost != want {
		t.Errorf("Boost = %f, want %f", boosts[0].Boost, want)
	}
}

func TestNoBoostForSelf(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "gen.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"gen.1.1": 1}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)
	if len(boosts) != 0 {
		t.Errorf("Self-connection should not produce boost, got %d", len(boosts))
	}
}

func TestNoPenaltyForSelf(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "gen.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"gen.1.1": 1}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	pens, _ := eng.ComputePenalties("gen.1.1", 1, getConns, hasCard)
	if len(pens) != 0 {
		t.Errorf("Self-connection should not produce penalty, got %d", len(pens))
	}
}

func TestMultiHopBoost(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
		"john.1.1": {{SourceVerse: "john.1.1", TargetVerse: "gen.1.3", Type: "allusion"}},
	}
	cards := map[string]int64{"john.1.1": 2, "gen.1.3": 3}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)

	boostMap := make(map[string]float64)
	for _, b := range boosts {
		boostMap[b.VerseID] = b.Boost
	}
	if b, ok := boostMap["john.1.1"]; !ok || b < 0.39 || b > 0.41 {
		t.Errorf("john.1.1 boost = %f, want ~0.4", b)
	}
	if b, ok := boostMap["gen.1.3"]; !ok || b < 0.11 || b > 0.13 {
		t.Errorf("gen.1.3 boost = %f, want ~0.12", b)
	}
}

func TestMultiHopPenalty(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
		"john.1.1": {{SourceVerse: "john.1.1", TargetVerse: "gen.1.3", Type: "allusion"}},
	}
	cards := map[string]int64{"john.1.1": 2, "gen.1.3": 3}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	pens, _ := eng.ComputePenalties("gen.1.1", 1, getConns, hasCard)

	penMap := make(map[string]float64)
	for _, p := range pens {
		penMap[p.VerseID] = p.Boost
	}
	// Direct: gen.1.1 → john.1.1: 1.0 * 0.8 * 1.0 = 0.8
	if b, ok := penMap["john.1.1"]; !ok || b < 0.79 || b > 0.81 {
		t.Errorf("john.1.1 penalty = %f, want ~0.8", b)
	}
	// Multi-hop: gen.1.1 → john.1.1 → gen.1.3: 1.0 * 0.8 * 0.3 * 1.0 = 0.24
	if b, ok := penMap["gen.1.3"]; !ok || b < 0.23 || b > 0.25 {
		t.Errorf("gen.1.3 penalty = %f, want ~0.24", b)
	}
}

func TestBestPathWins(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {
			{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"},
			{SourceVerse: "gen.1.1", TargetVerse: "gen.1.3", Type: "echo"},
		},
		"john.1.1": {{SourceVerse: "john.1.1", TargetVerse: "gen.1.3", Type: "allusion"}},
	}
	cards := map[string]int64{"john.1.1": 2, "gen.1.3": 3}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)

	for _, b := range boosts {
		if b.VerseID == "gen.1.3" {
			if b.Boost < 0.11 || b.Boost > 0.13 {
				t.Errorf("gen.1.3 boost = %f, want ~0.12 (best path)", b.Boost)
			}
		}
	}
}

func TestNoCardNoCredit(t *testing.T) {
	eng := New()
	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{}
	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }
	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)
	if len(boosts) != 0 {
		t.Errorf("Should be 0 boosts when target has no card, got %d", len(boosts))
	}
	pens, _ := eng.ComputePenalties("gen.1.1", 1, getConns, hasCard)
	if len(pens) != 0 {
		t.Errorf("Should be 0 penalties when target has no card, got %d", len(pens))
	}
}
