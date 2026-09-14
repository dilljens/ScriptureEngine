"""Subagent fan-out tests (Track B): planner parse/fallback, worker pool
parallelism + failure isolation, synthesis message building, and the full
planner→workers→synthesizer pipeline through _chat_pipeline.

Run: pytest tests/subagents_test.py -q
"""
import asyncio
import json
import time

from web.lib import subagents as sub
from web.routes import chat as chat_routes
from tests._chat_fakes import FakeHttpClient, FakeResp
from tests.chat_speedup_test import _complete_stream, _body


# ── Unit: planner ──

def test_should_plan_heuristic():
    assert sub.should_plan([{"role": "user", "content": "hi"}]) is False
    assert sub.should_plan([{"role": "user", "content": "hi" * 300}]) is True
    assert sub.should_plan([{"role": "user", "content": "Compare Genesis 1 and John 1 and explain the temple imagery"}]) is True
    assert sub.should_plan([{"role": "user", "content": "a? b? c?"}]) is True


def test_parse_plan_valid_and_capped():
    plan = sub._parse_plan('{"tasks": [{"id":"t1","goal":"g1","tools":["scripture_verse"]},'
                           '{"id":"t2","goal":"g2","tools":[]},{"id":"t3","goal":"g3"},'
                           '{"id":"t4","goal":"g4"},{"id":"t5","goal":"g5"}]}')
    assert plan is not None
    assert len(plan) == 3, "capped at MAX_WORKERS"
    assert plan[0]["goal"] == "g1"


def test_parse_plan_fenced_and_garbage():
    plan = sub._parse_plan('```json\n{"tasks":[{"id":"t1","goal":"g"}]}\n```')
    assert plan and plan[0]["goal"] == "g"
    assert sub._parse_plan("no plan here") is None
    assert sub._parse_plan("") is None
    assert sub._parse_plan('{"tasks": "not a list"}') is None


def test_plan_research_stub(monkeypatch):
    async def fake_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": '{"tasks":[{"id":"t1","goal":"g"}]}'}}]}

    async def main():
        return await sub.plan_research(fake_call, [{"role": "user", "content": "q"}], ["scripture_verse"])

    plan = asyncio.run(main())
    assert plan and plan[0]["goal"] == "g"


def test_plan_research_garbage_falls_back(monkeypatch):
    async def fake_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": "I cannot plan"}}]}

    async def main():
        return await sub.plan_research(fake_call, [{"role": "user", "content": "q"}], [])

    assert asyncio.run(main()) is None


# ── Unit: workers ──

def test_run_worker_single_round(monkeypatch):
    async def fake_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": "findings"}}]}

    async def main():
        events = []
        report = await sub.run_worker({"id": "t1", "goal": "look up", "tools": []},
                                      [{"function": {"name": "scripture_verse"}}], [],
                                      fake_call, None, events.append)
        return report, events

    report, events = asyncio.run(main())
    assert report["content"] == "findings"
    assert report["tool_results"] == []
    assert report["task_id"] == "t1"


def test_run_worker_tool_round_then_content(monkeypatch):
    calls = {"n": 0}

    async def fake_call(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "scripture_verse",
                 "arguments": json.dumps({"book": "gen", "chapter": 1, "verse": 1})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "found it"}}]}

    async def run_tool(tc):
        return {"ok": True, "verse": "In the beginning..."}

    async def main():
        events = []
        report = await sub.run_worker({"id": "t1", "goal": "look up gen 1:1", "tools": ["scripture_verse"]},
                                      [{"function": {"name": "scripture_verse"}}], [], fake_call, run_tool, events.append)
        return report, events

    report, events = asyncio.run(main())
    assert report["content"] == "found it"
    assert len(report["tool_results"]) == 1
    assert report["tool_results"][0]["name"] == "scripture_verse"
    assert any(e["type"] == "tool_progress" and e.get("worker") == "t1" for e in events)


def test_run_workers_parallel_and_isolated():
    async def slow_call(payload):
        await asyncio.sleep(0.3)
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}

    async def boom_call(payload):
        goal = payload["messages"][-1]["content"]
        if goal == "y":  # the failing task
            return {"error": {"message": "worker crashed"}}
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}

    async def main():
        tasks = [{"id": "t1", "goal": "a", "tools": []},
                 {"id": "t2", "goal": "b", "tools": []}]
        t0 = time.monotonic()
        reports = await sub.run_workers(tasks, [], [], slow_call, None, lambda e: None)
        elapsed = time.monotonic() - t0
        # one failing worker doesn't abort the others
        mixed = await sub.run_workers([{"id": "ok", "goal": "x", "tools": []},
                                       {"id": "bad", "goal": "y", "tools": []}],
                                      [], [], boom_call, None, lambda e: None)
        return reports, elapsed, mixed

    reports, elapsed, mixed = asyncio.run(main())
    assert all(r["content"] == "done" for r in reports)
    assert elapsed < 0.55, f"workers ran serially: {elapsed:.2f}s"  # 2×0.3s parallel ≈ 0.3s
    by_id = {r["task_id"]: r for r in mixed}
    assert "error" in by_id["bad"]
    assert by_id["ok"]["content"] == "done"


