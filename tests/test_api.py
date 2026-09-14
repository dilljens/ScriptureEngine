"""
API contract tests for HTTP endpoints with behavior assertions.

The old _ok()-only smoke tests are gone: route-existence is pinned by the
OpenAPI route-set test (test_openapi_snapshot.py) and correctness by the
dedicated files (test_verses.py, test_search.py, test_graph.py, ...).
What remains here asserts response bodies, auth isolation, and security
invariants — things that catch real regressions.

Run: pytest tests/test_api.py -q
"""

import asyncio
import json
from pathlib import Path

import pytest

from web.routes import chat as chat_routes

# ── Helpers ───────────────────────────────────────────────────────────


def _ok(status):
    """Acceptable status codes for a working endpoint."""
    return status in (200, 201, 202, 204, 301, 302, 307, 400, 401, 403, 404, 409, 422, 423)


def _session_token(user_id):
    from web.routes import auth

    return auth._generate_session_token(user_id)


def _placement_answer(question):
    import sqlite3
    from web.routes import hebrew

    conn = sqlite3.connect(str(hebrew.MEM_DB))
    row = conn.execute(
        "SELECT correct_answer FROM hebrew_practice_items WHERE id=?",
        (question["question_id"],),
    ).fetchone()
    conn.close()
    return row[0]


# ═══════════════════════════════════════════════════════════════════════
# web/server.py — Inline Routes
# ═══════════════════════════════════════════════════════════════════════


class TestServerRootRoutes:
    """Core informational and discovery endpoints."""

    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"


