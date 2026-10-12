"""Chat lookup fast path: simple locate/quote questions stay cheap.

Covers the two halves of the fast path (prompt rule in CHAT_AGENTS.md is
not machine-testable; everything enforceable lives here):
  - web.lib.subagents.is_simple_lookup — narrow, high-precision phrasing
  - web.routes.chat wiring — 2 tool rounds, no planner fan-out,
    lookup-only tool menu, Hebrew Tutor excluded

Run: pytest tests/test_chat_lookup_fastpath.py -q
"""

from types import SimpleNamespace

from web.lib import subagents as _subagents
from web.routes import chat as chat_routes

LOOKUP_MSGS = lambda text: [{"role": "user", "content": text}]


def test_simple_lookup_matches_locate_quote_identify():
    positives = [
        "where is the scripture where nephi says he will go and do",
        "where's the verse about the word was god",
        "where is the passage where jesus wept",
        "what verse says god is love",
        "which verse talks about the good shepherd",
        "which scripture describes the plan of salvation",
        "quote john 1:1",
        "cite 1 nephi 3:7",
        "find me the verse where alma talks about faith",
        "find me the passage about charity",
        "what does 1 nephi 3:7 say",
        "show me the scripture on baptism",
        "give me the verse about prayer",
    ]
    for text in positives:
        assert _subagents.is_simple_lookup(LOOKUP_MSGS(text)), text


def test_simple_lookup_rejects_research_shaped():
    negatives = [
        "compare genesis 1 and john 1",
        "trace the temple theme through the scriptures",
        "explain why nephi went back to jerusalem",
        "analyze the chiasmus in alma 36",
        "describe in detail the atonement",
        "how do the covenants relate to each other",
        "why does isaiah use vineyard imagery",
        "what is the difference between pshat and sod",
        "tell me about nephi",
        "hi",
        "",
        # Deep intent wins over lookup phrasing.
        "where is 1 nephi 3:7 and explain its meaning in depth",
        # Multi-part and long questions stay on the full pipeline.
        "where is the verse about faith? and what about hope?",
        "where is the verse about faith " + "x" * 200,
    ]
    for text in negatives:
        assert not _subagents.is_simple_lookup(LOOKUP_MSGS(text)), text


def test_gate_excludes_hebrew_and_toolless():
    msgs = LOOKUP_MSGS("quote john 1:1")
    assert chat_routes._is_simple_lookup(
        SimpleNamespace(mode="chat", tools_enabled=True), msgs
    )
    assert chat_routes._is_simple_lookup(
        SimpleNamespace(mode="knowledge", tools_enabled=True), msgs
    )
    assert not chat_routes._is_simple_lookup(
        SimpleNamespace(mode="hebrew", tools_enabled=True), msgs
    )
    assert not chat_routes._is_simple_lookup(
        SimpleNamespace(mode="chat", tools_enabled=False), msgs
    )


def test_lookup_only_menu_has_just_four_tools():
    body = SimpleNamespace(
        model=chat_routes._llm_provider.default_model,
        max_tokens=100,
        temperature=0.0,
        tools_enabled=True,
        scopes=[],
        disabled_tools=[],
        mode="chat",
        session_id="",
    )
    payload = chat_routes._build_payload(
        body, LOOKUP_MSGS("quote john 1:1"), lookup_only=True
    )
    names = {t["function"]["name"] for t in payload["tools"]}
    assert names == set(chat_routes.LOOKUP_TOOLS)
    full = chat_routes._build_payload(body, LOOKUP_MSGS("quote john 1:1"))
    assert len(full["tools"]) > len(payload["tools"])


def _tool_call_response():
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "scripture_search", "arguments": "{}"},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }


def _auth_headers():
    return {"Origin": "https://scriptureengine.org"}