def test_build_synthesis_messages():
    msgs = [{"role": "user", "content": "original question"}]
    out = sub.build_synthesis_messages(msgs, [
        {"task_id": "t1", "content": "gen 1:1 data", "tool_results": []},
        {"task_id": "t2", "content": "", "error": "timeout", "tool_results": []},
    ])
    assert len(out) == len(msgs) + 1
    tail = out[-1]["content"]
    assert "gen 1:1 data" in tail
    assert "failed: timeout" in tail
    assert msgs[-1]["content"] == "original question"  # original untouched


# ── Integration: full pipeline with subagents ──

def test_chat_pipeline_subagent_fanout(monkeypatch):
    """Planner → workers → synthesizer through _chat_pipeline."""
    body = _body(messages=[{"role": "user", "content": "Compare Genesis 1 and John 1 and explain the differences in detail"}])
    msgs = [{"role": "user", "content": body.messages[0]["content"]}]

    calls = {"n": 0}

    async def fake_deepseek(payload):
        calls["n"] += 1
        if calls["n"] == 1:  # planner
            return {"choices": [{"message": {"role": "assistant", "content": json.dumps({
                "tasks": [
                    {"id": "t1", "goal": "Genesis 1 gematria", "tools": ["scripture_gematria"]},
                    {"id": "t2", "goal": "John 1 connections", "tools": ["scripture_connections"]},
                ]})}}]}
        # workers — concurrent, order not guaranteed
        return {"choices": [{"message": {"role": "assistant", "content": "worker findings"}}]}

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_deepseek)
    monkeypatch.setattr(chat_routes, "_http_client",
                        FakeHttpClient([FakeResp(_complete_stream("synthesized answer"))]))

    async def main():
        events = []
        async for ev in chat_routes._chat_pipeline(body, msgs):
            events.append(ev)
        return events

    events = asyncio.run(main())
    types = [e["type"] for e in events]
    assert "plan" in types, types
    assert events[types.index("plan")]["tasks"][0]["id"] == "t1"
    done = [e for e in events if e["type"] == "done"]
    assert done, "no done event"
    assert done[0]["final_content"] == "synthesized answer"
    assert calls["n"] == 3, f"expected planner+2 workers, got {calls['n']}"


# ── Track D: agent-visible swarm tools ─────────────────────────────────────
# (folded from tests/track_d_test.py — same worker-pool machinery, one home.)

def test_batch_lookup_registered_and_works():
    from lib.api import TOOL_REGISTRY, call_tool
    from lib.db import get_db

    assert "scripture_batch_lookup" in TOOL_REGISTRY
    assert "scripture_research_parallel" in [t["function"]["name"] for t in chat_routes.TOOL_DEFINITIONS]

    conn = get_db()
    try:
        r = call_tool("scripture_batch_lookup", conn, verses=["gen.1.1", "john.3.16", "bad.ref"])
        assert r["count"] == 3
        assert r["verses"]["gen.1.1"]["text_english"]
        assert "error" in r["verses"]["bad.ref"]
    finally:
        conn.close()


def test_research_parallel_returns_findings():
    async def fake_llm(payload):
        system = payload["messages"][0]["content"]
        if "Available tools" in system:  # planner call
            return {"choices": [{"message": {"role": "assistant", "content": json.dumps({
                "tasks": [
                    {"id": "t1", "goal": "gematria of Genesis 1:1", "tools": []},
                    {"id": "t2", "goal": "connections of John 1:1", "tools": []},
                ]})}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "worker findings here"}}]}

    result = chat_routes._run_research_parallel({"query": "Compare Genesis 1 and John 1 deeply"}, call_llm=fake_llm)
    assert result["tasks"] == 2
    assert "worker findings here" in result["findings"][0]


def test_research_parallel_requires_query():
    result = chat_routes._run_research_parallel({}, call_llm=lambda p: None)
    assert "error" in result


def test_tool_thread_routes_research_parallel():
    """_run_tool_thread special-cases scripture_research_parallel before the
    scope gate / registry path."""
    async def fake_llm(payload):
        return {"choices": [{"message": {"role": "assistant", "content": json.dumps({
            "tasks": [{"id": "t1", "goal": "simple task", "tools": []}]})}}]}

    # _run_tool_thread calls _run_research_parallel with default call_llm (network).
    # Verify the routing exists by patching _run_research_parallel itself.
    calls = {}
    orig = chat_routes._run_research_parallel

    def spy(args, call_llm=None):
        calls["seen"] = args.get("query")
        return {"tasks": 1, "findings": ["ok"]}

    chat_routes._run_research_parallel = spy
    try:
        r = chat_routes._run_tool_thread("scripture_research_parallel", {"query": "x"}, [])
        assert r == {"tasks": 1, "findings": ["ok"]}
        assert calls["seen"] == "x"
    finally:
        chat_routes._run_research_parallel = orig
