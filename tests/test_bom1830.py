"""Tests for tools/bom1830.py — 1830-vs-modern sync + Son-of insertions.

The four EXPECTED insertions are the well-known 1837 second-edition changes
(Skousen): 1 Ne 11:18, 11:21, 11:32, 13:40. If this set ever grows, the doctrine
didn't change — the aligner probably regressed. Check snippets first.
"""

import json
import subprocess
import sys

import pytest

TOOL = ["python3", "tools/bom1830.py"]


def run(payload):
    r = subprocess.run(TOOL + [json.dumps(payload)], capture_output=True,
                       text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_status_maps_all_books():
    res = run({"action": "status"})
    assert res["sections"] == 132
    assert res["books_mapped"] == 15
    assert res["unmapped"] == []


def test_lookup_finds_1830_reading():
    res = run({"action": "lookup", "verse": "1ne.11.18"})
    assert res["flag"] == "INSERTION_CANDIDATE"
    assert res["1830_section"].endswith("/Chapter 3")
    assert "mother of God" in res["1830_snippet"]
    assert res["align_score"] >= 0.5


def test_unchanged_verse_is_same():
    # Alma 11:32 already read "Son of God" in 1830 — guards against the
    # aligner crying insertion everywhere.
    res = run({"action": "lookup", "verse": "alma.11.32"})
    assert res["flag"] == "SAME"
    assert "Son of God" in res["1830_snippet"]


def test_sonof_finds_exactly_the_famous_four():
    # limit=14 covers every 1ne hit (string sort) while keeping the test fast.
    res = run({"action": "sonof", "limit": 14})
    found = {o["verse"] for o in res["verses"] if o["flag"] == "INSERTION_CANDIDATE"}
    assert found == {"1ne.11.18", "1ne.11.21", "1ne.11.32", "1ne.13.40"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
