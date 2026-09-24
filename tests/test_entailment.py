"""Stage-2 entailment verifier: prompts, strict parsing, bounded opinions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.controls.entailment import (
    MAX_ITEMS,
    entailment_prompt,
    parse_verdict,
    second_opinion,
)


def test_parse_verdict_accepts_all_three():
    assert parse_verdict('{"verdict": "supported", "reason": "verbatim"}')[
        "verdict"] == "supported"
    assert parse_verdict('{"verdict": "unsupported", "reason": "absent"}')[
        "verdict"] == "unsupported"
    assert parse_verdict('{"verdict": "abstain", "reason": "unclear"}')[
        "verdict"] == "abstain"


def test_parse_verdict_fails_open():
    for raw in ("", "not json", "[1,2]", '{"verdict": "maybe"}',
                '{"nope": 1}', None):
        assert parse_verdict(raw)["verdict"] == "abstain"


def test_second_opinion_confirms_and_confirms_not():
    items = [{"quote": "real words here now", "ref": "a.1.1"},
             {"quote": "invented words here now", "ref": "a.1.2"}]
    texts = {"a.1.1": "real words here now", "a.1.2": "other text entirely"}
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        if "real words" in prompt and "other text" not in prompt.split(
                "Actual verse text:")[1]:
            return '{"verdict": "supported", "reason": "verbatim"}'
        return '{"verdict": "unsupported", "reason": "absent"}'

    out = second_opinion(items, texts, fake_llm)
    assert [o["verdict"] for o in out] == ["supported", "unsupported"]
    assert len(calls) == 2


def test_second_opinion_abstains_on_missing_text_and_llm_failure():
    def boom(prompt):
        raise RuntimeError("provider down")

    out = second_opinion([{"quote": "some long quote here now", "ref": "x.9.9"}],
                         {}, boom)
    assert out[0]["verdict"] == "abstain"
    out = second_opinion([{"quote": "some long quote here now", "ref": "x.9.9"}],
                         {"x.9.9": "text"}, boom)
    assert out[0]["verdict"] == "abstain"


def test_second_opinion_bounded():
    items = [{"quote": f"quoted span number {i} here now", "ref": f"r.{i}.1"}
             for i in range(10)]
    texts = {f"r.{i}.1": "unrelated" for i in range(10)}
    seen = []
    second_opinion(items, texts,
                   lambda p: seen.append(p) or '{"verdict": "abstain"}')
    assert len(seen) == MAX_ITEMS


def test_prompt_is_bounded_and_contains_evidence():
    p = entailment_prompt("q" * 5000, "a.1.1", "v" * 5000)
    assert len(p) <= 1500 and "a.1.1" in p
