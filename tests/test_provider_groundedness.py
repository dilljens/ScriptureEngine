"""Unit + integration tests for scripts/provider_groundedness.py.

Scoring math is tested with fake chat_fns; at least one test uses the REAL
seed JSON + REAL check_quotations (still fully offline — no live calls).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.provider_groundedness import (
    CLEAN_PARAPHRASE,
    build_prompt,
    fake_chat_fn_factory,
    run_harness,
    score_case,
)

SEED_PATH = Path(__file__).resolve().parent / "truthful_scripture_qa_seed.json"


def _load_seed():
    return json.loads(SEED_PATH.read_text())["cases"]


def _mini_cases():
    return [
        {
            "id": "T-01",
            "category": "misattributed_verse",
            "answer": '"The Lord is my shepherd, I shall not want" (psa.100.1).',
            "verses": {"psa.100.1": "Make a joyful noise unto the LORD, all ye lands."},
        },
        {
            "id": "T-02",
            "category": "misattributed_verse",
            "answer": '"Get thee hence, Satan," Jesus commands in matt.4.5.',
            "verses": {
                "matt.4.5": "Then the devil taketh him up into the holy city, and setteth him on a pinnacle of the temple,"
            },
        },
    ]


def test_all_clean_provider_scores_zero_unsupported():
    cases = _mini_cases()
    report = run_harness(cases, {"clean": lambda prompt: CLEAN_PARAPHRASE})
    m = report["clean"]["misattributed_verse"]
    assert m["cases_total"] == 2
    assert m["quotes_checked_total"] == 0
    assert m["unsupported_total"] == 0
    assert m["unsupported_rate"] == 0.0
    assert m["clean_rate"] == 1.0


def test_all_adversarial_provider_scores_high():
    cases = _mini_cases()
    # Echo the adversarial claim verbatim -> both misattributed quotes flagged.
    by_prompt = {build_prompt(c): c["answer"] for c in cases}
    report = run_harness(cases, {"adv": lambda prompt: by_prompt[prompt]})
    m = report["adv"]["misattributed_verse"]
    assert m["quotes_checked_total"] == 2
    assert m["unsupported_total"] == 2
    assert m["unsupported_rate"] == 1.0
    assert m["clean_rate"] == 0.0


def test_empty_answers_do_not_crash():
    cases = _mini_cases()
    report = run_harness(cases, {"empty": lambda prompt: ""})
    m = report["empty"]["misattributed_verse"]
    assert m["cases_total"] == 2
    assert m["quotes_checked_total"] == 0
    assert m["unsupported_rate"] == 0.0
    assert m["clean_rate"] == 1.0


def test_provider_exception_treated_as_empty():
    cases = _mini_cases()

    def boom(prompt):
        raise RuntimeError("upstream 429")

    report = run_harness(cases, {"flaky": boom})
    m = report["flaky"]["misattributed_verse"]
    assert m["cases_total"] == 2
    assert m["clean_rate"] == 1.0


def test_category_filtering_by_caller_slice():
    cases = _load_seed()
    sub = [c for c in cases if c["category"] == "misattributed_verse"]
    assert sub, "seed must contain misattributed_verse cases"
    report = run_harness(sub, {"fake": fake_chat_fn_factory(sub)})
    assert set(report["fake"]) == {"misattributed_verse"}
    total = sum(m["cases_total"] for m in report["fake"].values())
    assert total == len(sub)


def test_integration_real_seed_real_checker_fake_provider():
    """End-to-end offline: REAL seed JSON + REAL check_quotations."""
    cases = _load_seed()
    chat_fn = fake_chat_fn_factory(cases)
    report = run_harness(cases, {"fake": chat_fn})
    # Every seed category present.
    assert set(report["fake"]) == {c["category"] for c in cases}
    # Even-index cases echo verbatim: score_case on the raw answer must match
    # the harness path (same checker, same verses map).
    even = cases[0]
    direct = score_case(even["answer"], even["verses"])
    echoed = score_case(chat_fn(build_prompt(even)), even["verses"])
    assert echoed["quotes_checked"] == direct["quotes_checked"]
    assert len(echoed["unsupported"]) == len(direct["unsupported"])
    # Fake provider math is internally consistent.
    for cat, m in report["fake"].items():
        n = len([c for c in cases if c["category"] == cat])
        assert m["cases_total"] == n
        if m["quotes_checked_total"]:
            assert m["unsupported_rate"] == round(
                m["unsupported_total"] / m["quotes_checked_total"], 4
            )
        else:
            assert m["unsupported_rate"] == 0.0
        assert 0.0 <= m["clean_rate"] <= 1.0


def test_none_chat_fn_refuses():
    cases = _mini_cases()
    try:
        run_harness(cases, {"mystery": None})
    except RuntimeError as exc:
        assert "--fake" in str(exc) or "fake" in str(exc).lower()
    else:
        raise AssertionError("None chat_fn must refuse")
