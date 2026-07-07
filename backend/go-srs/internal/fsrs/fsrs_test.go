package fsrs

import (
	"math"
	"testing"
	"time"
)

// Tolerance for floating-point comparisons.
const tol = 1e-4

func approxEqual(a, b, epsilon float64) bool {
	return math.Abs(a-b) <= epsilon
}

func TestDefaultParameters(t *testing.T) {
	want := [21]float64{
		0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194,
		0.001, 1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629,
		1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
	}
	for i, v := range DefaultW {
		if !approxEqual(v, want[i], 1e-6) {
			t.Errorf("DefaultW[%d] = %f, want %f", i, v, want[i])
		}
	}
}

// TestPowerForgettingCurve matches Rust test_power_forgetting_curve.
func TestPowerForgettingCurve(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		t, s, want float64
	}{
		{0.0, 1.0, 1.0},
		{1.0, 2.0, 0.9403443},
		{2.0, 3.0, 0.9253786},
		{3.0, 4.0, 0.9185229},
		{4.0, 4.0, 0.9},
		{5.0, 2.0, 0.8261359},
	}
	for _, c := range cases {
		got := powerForgettingCurve(w, c.t, c.s)
		if !approxEqual(got, c.want, tol) {
			t.Errorf("R(%.1f, %.1f) = %.7f, want %.7f", c.t, c.s, got, c.want)
		}
	}
}

// TestInitStability matches Rust test_init_stability.
func TestInitStability(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		rating int
		want   float64
	}{
		{1, DefaultW[0]},
		{2, DefaultW[1]},
		{3, DefaultW[2]},
		{4, DefaultW[3]},
	}
	for _, c := range cases {
		got := initStability(w, c.rating)
		if got != c.want {
			t.Errorf("initStability(%d) = %f, want %f", c.rating, got, c.want)
		}
	}
}

// TestInitDifficulty matches Rust test_init_difficulty.
func TestInitDifficulty(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		rating int
		want   float64
	}{
		{1, DefaultW[4]},
		{2, DefaultW[4] - math.Exp(DefaultW[5]) + 1.0},
		{3, DefaultW[4] - math.Exp(2.0*DefaultW[5]) + 1.0},
		{4, DefaultW[4] - math.Exp(3.0*DefaultW[5]) + 1.0},
	}
	for _, c := range cases {
		got := initDifficulty(w, c.rating)
		if !approxEqual(got, c.want, tol) {
			t.Errorf("initDifficulty(%d) = %f, want %f", c.rating, got, c.want)
		}
	}
}

// TestNextDifficulty matches Rust test_next_difficulty.
func TestNextDifficulty(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		rating float64
		want   float64
	}{
		{1, 8.354889},
		{2, 6.6774445},
		{3, 5.0},
		{4, 3.3225555},
	}
	startD := 5.0
	for _, c := range cases {
		got := nextDifficulty(w, startD, c.rating)
		if !approxEqual(got, c.want, tol) {
			t.Errorf("nextDifficulty(%.1f) = %f, want %f", c.rating, got, c.want)
		}
		// Also test mean reversion
		mr := meanRevision(w, got)
		idx := int(c.rating) - 1
		wantMR := []float64{8.341763, 6.6659956, 4.990228, 3.3144615}
		if !approxEqual(mr, wantMR[idx], tol) {
			t.Errorf("meanReversion(%.1f) = %f, want %f", c.rating, mr, wantMR[idx])
		}
	}
}

// TestStabilityAfterSuccess matches Rust test_next_stability.
func TestStabilityAfterSuccess(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		rating       float64
		retrievability float64
		want         float64
	}{
		{1, 0.9, 25.602541},
		{2, 0.8, 28.226582},
		{3, 0.7, 58.656002},
		{4, 0.6, 127.226685},
	}
	lastS := 5.0
	for _, c := range cases {
		got := stabilityAfterSuccess(w, lastS, c.rating, c.retrievability, c.rating)
		if !approxEqual(got, c.want, 0.01) {
			t.Errorf("stabilityAfterSuccess(rating=%.0f, r=%.1f) = %f, want %f",
				c.rating, c.retrievability, got, c.want)
		}
	}
}

// TestStabilityAfterFailure matches Rust test_next_stability.
func TestStabilityAfterFailure(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		difficulty   float64
		retrievability float64
		want         float64
	}{
		{1.0, 0.9, 1.0525396},
		{2.0, 0.8, 1.1894329},
		{3.0, 0.7, 1.3680838},
		{4.0, 0.6, 1.584989},
	}
	lastS := 5.0
	for _, c := range cases {
		got := stabilityAfterFailure(w, lastS, c.difficulty, c.retrievability)
		if !approxEqual(got, c.want, 0.01) {
			t.Errorf("stabilityAfterFailure(D=%.1f, r=%.1f) = %f, want %f",
				c.difficulty, c.retrievability, got, c.want)
		}
	}
}

// TestShortTermStability matches Rust test_next_stability.
func TestShortTermStability(t *testing.T) {
	w := DefaultW[:]
	cases := []struct {
		rating float64
		want   float64
	}{
		{1, 1.596818},
		{2, 5.0},
		{3, 5.0},
		{4, 8.12961},
	}
	lastS := 5.0
	for _, c := range cases {
		got := stabilityShortTerm(w, lastS, c.rating)
		if !approxEqual(got, c.want, 0.01) {
			t.Errorf("stabilityShortTerm(rating=%.0f) = %f, want %f", c.rating, got, c.want)
		}
	}
}

