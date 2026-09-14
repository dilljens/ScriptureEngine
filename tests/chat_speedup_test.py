"""Chat speedup tests (Track A1/A2): real parallel tool execution via
asyncio.to_thread, tool-result caching, and scope-gated error handling.

Run: pytest tests/chat_speedup_test.py -q
"""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from web.routes import chat as chat_routes

from tests._chat_fakes import FakeHttpClient, FakeResp


# ── Fakes (shared helpers in tests/_chat_fakes.py) ──

def _sse(data) -> str:
    return "data: " + json.dumps(data)


def _complete_stream(content="final answer"):
    return [
        _sse({"choices": [{"delta": {"content": content[:6]}, "finish_reason": None}]}),
        _sse({"choices": [{"delta": {"content": content[6:]}, "finish_reason": None}]}),
        _sse({"choices": [{"delta": {}, "finish_reason": "stop"}],
              "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}),
        "data: [DONE]",
    ]


def _body(**over):
    base = dict(
        model="deepseek-v4-flash", max_tokens=16384, temperature=0.7,
        tools_enabled=True, disabled_tools=[], scopes=[],
        mode="chat", session_id="", client_message_id="",
        messages=[{"role": "user", "content": "hi"}],
    )
    base.update(over)
    return SimpleNamespace(**base)


def _tool_call(cid, name, args):
    return {
        "id": cid, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _msg_with_tools(tool_calls, content=""):
    return {"choices": [{"message": {"role": "assistant", "content": content,
                                     "tool_calls": tool_calls}}], "usage": {}}


def _msg_final(content="final answer"):
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": {}}


async def _collect(body, msgs):
    events = []
    async for ev in chat_routes._chat_pipeline(body, msgs):
        events.append(ev)
    return events


# ── Tests ──

def test_tool_round_runs_in_parallel(monkeypatch):
    """3 slow tool calls complete in ~max, not ~sum (real threading)."""
    calls = []

    def slow_tool(name, conn, **kwargs):
        calls.append(name)
        time.sleep(0.25)
        return {"ok": True, "tool": name}

    monkeypatch.setattr(chat_routes, "call_tool", slow_tool)

    round1 = _msg_with_tools([
        _tool_call("c1", "scripture_verse", {"book": "gen", "chapter": 1, "verse": 1}),
        _tool_call("c2", "scripture_search", {"query": "covenant"}),
        _tool_call("c3", "scripture_gematria", {"word": "יהוה"}),
    ])
    n = {"calls": 0}

    async def fake_deepseek(payload):
        n["calls"] += 1
        return round1 if n["calls"] == 1 else _msg_final()

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_deepseek)
    monkeypatch.setattr(chat_routes, "_http_client", FakeHttpClient([FakeResp(_complete_stream())]))

    body = _body()
    t0 = time.monotonic()
    events = asyncio.run(_collect(body, [{"role": "user", "content": "hi"}]))
    elapsed = time.monotonic() - t0

    # All three tools ran
    assert sorted(calls) == ["scripture_gematria", "scripture_search", "scripture_verse"], calls
    # Serial would be >= 0.75s; parallel should be ~0.25-0.4s
    assert elapsed < 0.6, f"tools ran serially: {elapsed:.2f}s"

    done = [e for e in events if e["type"] == "done"]
    assert done, "no done event"
    assert len(done[0]["tool_results"]) == 3


def test_tool_result_cache_hits_skip_execution(monkeypatch):
    """Same deterministic tool+args returns cached result without re-running."""
    real_calls = []

    def counting_tool(name, conn, **kwargs):
        real_calls.append((name, kwargs))
        return {"ok": True, "value": 42}

    monkeypatch.setattr(chat_routes, "call_tool", counting_tool)
    chat_routes.tool_cache.clear()

    args = {"book": "gen", "chapter": 1, "verse": 1}
    r1 = chat_routes._run_tool_thread("scripture_verse", args, [])
    r2 = chat_routes._run_tool_thread("scripture_verse", args, [])
    r3 = chat_routes._run_tool_thread("scripture_verse", args, [])

    assert r1 == r2 == r3 == {"ok": True, "value": 42}
    assert len(real_calls) == 1, f"cache miss: executed {len(real_calls)} times"

    # Different args → new execution
    chat_routes._run_tool_thread("scripture_verse", {"book": "gen", "chapter": 2, "verse": 1}, [])
    assert len(real_calls) == 2


def test_scope_gated_tool_rejected_before_execution(monkeypatch):
    """A scoped tool the request didn't opt into returns an error, no execution."""
    executed = []

    def counting_tool(name, conn, **kwargs):
        executed.append(name)
        return {"ok": True}

    monkeypatch.setattr(chat_routes, "call_tool", counting_tool)
    result = chat_routes._run_tool_thread("scripture_cfm_lesson", {}, [])  # no scopes
    assert "error" in result
    assert "disabled" in result["error"]
    assert executed == [], "gated tool executed despite missing scope"

    # With the scope granted, it executes
    ok = chat_routes._run_tool_thread("scripture_cfm_lesson", {}, ["cfm"])
    assert ok == {"ok": True}
    assert executed == ["scripture_cfm_lesson"]


def test_non_cacheable_tool_not_cached(monkeypatch):
    """Tools outside the cache whitelist always execute."""
    real_calls = []
    monkeypatch.setattr(chat_routes, "call_tool",
                        lambda name, conn, **kw: real_calls.append(name) or {"ok": True})
    chat_routes.tool_cache.clear()

    chat_routes._run_tool_thread("scripture_graph_path", {"start": "gen.1.1", "end": "john.1.1"}, [])
    chat_routes._run_tool_thread("scripture_graph_path", {"start": "gen.1.1", "end": "john.1.1"}, [])
    assert len(real_calls) == 2
