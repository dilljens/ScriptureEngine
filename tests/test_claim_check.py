"""Track A3 stage 1: deterministic quotation-vs-verse checks (lib/controls/claims.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.controls.claims import check_quotations, extract_refs, normalize


KJV_PSA_69_14 = (
    "Deliver me out of the mire, and let me not sink: let me be delivered "
    "from them that hate me, and out of the deep waters."
)

VERSES = {
    "psa.69.14": KJV_PSA_69_14,
    "matt.4.10": "Then saith Jesus unto him, Get thee hence, Satan: for it "
                 "is written, Thou shalt worship the Lord thy God, and him "
                 "only shalt thou serve.",
}


def _lookup(ref):
    return VERSES.get(ref)


def test_supported_quotation_passes():
    answer = (
        'Peter is restating the wilderness temptation. Jesus says "Get thee '
        'hence, Satan" in matt.4.10.'
    )
    result = check_quotations(answer, _lookup)
    assert result["quotes_checked"] == 1
    assert result["supported"] == 1
    assert result["unsupported"] == []


def test_misattributed_or_invented_quotation_is_flagged():
    answer = (
        'As the psalmist prays, "Deliver me out of the mire, and let me not '
        'sink" in psa.23.1.'
    )  # real words, wrong psalm
    result = check_quotations(answer, _lookup)
    assert result["quotes_checked"] == 1
    assert result["supported"] == 0
    assert result["unsupported"][0]["ref"] == "psa.23.1"


def test_elided_quotation_matches_on_fragments():
    answer = (
        'The prayer continues "Deliver me out of the mire ... out of the '
        'deep waters" (psa.69.14).'
    )
    result = check_quotations(answer, _lookup)
    assert result["supported"] == 1
    assert result["quotes_checked"] == 1


def test_unavailable_verse_text_counts_as_unsupported_not_pass():
    answer = 'Paul writes "Be anxious for nothing" in col.99.9.'
    result = check_quotations(answer, lambda ref: None)
    assert result["quotes_checked"] == 1
    assert result["supported"] == 0
    assert len(result["unsupported"]) == 1


def test_short_quotes_and_refless_quotes_are_ignored():
    answer = 'He says "Amen" and "Come, Lord Jesus" without a reference nearby.'
    result = check_quotations(answer, _lookup)
    assert result["quotes_checked"] == 0
    assert result["refs_seen"] == []


def test_lookup_budget_is_bounded():
    refs = " ".join(f"x.{i}.1" for i in range(12))
    answer = " ".join(
        f'"some long quoted span number {i} here now" ({r})'
        for i, r in enumerate(refs.split())
    )
    calls = {"n": 0}

    def counting_lookup(_ref):
        calls["n"] += 1
        return None

    check_quotations(answer, counting_lookup, max_lookups=6)
    assert calls["n"] <= 6


def test_extract_refs_handles_numeric_book_ids():
    text = "See gen.1.1 then dc88.88.67 and 2ne.4.3; skip 3.14.15 and v2.x.y"
    assert extract_refs(text) == ["gen.1.1", "dc88.88.67", "2ne.4.3"]


def test_normalize_strips_punctuation_and_case():
    assert normalize("Get thee Hence, Satan!") == normalize("get thee hence satan")