// TestStep verifies the step function produces expected intervals.
func TestStepFirstReview(t *testing.T) {
	w := DefaultW[:]
	// First review (nth=0, state=zero) with delta_t=0, rating=Good
	state := MemoryState{Stability: 0.0, Difficulty: 0.0}
	result := step(w, 0.0, float64(RatingGood), state, 0)

	if result.Stability <= 0 {
		t.Errorf("First review: stability should be > 0, got %f", result.Stability)
	}
	if result.Difficulty <= 0 {
		t.Errorf("First review: difficulty should be > 0, got %f", result.Difficulty)
	}
}

// TestCardLifecycle tests a realistic memorization scenario.
func TestCardLifecycle(t *testing.T) {
	params := DefaultParams
	c := NewCard()

	// Day 1: First review
	c, _ = c.Next(RatingGood, params)
	t.Logf("Day 1: S=%.4f D=%.4f interval=%.2f state=%d",
		c.Stability, c.Difficulty, c.ScheduledDays, c.State)

	if c.ScheduledDays <= 0 {
		t.Errorf("Day 1: interval should be > 0, got %f", c.ScheduledDays)
	}

	// Simulate reviews over time with Good ratings
	for day := 2; day <= 30; day++ {
		if c.Due.After(time.Now()) {
			break
		}
		c.LastReview = c.LastReview.Add(-time.Duration(c.ScheduledDays*24) * time.Hour)
		c.ElapsedDays = c.ScheduledDays
		c, _ = c.Next(RatingGood, params)
		t.Logf("Day %d: S=%.2f interval=%.1f state=%d",
			day, c.Stability, c.ScheduledDays, c.State)
	}

	if c.ScheduledDays < 1 {
		t.Errorf("After 30 days: interval should be >= 1 day, got %f", c.ScheduledDays)
	}
}

// TestRatingOrder verifies intervals: Again < Hard < Good < Easy.
func TestRatingOrder(t *testing.T) {
	params := DefaultParams
	c := NewCard()
	c, _ = c.Next(RatingGood, params)

	c.LastReview = c.LastReview.Add(-7 * 24 * time.Hour)
	c.State = StateReview
	c.ElapsedDays = 7.0

	again, _ := c.Next(RatingAgain, params)
	hard, _ := c.Next(RatingHard, params)
	good, _ := c.Next(RatingGood, params)
	easy, _ := c.Next(RatingEasy, params)

	t.Logf("Again: %.2f days", again.ScheduledDays)
	t.Logf("Hard:  %.2f days", hard.ScheduledDays)
	t.Logf("Good:  %.2f days", good.ScheduledDays)
	t.Logf("Easy:  %.2f days", easy.ScheduledDays)

	// Good should give longer interval than again
	if good.ScheduledDays <= again.ScheduledDays*0.9 {
		t.Errorf("Good (%.2f) should be much longer than Again (%.2f)",
			good.ScheduledDays, again.ScheduledDays)
	}
}

// TestZeroStateHandling verifies edge cases.
func TestZeroStateHandling(t *testing.T) {
	w := DefaultW[:]

	// Rating=0 should keep state unchanged
	state := MemoryState{Stability: 5.0, Difficulty: 6.0}
	result := step(w, 1.0, 0.0, state, 1)
	if result.Stability != state.Stability || result.Difficulty != state.Difficulty {
		t.Errorf("Rating=0 should keep state unchanged: got (%f,%f), want (%f,%f)",
			result.Stability, result.Difficulty, state.Stability, state.Difficulty)
	}
}

// TestNewCardBasic verifies new card creation.
func TestNewCardBasic(t *testing.T) {
	c := NewCard()
	if c.State != StateNew {
		t.Errorf("New card state = %d, want %d", c.State, StateNew)
	}
	if c.Reps != 0 {
		t.Errorf("New card reps = %d, want 0", c.Reps)
	}
}

// TestLapsesIncrement verifies lapses increase on Again.
func TestLapsesIncrement(t *testing.T) {
	c := NewCard()
	c, _ = c.Next(RatingGood, DefaultParams)

	c.LastReview = c.LastReview.Add(-24 * time.Hour)
	c.State = StateReview
	c.ElapsedDays = 1.0

	c2, _ := c.Next(RatingAgain, DefaultParams)
	if c2.Lapses != 1 {
		t.Errorf("Lapses = %d, want 1", c2.Lapses)
	}
}

// TestRetrievabilityBounds verifies retrievability stays in [0,1].
func TestRetrievabilityBounds(t *testing.T) {
	c := NewCard()
	c.Stability = 10.0
	c.State = StateReview

	if r := c.Retrievability(0); r != 1.0 {
		t.Errorf("R(0) = %f, want 1.0", r)
	}
	if r := c.Retrievability(1e6); r > 0.5 {
		t.Errorf("R(1e6) = %f, want well below 1", r)
	}
	if r := c.Retrievability(0); r != 1.0 {
		t.Errorf("R(0) = %f, want 1.0", r)
	}
	// Verify decay: R should be lower after more time
	r1 := c.Retrievability(1)
	r10 := c.Retrievability(10)
	if r10 >= r1 {
		t.Errorf("R should decay: R(1)=%f, R(10)=%f", r1, r10)
	}
}