def test_non_stream_caps_tool_rounds_for_lookup(client, monkeypatch):
    """A model that never stops calling tools is cut off after 2 rounds."""
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip, limit=None: True)
    monkeypatch.setattr(
        chat_routes,
        "_run_tool_thread",
        lambda *a, **k: {"ok": True, "results": []},
    )
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        return _tool_call_response()

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)
    resp = client.post(
        "/api/v1/chat",
        headers=_auth_headers(),
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "where is the scripture where nephi says he will go and do",
                }
            ]
        },
    )
    assert resp.status_code == 200
    # 1 initial + 2 capped tool rounds + 1 final-answer synthesis retry
    # (not research). Without the cap this same stub burns 1 + 15 + 1.
    assert len(calls) == 1 + chat_routes.LOOKUP_MAX_ROUNDS + 1
    # Every tool-bearing round offered only the lookup menu. (The final
    # synthesis retry carries no tools key at all — also desirable.)
    assert "tools" in calls[0]
    for payload in calls:
        if "tools" not in payload:
            continue
        names = {t["function"]["name"] for t in payload["tools"]}
        assert names == set(chat_routes.LOOKUP_TOOLS)


def test_non_stream_research_question_keeps_full_menu(client, monkeypatch):
    """A research-shaped question is unaffected by the fast path."""
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip, limit=None: True)
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "done"},
                    "finish_reason": "stop",
                }
            ],
        }

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)
    resp = client.post(
        "/api/v1/chat",
        headers=_auth_headers(),
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "compare the creation accounts in genesis 1 and moses 2",
                }
            ]
        },
    )
    assert resp.status_code == 200
    names = {t["function"]["name"] for t in calls[0]["tools"]}
    assert "scripture_research" in names
    assert "scripture_graph_path" in names


def _two_identical_calls_response():
    def tc(call_id):
        return {
            "id": call_id,
            "type": "function",
            "function": {"name": "scripture_search",
                         "arguments": '{"query": "nephi go and do"}'},
        }
    return {
        "choices": [{
            "message": {"role": "assistant", "content": "",
                        "tool_calls": [tc("call_1"), tc("call_2")]},
            "finish_reason": "tool_calls",
        }],
    }


def _stop_response(content="done"):
    return {
        "choices": [{"message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}],
    }


def test_identical_calls_in_one_round_execute_once(client, monkeypatch):
    """Two identical tool calls in one round hit the DB once."""
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip, limit=None: True)
    executions = []

    def fake_call_tool(name, conn, **kwargs):
        executions.append((name, kwargs))
        return {"ok": True, "results": [{"ref": "1ne.3.7"}]}

    monkeypatch.setattr(chat_routes, "call_tool", fake_call_tool)
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        if len(calls) == 1:
            return _two_identical_calls_response()
        return _stop_response("1 Nephi 3:7")

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)
    resp = client.post(
        "/api/v1/chat",
        headers=_auth_headers(),
        json={"messages": [{"role": "user", "content":
                "where is the scripture where nephi says he will go and do"}]},
    )
    assert resp.status_code == 200
    assert len(executions) == 1
    # Both tool_call ids still get their (shared) result in context.
    data = resp.json()["data"]
    assert len(data["tool_results"]) == 2
    assert (data["tool_results"][0]["result"]
            == data["tool_results"][1]["result"])


def test_lookup_budget_clamped_research_untouched(client, monkeypatch):
    """Simple lookups are capped at the minimum thinking budget; deep
    questions keep whatever budget the client sent."""
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip, limit=None: True)
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        return _stop_response()

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)

    client.post("/api/v1/chat", headers=_auth_headers(), json={
        "messages": [{"role": "user", "content":
                      "where is the scripture where nephi says he will go and do"}],
        "max_tokens": 128000,
    })
    assert calls[0]["max_tokens"] == chat_routes.LOOKUP_MAX_TOKENS == 16_384

    calls.clear()
    client.post("/api/v1/chat", headers=_auth_headers(), json={
        "messages": [{"role": "user", "content":
                      "compare the creation accounts in genesis 1 and moses 2"}],
        "max_tokens": 128000,
    })
    assert calls[0]["max_tokens"] == 128000
