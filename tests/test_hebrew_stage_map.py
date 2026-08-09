"""Track A: 3-KP micro-scaffolding stage map (Phase 4).

Verifies the deterministic recognition → recall → production stage map exposed
in the lesson payload, and that lessons missing a stage fall back gracefully
(never block).
"""
import pytest

from web.routes.hebrew import KP_STAGE_ORDER, build_kp_stages, practice_stage


# ── 1. Type → stage classification ──

@pytest.mark.parametrize("qtype,expected", [
    ("multiple_choice", "recognition"),
    ("true_false", "recognition"),
    ("letter_recognition", "recognition"),
    ("classification", "recognition"),
    ("cloze", "recall"),
    ("transliteration", "recall"),
    ("contrast", "recall"),
    ("recall", "recall"),
    ("typing", "production"),
    ("sentence", "production"),
])
def test_practice_stage_maps_known_types(qtype, expected):
    assert practice_stage(qtype) == expected


def test_practice_stage_unknown_type_is_none():
    assert practice_stage("essay") is None
    assert practice_stage("") is None


# ── 2. Stage grouping is deterministic + falls back ──

def test_build_kp_stages_groups_and_sorts():
    items = [
        {"id": 2, "question_type": "recall", "difficulty": 0.6},
        {"id": 1, "question_type": "multiple_choice", "difficulty": 0.3},
        {"id": 4, "question_type": "typing", "difficulty": 0.7},
        {"id": 3, "question_type": "cloze", "difficulty": 0.4},
    ]
    stages = build_kp_stages(items)
    assert [s["stage"] for s in stages] == ["recognition", "recall", "production"]
    assert [s["count"] for s in stages] == [1, 2, 1]
    # recognition first, recall (sorted by difficulty), production last
    assert stages[0]["items"][0]["id"] == 1
    assert [i["id"] for i in stages[1]["items"]] == [3, 2]
    assert stages[2]["items"][0]["id"] == 4
    # every item carries its kp_stage annotation
    for s in stages:
        for it in s["items"]:
            assert it["kp_stage"] == s["stage"]


def test_build_kp_stages_omits_empty_stages():
    # Lesson with only MC items → only recognition present; KP2/KP3 skip.
    stages = build_kp_stages([
        {"id": 1, "question_type": "multiple_choice", "difficulty": 0.3},
        {"id": 2, "question_type": "multiple_choice", "difficulty": 0.4},
    ])
    assert [s["stage"] for s in stages] == ["recognition"]
    # Lesson with no items → no stages, never raises.
    assert build_kp_stages([]) == []
    # Unknown type items are ignored entirely.
    stages = build_kp_stages([{"id": 9, "question_type": "essay", "difficulty": 0.5}])
    assert stages == []


def test_stage_order_constant_matches_plan():
    assert KP_STAGE_ORDER == ["recognition", "recall", "production"]


# ── 3. Lesson payload integration ──

def test_lesson_payload_exposes_kp_stages(client):
    r = client.get("/api/v1/hebrew/lesson/shin")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "kp_stages" in data
    stages = data["kp_stages"]
    assert stages, "shin should have staged practice"
    # Every lesson stage is one of the three KP stages, in plan order.
    stage_names = [s["stage"] for s in stages]
    assert stage_names == [name for name in KP_STAGE_ORDER if name in stage_names]
    # The top-level practice items carry their stage annotation.
    for it in data["practice_items"]:
        assert it["kp_stage"] in KP_STAGE_ORDER
    # Stage items are deterministic (sorted by difficulty) and non-empty.
    for s in stages:
        assert s["count"] > 0
        assert s["count"] == len(s["items"])
        diffs = [it["difficulty"] or 0 for it in s["items"]]
        assert diffs == sorted(diffs)


def test_lesson_payload_recognizes_all_three_stages_for_letters(client):
    r = client.get("/api/v1/hebrew/lesson/bet")
    assert r.status_code == 200
    stages = r.json()["data"]["kp_stages"]
    assert {s["stage"] for s in stages} == {"recognition", "recall", "production"}
