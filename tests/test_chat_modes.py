from web.routes.chat import (
    GENERAL_CHAT_BLOCKED_TOOLS,
    HEBREW_TOOL_ALLOWLIST,
    TOOL_DEFINITIONS,
    _filter_tools,
    _hebrew_learner_snapshot,
    _prepare_chat_messages,
    _run_tool_thread,
    _sanitize_chat_content,
)
import web.routes.chat as chat_routes

import lib.api.progress


def _names(mode):
    return {
        tool["function"]["name"]
        for tool in _filter_tools(TOOL_DEFINITIONS, [], [], mode)
    }


def test_general_chat_excludes_all_learning_tools():
    names = _names("chat")
    assert not names.intersection(GENERAL_CHAT_BLOCKED_TOOLS)
    assert "scripture_verse" in names


def test_hebrew_mode_is_allowlisted_to_language_tools():
    names = _names("hebrew")
    assert names
    assert names <= HEBREW_TOOL_ALLOWLIST
    assert "scripture_hebrew_progress" in names
    assert "scripture_assess_start" not in names


def test_forbidden_tool_is_rejected_before_execution():
    result = _run_tool_thread("scripture_hebrew_progress", {}, [], "user-1", "chat")
    assert result == {"error": "Tool disabled in chat mode"}


def test_general_chat_quiz_markers_are_neutralized():
    content = "Text first. %%%HEBREW_QUIZ:{\"question\":\"Q\"}%%%"
    sanitized = _sanitize_chat_content(content, "chat")
    assert "%%%HEBREW_QUIZ" not in sanitized
    assert "Hebrew/Learn" in sanitized
    assert _sanitize_chat_content(content, "hebrew") == content


def test_user_scoped_tool_cannot_override_server_bound_identity(monkeypatch):
    seen = {}

    def fake_call_tool(name, _conn, **kwargs):
        seen["name"] = name
        seen.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(chat_routes, "call_tool", fake_call_tool)
    result = _run_tool_thread(
        "scripture_hebrew_progress",
        {"user_id": "victim"},
        [],
        "attacker",
        "hebrew",
    )
    assert result == {"ok": True}
    assert seen["user_id"] == "attacker"


# ── Hebrew Tutor learner-state hydration (Track C1) ───────────────────

def _fake_progress_payload():
    return {
        "ok": True,
        "has_progress": True,
        "by_category": [
            {"category": "consonant", "total": 22, "mastered": 18, "avg_mastery": 0.9},
            {"category": "grammar", "total": 30, "mastered": 6, "avg_mastery": 0.4},
        ],
        "practiced_nodes": [
            {"node_id": "aleph", "title": "Aleph"},
            {"node_id": "bet", "title": "Bet"},
        ],
        "due_reviews": {
            "count": 7,
            "next_items": [{"node_id": "gimel", "title": "Gimel"}],
        },
        "gamification": {"xp": 1240, "streak_count": 5},
        "placement": {
            "taken_at": "2026-08-20 10:00:00",
            "applied": True,
            "level_estimates": {"alphabet": 3, "vocab": 1},
        },
    }


class _Body:
    """Minimal ChatRequest stand-in for _prepare_chat_messages."""

    def __init__(self, mode="chat", tool_user_id="learner-1"):
        self.messages = [{"role": "user", "content": "hello"}]
        self.mode = mode
        self.max_tokens = 4096
        self.tool_user_id = tool_user_id


def test_hebrew_mode_hydrates_learner_snapshot(monkeypatch):
    monkeypatch.setattr(lib.api.progress, "hebrew_progress",
                        lambda conn, user_id="default", limit=10: _fake_progress_payload())
    msgs = _prepare_chat_messages(_Body(mode="hebrew"))
    system_msgs = [m for m in msgs if m["role"] == "system"]
    assert len(system_msgs) == 2
    snapshot = system_msgs[1]["content"]
    assert "LEARNER PROGRESS SNAPSHOT" in snapshot
    assert "Due reviews: 7 item(s)" in snapshot


def test_general_chat_never_receives_learner_snapshot(monkeypatch):
    monkeypatch.setattr(lib.api.progress, "hebrew_progress",
                        lambda conn, user_id="default", limit=10: _fake_progress_payload())
    msgs = _prepare_chat_messages(_Body(mode="chat"))
    assert all("LEARNER PROGRESS SNAPSHOT" not in m["content"]
               for m in msgs if m["role"] == "system")