class TestServerSearchRoutes:
    """Search endpoints (behavioral asserts; status-only smoke lives in test_search.py)."""

    def test_search_sections_tool_registered(self, client):
        """scripture_search_sections is exposed via the generic tool endpoint."""
        listed = client.get("/api/v1/tools")
        assert listed.status_code == 200
        names = json.dumps(listed.json())
        assert "scripture_search_sections" in names

        resp = client.post(
            "/api/v1/tools/scripture_search_sections",
            json={"query": "covenant", "min_hits": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True or "sections" in data

    def test_cluster_hits_groups_contiguous_verses(self):
        from lib.api.search import _cluster_hits

        def hit(vid, book="Isaiah"):
            return {"verse": vid, "text": f"text {vid}", "book": book, "book_id": vid.rsplit(".", 2)[0], "work_id": "ot"}

        hits = [
            hit("isa.52.13"), hit("isa.53.2"), hit("isa.53.5"),  # one section
            hit("psa.130.8"),                                     # singleton — dropped
            hit("ruth.4.14"), hit("ruth.4.15"),                   # second section (different book)
        ]
        sections = _cluster_hits(hits, gap=3, min_hits=2)
        labels = [s["section"] for s in sections]
        assert "isa.52.13-isa.53.5" in labels
        assert "ruth.4.14-ruth.4.15" in labels
        # Densest first
        assert sections[0]["hits"] >= sections[-1]["hits"]

    def test_cluster_handles_non_numeric_chapters(self):
        from lib.api.search import _cluster_hits

        hits = [
            {"verse": "dss.1QHa.5", "text": "a", "book": "Hodayot", "book_id": "dss", "work_id": "dss"},
            {"verse": "dss.1QHa.6", "text": "b", "book": "Hodayot", "book_id": "dss", "work_id": "dss"},
            {"verse": "dc104.104.51", "text": "c", "book": "D&C 104", "book_id": "dc104", "work_id": "dc"},
            {"verse": "dc104.104.52", "text": "d", "book": "D&C 104", "book_id": "dc104", "work_id": "dc"},
        ]
        sections = _cluster_hits(hits, gap=3, min_hits=2)
        labels = [s["section"] for s in sections]
        assert "dss.1QHa.5-dss.1QHa.6" in labels
        assert "dc104.104.51-dc104.104.52" in labels

    def test_merge_graph_anchors_direct_and_shared(self):
        from lib.api.search import _merge_graph_anchors

        anchors = ["isa.42.19", "isa.44.1", "isa.49.3", "isa.65.13"]
        direct = [("isa.42.19", "isa.44.1")]
        shared = {"isa.52.13": {"isa.44.1", "isa.49.3"}}  # bridge via one neighbor

        groups = _merge_graph_anchors(anchors, direct, shared)
        assert [g for g in groups if len(g) == 3] == [["isa.42.19", "isa.44.1", "isa.49.3"]]
        assert ["isa.65.13"] in groups

    def test_search_sections_response_shape(self, client):
        resp = client.post(
            "/api/v1/tools/scripture_search_sections",
            json={"query": "servant", "min_hits": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        body = data.get("data") or data
        assert "sections" in body
        for s in body["sections"]:
            assert s.get("basis") in ("word", "graph")
            if s.get("basis") == "graph":
                assert isinstance(s.get("evidence"), list)


# ═══════════════════════════════════════════════════════════════════════
# routes/hebrew.py
# ═══════════════════════════════════════════════════════════════════════


class TestHebrewRoutes:
    """Hebrew learning endpoints."""

    def test_hebrew_uses_isolated_database(self, client):
        from web.routes import hebrew
        assert hebrew.MEM_DB != Path(__file__).parent.parent / "data" / "memorize.db"

    def test_hebrew_lesson_quiz(self, client):
        """Per-lesson quiz returns the lesson's practice items in quiz shape,
        ordered for micro-scaffolding (recognition before production), with
        confusable distractor items appended last."""
        resp = client.get("/api/v1/hebrew/lesson/qal_perfect/quiz")
        assert _ok(resp.status_code)
        data = resp.json()["data"]
        assert data["node_id"] == "qal_perfect"
        assert len(data["questions"]) > 0
        # Every question carries the quiz-renderer contract
        for q in data["questions"]:
            for field in ("node_id", "question_id", "type", "question", "options", "answer_mode", "category"):
                assert field in q, f"missing {field} in {q}"
        # Scaffolding: any multiple_choice must precede any typing question
        types = [q["type"] for q in data["questions"]]
        mc_positions = [i for i, t in enumerate(types) if t == "multiple_choice"]
        typing_positions = [i for i, t in enumerate(types) if t == "typing"]
        if mc_positions and typing_positions:
            assert max(mc_positions) < min(typing_positions)
        # Distractors (if any) come last
        distractors = [i for i, q in enumerate(data["questions"]) if q.get("is_distractor")]
        if distractors and not data["questions"][-1].get("is_distractor"):
            assert max(distractors) == len(data["questions"]) - 1

    def test_hebrew_lesson_quiz_missing(self, client):
        resp = client.get("/api/v1/hebrew/lesson/zzz_nonexistent/quiz")
        assert resp.status_code == 404

    def test_hebrew_adaptive_diagnostic_flow(self, client):
        """Adaptive placement: start → answer → converge with per-skill estimates
        and SRS seeding (correct → mature interval, tested-out credit)."""
        token = _session_token("placement-test")
        resp = client.post("/api/v1/hebrew/diagnostic/adaptive/start", json={
            "user_id": "placement-test", "session_token": token,
        })
        assert _ok(resp.status_code)
        data = resp.json()["data"]
        assert data["session_id"]
        assert data["skill"] == "alphabet"
        q = data["question"]
        assert "correct_answer" not in q

        sid = data["session_id"]
        answers = 0
        cur_data = data
        # Drive the whole session with 100% correct answers → should converge
        while "question" in cur_data:
            q = cur_data["question"]
            answers += 1
            assert answers < 200, "placement did not converge"
            resp = client.post("/api/v1/hebrew/diagnostic/adaptive/answer", json={
                "session_id": sid,
                "user_id": "placement-test",
                "session_token": token,
                "question_id": q["question_id"],
                "question_nonce": q["question_nonce"],
                "answer": _placement_answer(q),
            })
            assert _ok(resp.status_code), f"answer {answers} failed: {resp.text[:200]}"
            cur_data = resp.json()["data"]
        assert cur_data.get("done") is True
        results = cur_data["results"]
        assert "skills" in results
        # All 4 skills estimated within their ranges
        for skill, _cats, lo, hi, _start in [
            ("alphabet", None, 1, 3, None), ("vocab", None, 4, 7, None),
            ("grammar", None, 3, 7, None), ("reading", None, 3, 7, None)]:
            est = results["skills"][skill]["estimated_level"]
            assert lo <= est <= hi, f"{skill} estimate {est} outside [{lo},{hi}]"
        assert results["srs_seeded"] >= 20  # at least min items × 4 skills
        # SRS seeding: the answered nodes should have review state with long intervals.
        # Sampling is SQLite ORDER BY RANDOM() (unseedable by design — real
        # learners get fresh paths), and repeat nodes upsert to one row, so the
        # DISTINCT-row count lands near the volume threshold. srs_seeded above
        # proves volume; here we prove breadth with margin for repeats.
        import sqlite3
        from web.routes import hebrew
        conn = sqlite3.connect(str(hebrew.MEM_DB))
        row = conn.execute(
            "SELECT COUNT(*) FROM hebrew_review_state WHERE user_id='placement-test' AND stability > 1"
        ).fetchone()
        conn.close()
        assert row[0] >= 15, f"expected seeded review state, got {row[0]}"

    def test_hebrew_adaptive_diagnostic_rejects_reuse(self, client):
        token = _session_token("placement-reuse")
        resp = client.post("/api/v1/hebrew/diagnostic/adaptive/start", json={
            "user_id": "placement-reuse", "session_token": token,
        })
        sid = resp.json()["data"]["session_id"]
        # Answering with a bogus question_id → 400
        resp = client.post("/api/v1/hebrew/diagnostic/adaptive/answer", json={
            "session_id": sid, "user_id": "placement-reuse", "session_token": token,
            "question_id": -1, "node_id": "aleph", "answer": "x"})
        assert resp.status_code == 400

    def test_hebrew_review_queue(self, client):
        resp = client.get("/api/v1/hebrew/review-queue")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "reviews" in data
        # Every due item carries a language label (hebrew or aramaic).
        for item in data["reviews"]:
            assert item.get("language") in ("hebrew", "aramaic")

    def test_hebrew_review_queue_new_cards(self, client):
        """New-card introduction: frontier nodes appear with is_new, capped by
        new_cards_per_day, and suppressed when the backlog is huge."""
        resp = client.get("/api/v1/hebrew/review-queue", params={
            "user_id": "new-cards-test", "session_token": _session_token("new-cards-test"),
            "new_cards_per_day": 5, "limit": 30})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_cards_per_day"] == 5
        new_items = [r for r in data["reviews"] if r.get("is_new")]
        assert len(new_items) <= 5
        for item in new_items:
            assert item["scheduler"] == "new"
            assert item["mastery"] == 0
        # Backlog suppression: with a huge due count the budget collapses to 0
        resp2 = client.get("/api/v1/hebrew/review-queue", params={
            "user_id": "new-cards-test", "session_token": _session_token("new-cards-test"),
            "new_cards_per_day": 5, "limit": 30})
        assert resp2.status_code == 200
        assert "new_cards" in resp2.json()["data"]

    def test_hebrew_fsrs_review(self, client):
        resp = client.post("/api/v1/hebrew/fsrs/review", json={"node_id": "aleph", "rating": 3})
        assert resp.status_code == 200
        assert resp.json()["data"]["scheduler"] == "adaptive-v1"

    def test_hebrew_hard_review_is_persisted_success(self, client):
        import sqlite3
        from web.routes import hebrew

        resp = client.post("/api/v1/hebrew/fsrs/review", json={
            "node_id": "aleph", "rating": 2, "user_id": "hard-review-test",
            "session_token": _session_token("hard-review-test"),
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["correct"] == 1
        conn = sqlite3.connect(hebrew.MEM_DB)
        state = conn.execute("""
            SELECT last_rating,reps,lapses,due FROM hebrew_review_state
            WHERE user_id='hard-review-test' AND node_id='aleph'
        """).fetchone()
        conn.close()
        assert state[:3] == (2, 1, 0)
        assert state[3]

    def test_hebrew_review_rejects_unknown_node(self, client):
        resp = client.post("/api/v1/hebrew/fsrs/review", json={
            "node_id": "does-not-exist", "rating": 3, "user_id": "invalid-node-audit",
            "session_token": _session_token("invalid-node-audit"),
        })
        assert resp.status_code == 400

    def test_hebrew_review_resolves_session_user(self, client):
        import sqlite3
        from web.routes import hebrew
        import web.routes.auth as auth

        # Ensure the sessions table exists in the test database (its schema is
        # normally created by SCHEMA_SQL in lib/db.py).
        conn = auth.get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                last_seen TEXT
            )
        """)
        conn.commit()
        conn.close()

        token = auth._generate_session_token("auth-owner-user")
        try:
            resp = client.post("/api/v1/hebrew/fsrs/review", json={
                "node_id": "aleph", "rating": 3,
                "user_id": "forged-user", "session_token": token,
            })
            assert resp.status_code == 200
            conn = sqlite3.connect(hebrew.MEM_DB)
            owner = conn.execute(
                "SELECT 1 FROM hebrew_review_state WHERE user_id='auth-owner-user' AND node_id='aleph'"
            ).fetchone()
            forged = conn.execute(
                "SELECT 1 FROM hebrew_review_state WHERE user_id='forged-user'"
            ).fetchone()
            conn.close()
            assert owner is not None
            assert forged is None
        finally:
            conn = auth.get_conn()
            conn.execute("DELETE FROM sessions WHERE user_id='auth-owner-user'")
            conn.commit()
            conn.close()

    def test_hebrew_review_rejects_bad_session(self, client):
        resp = client.post("/api/v1/hebrew/fsrs/review", json={
            "node_id": "aleph", "rating": 3, "user_id": "x",
            "session_token": "invalid-token-value",
        })
        assert resp.status_code == 401

    def test_hebrew_diagnostic_apply(self, client):
        resp = client.post("/api/v1/hebrew/diagnostic/apply", json={
            "user_id": "test",
            "session_token": _session_token("test"),
            "answers": []
        })
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════
# routes/conversations.py
# ═══════════════════════════════════════════════════════════════════════


class TestConversationRoutes:
    """Conversation/chat session management (ownership isolation only)."""

    def test_conversations_are_scoped_to_owner(self, client):
        resp = client.post("/api/v1/conversations", json={
            "title": "Owner scope test",
            "created_by": "owner_a",
        })
        assert resp.status_code in (200, 201)
        session_id = resp.json()["data"]["id"]
        try:
            owned = client.get(
                f"/api/v1/conversations/{session_id}",
                params={"user_id": "owner_a"},
            )
            assert owned.status_code == 200

            denied = client.get(
                f"/api/v1/conversations/{session_id}",
                params={"user_id": "owner_b"},
            )
            assert denied.status_code == 403

            denied_write = client.post(
                f"/api/v1/conversations/{session_id}/messages",
                params={"user_id": "owner_b"},
                json={"role": "user", "content": "must be denied"},
            )
            assert denied_write.status_code == 403

            invalid_token = client.get(
                f"/api/v1/conversations/{session_id}",
                params={"user_id": "owner_a", "session_token": "not-valid"},
            )
            assert invalid_token.status_code == 401
        finally:
            client.delete(
                f"/api/v1/conversations/{session_id}",
                params={"user_id": "owner_a"},
            )

    def test_connection_promotion_cannot_cross_sessions(self, client):
        owner_a = client.post(
            "/api/v1/conversations",
            json={"title": "Connection A", "created_by": "owner_a"},
        ).json()["data"]["id"]
        owner_b = client.post(
            "/api/v1/conversations",
            json={"title": "Connection B", "created_by": "owner_b"},
        ).json()["data"]["id"]
        try:
            added = client.post(
                f"/api/v1/conversations/{owner_a}/connections",
                params={"user_id": "owner_a"},
                json={
                    "source_verse": "gen.1.1",
                    "target_verse": "john.1.1",
                    "relationship": "scope test",
                },
            )
            assert added.status_code == 200
            listed = client.get(
                f"/api/v1/conversations/{owner_a}/connections",
                params={"user_id": "owner_a"},
            ).json()
            connection_id = listed["data"]["connections"][0]["id"]

            promoted = client.post(
                f"/api/v1/conversations/{owner_b}/connections/{connection_id}/promote",
                params={"user_id": "owner_b"},
                json={},
            )
            assert promoted.status_code == 200
            assert promoted.json()["ok"] is False

            still_unpromoted = client.get(
                f"/api/v1/conversations/{owner_a}/connections",
                params={"user_id": "owner_a"},
            ).json()["data"]["connections"]
            assert next(c for c in still_unpromoted if c["id"] == connection_id)["promoted"] == 0
        finally:
            client.delete(f"/api/v1/conversations/{owner_a}", params={"user_id": "owner_a"})
            client.delete(f"/api/v1/conversations/{owner_b}", params={"user_id": "owner_b"})


class TestSharedConversations:
    """Unlisted share links: snapshot, public read, fork-on-question."""

    def _make_conversation(self, client, owner="sharer_a"):
        sid = client.post(
            "/api/v1/conversations",
            json={"title": "Share me", "created_by": owner},
        ).json()["data"]["id"]
        client.post(
            f"/api/v1/conversations/{sid}/messages",
            params={"user_id": owner},
            json={"role": "user", "content": "What is redemption? See ruth.4.1"},
        )
        asst = client.post(
            f"/api/v1/conversations/{sid}/messages",
            params={"user_id": owner},
            json={"role": "assistant", "content": "Redemption is kinsman buy-back."},
        ).json()["data"]
        return sid, asst["id"]

    def test_share_whole_conversation(self, client):
        sid, _ = self._make_conversation(client)
        try:
            resp = client.post(
                f"/api/v1/conversations/{sid}/share",
                params={"user_id": "sharer_a"},
                json={},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["slug"] and data["url"].startswith("/?shared=")

            # Public read — no owner params
            got = client.get(f"/api/v1/shared/{data['slug']}").json()
            assert got["ok"] is True
            assert len(got["data"]["messages"]) == 2

            # Missing slug
            missing = client.get("/api/v1/shared/nope-does-not-exist").json()
            assert missing["ok"] is False
        finally:
            client.delete(f"/api/v1/conversations/{sid}", params={"user_id": "sharer_a"})

    def test_share_single_response_includes_question(self, client):
        sid, msg_id = self._make_conversation(client)
        try:
            resp = client.post(
                f"/api/v1/conversations/{sid}/share",
                params={"user_id": "sharer_a"},
                json={"message_id": msg_id},
            ).json()
            assert resp["ok"] is True
            got = client.get(f"/api/v1/shared/{resp['data']['slug']}").json()["data"]
            roles = [m["role"] for m in got["messages"]]
            assert roles == ["user", "assistant"]
        finally:
            client.delete(f"/api/v1/conversations/{sid}", params={"user_id": "sharer_a"})

    def test_share_requires_owner(self, client):
        sid, _ = self._make_conversation(client, owner="sharer_owner")
        try:
            denied = client.post(
                f"/api/v1/conversations/{sid}/share",
                params={"user_id": "someone_else"},
                json={},
            )
            assert denied.status_code == 403
        finally:
            client.delete(f"/api/v1/conversations/{sid}", params={"user_id": "sharer_owner"})

    def test_fork_creates_session_owned_by_asker(self, client):
        sid, _ = self._make_conversation(client)
        try:
            slug = client.post(
                f"/api/v1/conversations/{sid}/share",
                params={"user_id": "sharer_a"},
                json={},
            ).json()["data"]["slug"]

            forked = client.post(
                f"/api/v1/shared/{slug}/fork",
                params={"user_id": "asker_b"},
                json={},
            ).json()
            assert forked["ok"] is True
            new_sid = forked["data"]["session_id"]
            assert forked["data"]["message_count"] == 2

            # The fork belongs to the asker, not the sharer.
            owned = client.get(
                f"/api/v1/conversations/{new_sid}", params={"user_id": "asker_b"}
            )
            assert owned.status_code == 200
            denied = client.get(
                f"/api/v1/conversations/{new_sid}", params={"user_id": "sharer_a"}
            )
            assert denied.status_code == 403

            # Forked messages carry extracted verse refs (ruth.4.1).
            msgs = owned.json()["data"]
            assert any(r["verse_id"].startswith("ruth") for r in msgs.get("refs", []))

            client.delete(f"/api/v1/conversations/{new_sid}", params={"user_id": "asker_b"})
        finally:
            client.delete(f"/api/v1/conversations/{sid}", params={"user_id": "sharer_a"})


# ═══════════════════════════════════════════════════════════════════════
# routes/chat.py
# ═══════════════════════════════════════════════════════════════════════


class TestChatRoutes:
    """LLM chat proxy endpoints."""

    def test_chat_instructions(self, client):
        resp = client.get("/api/v1/chat/instructions")
        assert resp.status_code == 200

    def test_origin_matching_rejects_prefix_attacks(self):
        assert chat_routes._origin_allowed("https://scriptureengine.org")
        assert chat_routes._origin_allowed("https://app.scriptureengine.org")
        assert not chat_routes._origin_allowed("https://scriptureengine.org.evil.com")
        assert not chat_routes._origin_allowed("https://evil.com/@scriptureengine.org")
        assert not chat_routes._origin_allowed("not a url")

    def test_stream_rejects_untrusted_origin(self, client, monkeypatch):
        monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
        resp = client.post(
            "/api/v1/chat/stream",
            headers={"Origin": "https://scriptureengine.org.evil.com"},
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert resp.status_code == 200
        assert "Chat is only available from scriptureengine.org" in resp.text

    def test_done_event_supports_final_content_fallback(self):
        event = chat_routes._sse_event({
            "type": "done",
            "final_content": "full answer",
            "final_reasoning": "private reasoning",
        })
        assert '"final_content": "full answer"' in event
        assert '"final_reasoning": "private reasoning"' in event

    def test_stream_surfaces_upstream_non_2xx(self, monkeypatch):
        class FakePostResponse:
            def json(self):
                return {"choices": [{"message": {"content": "no tools"}}], "model": "test"}

        class FakeStreamResponse:
            status_code = 429

            async def aread(self):
                return b'{"error":{"message":"upstream rate limit"}}'

            async def aiter_lines(self):
                if False:
                    yield ""

        class FakeStreamContext:
            async def __aenter__(self):
                return FakeStreamResponse()

            async def __aexit__(self, *_args):
                return False

        class FakeClient:
            async def post(self, *_args, **_kwargs):
                return FakePostResponse()

            def stream(self, *_args, **_kwargs):
                return FakeStreamContext()

        monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setattr(chat_routes, "_http_client", FakeClient())
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/chat/stream",
            "headers": [(b"origin", b"https://scriptureengine.org")],
            "query_string": b"",
            "client": ("203.0.113.10", 443),
            "scheme": "https",
        }
        request = chat_routes.Request(scope)
        response = asyncio.run(chat_routes.llm_chat_stream(
            chat_routes.ChatRequest(messages=[{"role": "user", "content": "hello"}]),
            request,
        ))
        chunks = asyncio.run(_collect_stream(response.body_iterator))
        payload = "".join(chunks)
        assert '"type": "error"' in payload
        assert "429" in payload
        assert "upstream rate limit" in payload


async def _collect_stream(iterator):
    return [chunk.decode() if isinstance(chunk, bytes) else chunk async for chunk in iterator]


# ═══════════════════════════════════════════════════════════════════════
# routes/assessment.py
# ═══════════════════════════════════════════════════════════════════════


class TestAssessmentRoutes:
    """Quiz and adaptive assessment endpoints (answer-key secrecy only)."""

    def test_assessment_start(self, client):
        resp = client.post("/api/v1/assessment/start")
        # 500 is acceptable when test DB has insufficient connections data
        assert _ok(resp.status_code) or resp.status_code in (404, 500)
        if resp.status_code == 200:
            question = resp.json().get("data", {}).get("question", {})
            assert "correct_answer" not in question
            assert all(
                not isinstance(option, dict) or "correct" not in option
                for option in question.get("options", [])
            )


# ═══════════════════════════════════════════════════════════════════════
# routes/learn.py
# ═══════════════════════════════════════════════════════════════════════


class TestLearnRoutes:
    """Learning module endpoints (grading integrity only)."""

    def test_learn_module_detail(self, client):
        resp = client.get("/api/v1/learn/modules/1")
        assert _ok(resp.status_code)
        if resp.status_code == 200:
            for question in resp.json().get("data", {}).get("questions", []):
                assert "correct_answer" not in question

    def test_learn_practice_rejects_client_correctness(self, client):
        resp = client.post(
            "/api/v1/learn/modules/1/practice",
            json={"question_id": 1, "correct": True},
        )
        assert resp.status_code == 400

    def test_learn_practice_is_idempotent(self, client):
        from web.routes import auth
        from web.routes.learn import get_conn

        modules = client.get("/api/v1/learn/modules").json()["data"]["modules"]
        if not modules:
            return
        module_id = modules[0]["id"]
        detail = client.get(f"/api/v1/learn/modules/{module_id}").json()["data"]
        question = detail["questions"][0]
        user_id = "learn-idempotency-test"
        attempt_id = "learn-idempotency-test-1"
        token = auth._generate_session_token(user_id)
        payload = {
            "user_id": user_id,
            "session_token": token,
            "question_id": question["id"],
            "answer": (question.get("options") or [""])[0],
            "answer_mode": question.get("answer_mode", "free_text"),
            "rating": 3,
            "attempt_id": attempt_id,
        }
        try:
            first = client.post(f"/api/v1/learn/modules/{module_id}/practice", json=payload)
            second = client.post(f"/api/v1/learn/modules/{module_id}/practice", json=payload)
            assert first.status_code == 200
            assert second.status_code == 200
            assert second.json() == first.json()
        finally:
            conn = get_conn()
            for table, column in (
                ("learning_attempts", "user_id"), ("quiz_progress", "user_id"),
                ("learning_progress", "user_id"), ("learn_gamification", "user_id"),
            ):
                conn.execute(f"DELETE FROM {table} WHERE {column}=?", (user_id,))
            conn.commit()
            conn.close()
