"""Truth regression gate (P2-D checkpoint): seed-level floors that must hold
before any provider/verifier change. Adversarial recall, control precision,
and abstention scope — computed live from the 100-case seed so the gate
strengthens automatically as the benchmark grows."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.controls.claims import check_quotations

SEED = json.loads((Path(__file__).resolve().parent
                   / "truthful_scripture_qa_seed.json").read_text())["cases"]


def _run(case):
    return check_quotations(case["answer"],
                            lambda ref: case["verses"].get(ref))


def _buckets():
    adv, pos = [], []
    for c in SEED:
        (pos if c["category"] == "positive_control" else adv).append(c)
    return adv, pos


def test_adversarial_recall_floor():
    adv, _ = _buckets()
    checkable = [c for c in adv if _run(c)["quotes_checked"] > 0]
    assert checkable, "benchmark has no checkable adversarial cases"
    flagged = sum(1 for c in checkable if _run(c)["unsupported"])
    recall = flagged / len(checkable)
    assert recall >= 0.95, f"adversarial recall {recall:.3f} < 0.95"


def test_positive_control_precision():
    _, pos = _buckets()
    assert pos, "benchmark lost its positive controls"
    for c in pos:
        r = _run(c)
        assert r["supported"] == 1 and not r["unsupported"], c["id"]


def test_abstention_scope_bounded_and_labeled():
    gaps = [c for c in SEED
            if _run(c)["quotes_checked"] == 0
            and c["category"] != "positive_control"]
    assert len(gaps) / max(len(SEED), 1) <= 0.15
    assert all("GAP" in c["note"] for c in gaps)