def test_new_learner_gets_no_snapshot(monkeypatch):
    monkeypatch.setattr(lib.api.progress, "hebrew_progress",
                        lambda conn, user_id="default", limit=10:
                        {"ok": True, "has_progress": False})
    msgs = _prepare_chat_messages(_Body(mode="hebrew"))
    assert len([m for m in msgs if m["role"] == "system"]) == 1


def test_snapshot_uses_server_bound_identity_only(monkeypatch):
    seen = {}

    def spy(conn, user_id="default", limit=10):
        seen["user_id"] = user_id
        return _fake_progress_payload()

    monkeypatch.setattr(lib.api.progress, "hebrew_progress", spy)
    body = _Body(mode="hebrew")
    body.user_id = "client-claimed-id"  # client field must be ignored
    _prepare_chat_messages(body)
    assert seen["user_id"] == "learner-1"


def test_snapshot_is_bounded_and_deterministic(monkeypatch):
    payload = _fake_progress_payload()
    payload["by_category"] = [
        {"category": f"cat{i}", "total": 10, "mastered": 1, "avg_mastery": 0.1}
        for i in range(50)
    ]
    payload["due_reviews"]["next_items"] = [
        {"node_id": f"n{i}", "title": f"Item {i}"} for i in range(100)
    ]
    monkeypatch.setattr(lib.api.progress, "hebrew_progress",
                        lambda conn, user_id="default", limit=10: payload)
    s1 = _hebrew_learner_snapshot("learner-1")
    s2 = _hebrew_learner_snapshot("learner-1")
    assert s1 == s2  # deterministic
    assert len(s1.splitlines()) <= 15  # bounded context
    # Only the first few categories/items survive the cap
    assert "cat5" in s1 and "cat6" not in s1
    assert "Item 0" in s1 and "Item 3" not in s1


# ── Track G3: capacity safety ────────────────────────────────────────────────

def test_public_provider_summary_carries_availability_only():
    summary = chat_routes._llm_provider.public_summary()
    assert set(summary.keys()) == {"available"}
    assert isinstance(summary["available"], bool)


def test_instructions_endpoint_does_not_leak_pool_details():
    data = chat_routes.chat_instructions("chat")["data"]
    assert set(data["provider"].keys()) == {"available"}


def test_contributor_disclosure_tracks_default_model(monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "deepseek-chat")
    assert chat_routes._contributor_disclosure() is None
    monkeypatch.setenv("CHAT_MODEL", "opencode-go/muse-spark-1.2-contributor")
    assert "training" in chat_routes._contributor_disclosure()


def test_emergency_disable_switch_scopes_by_mode(monkeypatch):
    monkeypatch.delenv("CHAT_DISABLED", raising=False)
    monkeypatch.delenv("HEBREW_CHAT_DISABLED", raising=False)
    assert chat_routes._chat_disabled("chat") is None
    assert chat_routes._chat_disabled("hebrew") is None
    monkeypatch.setenv("HEBREW_CHAT_DISABLED", "1")
    assert chat_routes._chat_disabled("hebrew") is not None
    assert chat_routes._chat_disabled("chat") is None
    monkeypatch.setenv("CHAT_DISABLED", "true")
    assert chat_routes._chat_disabled("chat") is not None
    assert chat_routes._chat_disabled("hebrew") is not None


def test_mode_rate_limits_are_env_configurable(monkeypatch):
    monkeypatch.setenv("CHAT_RATE_LIMIT", "7")
    monkeypatch.setenv("HEBREW_RATE_LIMIT", "3")
    assert chat_routes._mode_rate_limit("chat") == 7
    assert chat_routes._mode_rate_limit("hebrew") == 3


def test_rate_limiter_honors_per_mode_limit(monkeypatch):
    ip = "10.9.9.9"
    chat_routes._rate_limits.pop(ip, None)
    monkeypatch.setenv("HEBREW_RATE_LIMIT", "2")
    limit = chat_routes._mode_rate_limit("hebrew")
    assert chat_routes._check_rate_limit(ip, limit) is True
    assert chat_routes._check_rate_limit(ip, limit) is True
    assert chat_routes._check_rate_limit(ip, limit) is False
    chat_routes._rate_limits.pop(ip, None)
