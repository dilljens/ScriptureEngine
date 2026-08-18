"""Tests for access-modulated temporal decay (lib/controls/temporal.py).

Track C1: access_count slows confidence decay. Backward compatibility:
access_count defaults to 0 → identical output to the pre-change behavior.
"""
from lib.controls.temporal import (
    apply_temporal_decay,
    get_staleness,
    needs_revalidation,
    revalidate_connection_row,
)


class TestAccessZeroBackCompat:
    """access_count=0 must be identical to the pre-change behavior."""

    def test_decay_unchanged_with_zero_access(self):
        kw = {"discovered_by": "algorithm", "created_at": "2018-06-15"}
        assert apply_temporal_decay(0.8, **kw) == apply_temporal_decay(0.8, access_count=0, **kw)

    def test_decay_matches_half_life_formula(self):
        # algorithm half-life = 2y. Confidence 1.0 created exactly one half-life
        # ago decays to ~0.5.
        import datetime

        created = (datetime.datetime.now() - datetime.timedelta(days=365 * 2)).strftime("%Y-%m-%d")
        assert apply_temporal_decay(1.0, "algorithm", created, access_count=0) == 0.5

    def test_text_never_decays_even_with_access(self):
        assert apply_temporal_decay(0.9, "text", "2010-01-01", access_count=0) == 0.9
        assert apply_temporal_decay(0.9, "text", "2010-01-01", access_count=50) == 0.9

    def test_revalidate_connection_row_unchanged(self):
        row = {"confidence": 0.7, "discovered_by": "llm", "created_at": "2020-01-01"}
        assert revalidate_connection_row(row)["decayed_confidence"] == apply_temporal_decay(
            0.7, "llm", "2020-01-01", access_count=0
        )

    def test_staleness_zero_access_matches_original(self):
        assert get_staleness("2018-01-01", "algorithm") == get_staleness(
            "2018-01-01", "algorithm", access_count=0
        )


class TestAccessSlowsDecay:
    def test_access_count_slows_confidence_decay(self):
        """More reads → higher retained confidence (slower effective age)."""
        created = "2018-01-01"  # ~8.6y ago
        base = apply_temporal_decay(1.0, "algorithm", created, access_count=0)
        read10 = apply_temporal_decay(1.0, "algorithm", created, access_count=10)
        read50 = apply_temporal_decay(1.0, "algorithm", created, access_count=50)
        assert read10 > base
        assert read50 > read10
        # Fully-damped effective age: 8.6 / (1 + 50*0.2) = 8.6/11 ≈ 0.78y
        assert read50 > 0.7

    def test_effective_years_damping_constant(self):
        """Effective age halves at ~5 reads: years / (1 + access*0.2)."""
        created = "2015-01-01"  # ~11.6y ago
        raw = apply_temporal_decay(1.0, "algorithm", created, access_count=0)
        five = apply_temporal_decay(1.0, "algorithm", created, access_count=5)
        # effective 11.6/2 = 5.8y vs 11.6y → decayed 0.5^(5.8/2)=0.134 vs 0.5^(11.6/2)=0.018
        assert five > raw * 4

    def test_staleness_fresher_with_access(self):
        """Read edge is never classified as staler than the unread edge."""
        created = "2015-01-01"  # algorithm half-life 2y → critical unread
        assert get_staleness(created, "algorithm", access_count=0) == "critical"
        # effective age 11.6/11 ≈ 1.05y → aging (between 1y and 2y)
        assert get_staleness(created, "algorithm", access_count=50) in ("fresh", "aging")

    def test_needs_revalidation_flips_with_access(self):
        created = "2014-01-01"  # very old
        assert needs_revalidation(created, "algorithm", access_count=0) is True
        assert needs_revalidation(created, "algorithm", access_count=100) is False

    def test_recent_connection_nearly_untouched(self):
        import datetime

        created = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        assert apply_temporal_decay(0.8, "algorithm", created, access_count=0) > 0.79
        assert apply_temporal_decay(0.8, "algorithm", created, access_count=0) == apply_temporal_decay(
            0.8, "algorithm", created, access_count=0
        )
