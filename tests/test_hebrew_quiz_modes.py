"""Quiz modes: single-script options, next-lesson shape, FSRS review mode.

Run: pytest tests/test_hebrew_quiz_modes.py -q
"""
import re

HEB = re.compile(r"[\u0590-\u05FF]")


def _script(s):
    return "he" if s and HEB.search(str(s)) else "lat"


def test_lesson_quiz_options_single_script(client):
    """No question mixes Hebrew glyphs with transliterated names in options."""
    for node in ("bet", "qal_perfect"):
        resp = client.get(f"/api/v1/hebrew/lesson/{node}/quiz?count=8")
        assert resp.status_code == 200
        for q in resp.json()["data"]["questions"]:
            opts = q.get("options") or []
            if len(opts) > 1:
                assert len({_script(o) for o in opts}) == 1, f"mixed scripts in {q}"


def test_next_lesson_card_plus_two(client):
    """Next lesson: one card + exactly 2 questions with different answers."""
    resp = client.get("/api/v1/hebrew/next-lesson")
    assert resp.status_code == 200
    data = resp.json()["data"]
    card = data["card"]
    assert card and card["node_id"] and card["title"]
    qs = data["questions"]
    assert len(qs) == 2
    for q in qs:
        for field in ("node_id", "question_id", "type", "question", "options", "answer_mode"):
            assert field in q
    # Same node (one card's worth), single-script options each
    assert qs[0]["node_id"] == qs[1]["node_id"] == card["node_id"]
    for q in qs:
        assert len({_script(o) for o in q["options"]}) == 1


def test_review_quiz_mode_ok(client):
    """FSRS review mode returns questions in quiz shape."""
    resp = client.get("/api/v1/hebrew/quiz?mode=review&count=4")
    assert resp.status_code == 200
    for q in resp.json()["data"]["questions"]:
        assert "question" in q and "node_id" in q


def test_top_words_and_roots(client):
    resp = client.get("/api/v1/hebrew/top-words?limit=5")
    assert resp.status_code == 200
    words = resp.json()["data"]["words"]
    assert len(words) == 5 and words[0]["rank"] == 1
    assert words[0]["bare"] and words[0]["gloss"]
    resp = client.get("/api/v1/hebrew/top-roots?limit=5")
    assert resp.status_code == 200
    roots = resp.json()["data"]["roots"]
    assert len(roots) == 5 and roots[0]["rank"] == 1
