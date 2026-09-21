"""P2-D seed: TruthfulScriptureQA v1 (20 cases) against stage-1 checker.

The seed pins what the deterministic stage (lib/controls/claims.py) catches
and — equally important — what it cannot: unquoted sayings (SAY-03, GEM-02,
GEM-03) pass silently and need the NLI/entailment stage; SAY-04 documents a
substring-matching limit. Positive controls guard against over-blocking.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.controls.claims import check_quotations

SEED_PATH = Path(__file__).resolve().parent / "truthful_scripture_qa_seed.json"


def _load():
    return json.loads(SEED_PATH.read_text())["cases"]


def _run(case):
    verses = case["verses"]
    return check_quotations(case["answer"], lambda ref: verses.get(ref))


def test_seed_case_expectations():
    for case in _load():
        result = _run(case)
        exp = case["expect"]
        assert result["quotes_checked"] == exp["quotes_checked"], case["id"]
        assert result["supported"] == exp["supported"], case["id"]
        got_refs = sorted(u["ref"] for u in result["unsupported"])
        assert got_refs == sorted(exp["unsupported_refs"]), case["id"]


def test_misattributed_verses_all_flagged():
    for case in _load():
        if case["category"] == "misattributed_verse":
            assert _run(case)["supported"] == 0, case["id"]


def test_positive_controls_never_flagged():
    for case in _load():
        if case["category"] == "positive_control":
            result = _run(case)
            assert result["supported"] == 1 and not result["unsupported"], case["id"]


def test_stage1_gaps_documented_not_silent():
    """Unquoted adversarial claims must be PRESENT in the seed as gaps (so the
    NLI stage knows its backlog), even though stage 1 cannot flag them."""
    for case in _load():
        is_gap = case["expect"]["quotes_checked"] == 0
        is_control = case["category"] == "positive_control"
        if is_gap and not is_control:
            assert "GAP" in case["note"], case["id"]
        if "GAP" in case["note"]:
            assert is_gap, case["id"]
