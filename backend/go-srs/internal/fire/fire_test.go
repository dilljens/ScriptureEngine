package fire

import (
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

func TestNoBoostsForAgainOrHard(t *testing.T) {
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

func TestSingleHopBoost(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) {
		return conns[verseID], nil
	}
	hasCard := func(verseID string) (int64, bool) {
		id, ok := cards[verseID]
		return id, ok
	}

	boosts, err := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)
	if err != nil {
		t.Fatal(err)
	}

	if len(boosts) != 1 {
		t.Fatalf("Expected 1 boost, got %d", len(boosts))
	}

	// chainWeight = 1.0 * 0.8 = 0.8, multiplier = 0.5 (Good)
	// boost = 0.8 * 0.5 = 0.4
	want := 0.4
	if boosts[0].Boost != want {
		t.Errorf("Boost = %f, want %f (chain=0.8 * mult=0.5)", boosts[0].Boost, want)
	}
	if boosts[0].VerseID != "john.1.1" {
		t.Errorf("Target = %s, want john.1.1", boosts[0].VerseID)
	}
	if boosts[0].CardID != 2 {
		t.Errorf("CardID = %d, want 2", boosts[0].CardID)
	}
}

func TestEasyGivesFullBoost(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	cards := map[string]int64{"john.1.1": 2}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	boosts, _ := eng.ComputeBoosts("gen.1.1", 4, getConns, hasCard)

	// Easy: multiplier = 1.0, so boost = 0.8 * 1.0 = 0.8
	if len(boosts) > 0 && boosts[0].Boost != 0.8 {
		t.Errorf("Easy boost = %f, want 0.8", boosts[0].Boost)
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

func TestMultiHopBoost(t *testing.T) {
	eng := New()

	// gen.1.1 --direct_quotation(0.8)--> john.1.1 --allusion(0.3)--> gen.1.3
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

	// Direct: gen.1.1 → john.1.1: 1.0 * 0.8 * 0.5 = 0.4
	if b, ok := boostMap["john.1.1"]; !ok || b < 0.39 || b > 0.41 {
		t.Errorf("john.1.1 boost = %f, want ~0.4", b)
	}

	// Multi-hop: gen.1.1 → john.1.1 → gen.1.3: 1.0 * 0.8 * 0.3 * 0.5 = 0.12
	if b, ok := boostMap["gen.1.3"]; !ok || b < 0.11 || b > 0.13 {
		t.Errorf("gen.1.3 boost = %f, want ~0.12", b)
	}
}

func TestBestPathWins(t *testing.T) {
	eng := New()

	// Two paths to gen.1.3: direct (weight 0.2) and via john.1.1 (weight 0.8*0.3=0.24)
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
			// Should use best path: 0.24 (via john) not 0.2 (direct echo)
			// With good multiplier 0.5: 0.24 * 0.5 = 0.12
			if b.Boost < 0.11 || b.Boost > 0.13 {
				t.Errorf("gen.1.3 boost = %f, want ~0.12 (best path)", b.Boost)
			}
		}
	}
}

func TestNoCardNoBoost(t *testing.T) {
	eng := New()

	conns := map[string][]Connection{
		"gen.1.1": {{SourceVerse: "gen.1.1", TargetVerse: "john.1.1", Type: "direct_quotation"}},
	}
	// No card for john.1.1
	cards := map[string]int64{}

	getConns := func(verseID string) ([]Connection, error) { return conns[verseID], nil }
	hasCard := func(verseID string) (int64, bool) { id, ok := cards[verseID]; return id, ok }

	boosts, _ := eng.ComputeBoosts("gen.1.1", 3, getConns, hasCard)

	if len(boosts) != 0 {
		t.Errorf("Should be 0 boosts when target has no card, got %d", len(boosts))
	}
}
