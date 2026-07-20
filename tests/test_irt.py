"""Tests for IRT calibration module — pure math, no DB required."""

import math
import pytest
from lib.assessment.irt import calibrate_item, estimate_ability
from web.routes.assessment import _fsrs_initial_stability, _fsrs_stability_after_success, _fsrs_stability_after_failure, _fsrs_next_interval


class TestCalibrateItem:
    def test_returns_same_params_below_min_responses(self):
        """Should return unchanged params when fewer than MIN_RESPONSES (5)."""
        result = calibrate_item(0.0, 1.0, 0.15, 0.10, total_attempts=3, correct_count=2)
        assert result == (0.0, 1.0, 0.15, 0.10)

    def test_updates_difficulty_with_sufficient_data(self):
        """High accuracy should decrease difficulty (make item easier)."""
        diff, disc, guess, slip = calibrate_item(0.0, 1.0, 0.15, 0.10, total_attempts=10, correct_count=9)
        # 90% accuracy → difficulty should decrease (get easier)
        assert diff < 0.0

    def test_updates_guess_parameter(self):
        """Guess should approach observed proportion for low performers."""
        diff, disc, guess, slip = calibrate_item(0.0, 1.0, 0.10, 0.10, total_attempts=100, correct_count=40)
        # 40% accuracy with high attempts → guess should increase (user is guessing)
        # The update blends prior guess with observed data
        assert guess > 0.10  # guess should increase from 0.10 toward 0.40

    def test_bounds_parameters(self):
        """Parameters should stay within reasonable bounds."""
        diff, disc, guess, slip = calibrate_item(5.0, 10.0, 0.9, 0.9, total_attempts=200, correct_count=100)
        assert -2.0 <= diff <= 2.0
        assert 0.3 <= disc <= 3.0
        assert 0.05 <= guess <= 0.4
        assert 0.02 <= slip <= 0.3


class TestFSRSScheduling:
    def test_initial_stability_increases_with_rating(self):
        s1 = _fsrs_initial_stability(1)
        s4 = _fsrs_initial_stability(4)
        assert s1 < s4
        assert s1 == 0.3
        assert s4 == 4.0

    def test_stability_grows_after_success(self):
        s = _fsrs_stability_after_success(1.0, 3)
        assert s > 1.0  # Good rating should increase stability

    def test_stability_decays_after_failure(self):
        s = _fsrs_stability_after_failure(1.0, 1)
        assert s < 1.0  # Again rating should decrease stability

    def test_next_interval_min_one(self):
        i1 = _fsrs_next_interval(1.0)
        assert i1 >= 1

    def test_next_interval_scales_with_stability(self):
        i10 = _fsrs_next_interval(10.0)
        i100 = _fsrs_next_interval(100.0)
        assert i100 > i10  # Higher stability → longer interval
        assert i10 >= 1


class TestEstimateAbility:
    def test_returns_zero_with_no_responses(self, monkeypatch):
        """Should return ability=0 when no response data."""
        class MockConn:
            def execute(self, *args, **kwargs):
                class MockCursor:
                    def fetchall(self): return []
                return MockCursor()
        
        result = estimate_ability(MockConn(), user_id="test")
        assert result["ability"] == 0.0
        assert result["total_responses"] == 0

    def test_estimate_improves_with_correct_responses(self, monkeypatch):
        """More correct responses should yield higher ability."""
        # Create mock DB response rows
        rows = [
            {"question_id": 1, "correct": 1, "attempts": 1,
             "difficulty": 0.0, "discrimination": 1.0, "guess_param": 0.15, "slip_param": 0.10},
        ]
        
        class MockCursor:
            def fetchall(self): return rows
        class MockConn:
            def execute(self, *args, **kwargs): return MockCursor()
        
        result = estimate_ability(MockConn(), user_id="test")
        assert result["total_responses"] == 1
        assert result["ability"] > 0.0  # Got it right → positive ability
        assert result["se"] > 0  # Standard error should be positive
