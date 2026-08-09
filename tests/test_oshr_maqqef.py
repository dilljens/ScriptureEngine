"""Track A: OSHB maqqef preservation + token-integrity regression gate.

The Hebrew OT token layer (gematria.word_index) is load-bearing for the
alignment/cloze/passage layers, so restoring U+05BE maqqef must never change
per-verse token counts or word_index sequences. These tests pin that invariant.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.ingest import (
    OSHB_SOURCE,
    extract_hebrew_words_from_verse,
    verify_maqqef_token_integrity,
)

ROOT = Path(__file__).parent.parent
WLC_DIR = ROOT / "data" / "raw" / "morphhb" / "wlc"

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"


def _verse_xml(children):
    """Build an OSIS <verse> element from (tag, text, attrs) tuples."""
    verse = ET.Element(f"{NS}verse", {"osisID": "Gen.1.4"})
    for tag, text, attrs in children:
        child = ET.SubElement(verse, f"{NS}{tag}", attrs or {})
        child.text = text
    return verse


def test_maqqef_attaches_to_preceding_token_and_keeps_word_index():
    verse = _verse_xml([
        ("w", "וַיֹּ֥אמֶר", {"lemma": "559", "morph": "HVqw3ms"}),
        ("w", "אֱלֹהִ֖ים", {"lemma": "430", "morph": "HNcmpa"}),
        ("w", "אֶת", {"lemma": "853", "morph": "HTo"}),
        ("seg", "\u05be", {"type": "x-maqqef"}),
        ("w", "הָ/א֖וֹר", {"lemma": "d/216", "morph": "HTd/Ncbsa"}),
        ("w", "כִּי", {"lemma": "3588 a", "morph": "HC"}),
        ("seg", "\u05be", {"type": "x-maqqef"}),
        ("w", "ט֑וֹב", {"lemma": "2896 a", "morph": "HAamsa"}),
    ])
    tokens = extract_hebrew_words_from_verse(verse)
    # Same count as without maqqef; the seg is folded onto the PRECEDING token.
    assert [t["index"] for t in tokens] == [0, 1, 2, 3, 4, 5]
    assert tokens[2]["word"] == "אֶת\u05be"
    assert tokens[3]["word"] == "הָ/א֖וֹר"
    assert tokens[4]["word"] == "כִּי\u05be"
    assert tokens[5]["word"] == "ט֑וֹב"
    # lemma/morph survive on the maqqef-bearing token
    assert tokens[2]["lemma"] == "853"
    assert tokens[2]["morph"] == "HTo"


def test_maqqef_seg_without_preceding_word_is_ignored():
    verse = _verse_xml([
        ("seg", "\u05be", {"type": "x-maqqef"}),
        ("w", "א", {"lemma": "1", "morph": "HN"}),
    ])
    tokens = extract_hebrew_words_from_verse(verse)
    assert [t["index"] for t in tokens] == [0]
    assert tokens[0]["word"] == "א"


def test_non_maqqef_segs_are_ignored():
    verse = _verse_xml([
        ("w", "אֶת", {"lemma": "853", "morph": "HTo"}),
        ("seg", "x", {"type": "x-punct"}),
        ("w", "הָאוֹר", {"lemma": "216", "morph": "HNcbsa"}),
    ])
    tokens = extract_hebrew_words_from_verse(verse)
    assert [t["word"] for t in tokens] == ["אֶת", "הָאוֹר"]


def _has_live_data():
    return WLC_DIR.exists() and bool(list(WLC_DIR.glob("*.xml"))) and (
        ROOT / "data" / "processed" / "scripture.db"
    ).exists()


@pytest.fixture()
def scripture_ro():
    """Read-only connection to the production scripture DB (token layer)."""
    import sqlite3

    conn = sqlite3.connect("file:data/processed/scripture.db?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


_SKIP_LIVE = "pinned OSHB source and/or scripture DB not present"


@pytest.mark.skipif(not _has_live_data(), reason=_SKIP_LIVE)
def test_pinned_source_token_integrity_gate_passes(scripture_ro):
    """Every OT verse in the DB keeps the source's token count + word_index."""
    mismatches, stats = verify_maqqef_token_integrity(scripture_ro)
    assert mismatches == [], f"token drift vs pinned OSHB source: {mismatches[:5]}"
    assert stats["verses_checked"] > 20_000
    assert stats["maqqef_tokens_in_source"] > 10_000


@pytest.mark.skipif(not _has_live_data(), reason=_SKIP_LIVE)
def test_sampled_books_scope(scripture_ro):
    books = {"gen", "psa", "isa"}
    mismatches, stats = verify_maqqef_token_integrity(scripture_ro, sample_books=books)
    assert mismatches == []
    assert stats["verses_checked"] < 23_500  # scoped, not the whole OT


def test_pinned_source_metadata_is_recorded():
    assert OSHB_SOURCE["commit"] == "3d15126fb1ef74867fc1434be1942e837932691f"
    assert OSHB_SOURCE["wlc_manifest_sha256"].startswith("f32cf0c4")
