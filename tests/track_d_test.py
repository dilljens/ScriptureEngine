"""Track D tests: agent-visible swarm tools — scripture_batch_lookup (registry)
and scripture_research_parallel (worker pool as a synchronous tool call).

Run: pytest tests/track_d_test.py -q
"""
import json
import sqlite3
from pathlib import Path

from lib.api import call_tool
from lib.db import get_db
from web.routes import chat as chat_routes

PROD_DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


def test_batch_lookup_registered_and_works():
    from lib.api import TOOL_REGISTRY
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
    import asyncio
    from web.routes import chat as chat_routes

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
