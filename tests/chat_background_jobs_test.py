"""Chat background job tests (Track A3/A4): create → poll → done lifecycle,
after_seq replay, cancel, per-IP concurrency cap, and server-side completion
save to the conversation session.

Run: pytest tests/chat_background_jobs_test.py -q
"""
import asyncio
import json
import time

import pytest

from web.routes import chat as chat_routes
from web.lib import jobs as chat_jobs


def _auth_headers():
    return {"Origin": "https://scriptureengine.org"}


def _sse_chunk(payload: dict) -> str:
    return "data: " + json.dumps(payload)


class FakeResp:
    def __init__(self, lines, status_code=200):
        self.status_code = status_code
        self._lines = lines

    async def aread(self):
        return b""

    def aiter_lines(self):
        async def gen():
            for line in self._lines:
                yield line
        return gen()


class _FakeStreamCtx:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class FakeHttpClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def stream(self, method, url, **kwargs):
        return _FakeStreamCtx(self._responses.pop(0))


def _complete_stream(content="hello job"):
    return [
        _sse_chunk({"choices": [{"delta": {"content": content}}]}),
        _sse_chunk({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
        "data: [DONE]",
    ]


def _stub_no_tools(monkeypatch, call_fn=None):
    """Stub the tool-round call so the pipeline goes straight to the final stream."""
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip: True)

    async def default_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {}}

    monkeypatch.setattr(chat_routes, "call_deepseek", call_fn or default_call)


def _poll_until(client, job_id, want=("done", "failed", "cancelled"), timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get(f"/api/v1/chat/jobs/{job_id}").json()["data"]
        if data["status"] in want:
            return data
        time.sleep(0.05)
    return client.get(f"/api/v1/chat/jobs/{job_id}").json()["data"]


def test_job_lifecycle_create_poll_done(client, monkeypatch):
    _stub_no_tools(monkeypatch)
    fake_http = FakeHttpClient([FakeResp(_complete_stream())])
    monkeypatch.setattr(chat_routes, "_http_client", fake_http)

    resp = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    job_id = resp.json()["data"]["job_id"]
    assert resp.json()["data"]["status"] == "queued"

    data = _poll_until(client, job_id)
    assert data["status"] == "done", data
    assert data["done"]["content"] == "hello job"
    assert data["done"]["finish_reason"] == "stop"
    types = [e["type"] for e in data["events"]]
    assert "text" in types
    assert "done" in types


def test_job_after_seq_replay(client, monkeypatch):
    _stub_no_tools(monkeypatch)
    fake_http = FakeHttpClient([FakeResp(_complete_stream("full"))])
    monkeypatch.setattr(chat_routes, "_http_client", fake_http)

    resp = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    job_id = resp.json()["data"]["job_id"]
    _poll_until(client, job_id)

    # after_seq beyond everything → no incremental events, but final snapshot present
    data = client.get(f"/api/v1/chat/jobs/{job_id}?after_seq=999999").json()["data"]
    assert data["events"] == []
    assert data["status"] == "done"
    assert data["done"]["content"] == "full"

    # after_seq = 0 → all buffered events (each carries a seq)
    data = client.get(f"/api/v1/chat/jobs/{job_id}?after_seq=0").json()["data"]
    seqs = [e["seq"] for e in data["events"]]
    assert seqs == sorted(seqs) and len(seqs) == len(set(seqs))  # monotonic, unique


def test_job_cancel_stops_running_job(client, monkeypatch):
    async def slow_call(payload):
        await asyncio.sleep(10)
        return {"choices": [{"message": {"role": "assistant", "content": "never"}}], "usage": {}}

    _stub_no_tools(monkeypatch, call_fn=slow_call)
    monkeypatch.setattr(chat_routes, "_http_client", FakeHttpClient([FakeResp(_complete_stream())]))

    resp = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    job_id = resp.json()["data"]["job_id"]

    cancel = client.post(f"/api/v1/chat/jobs/{job_id}/cancel").json()
    assert cancel["ok"] is True
    assert cancel["data"]["cancelled"] is True

    data = _poll_until(client, job_id, want=("cancelled",))
    assert data["status"] == "cancelled"


def test_job_per_ip_concurrency_cap(client, monkeypatch):
    async def slow_call(payload):
        await asyncio.sleep(10)
        return {"choices": [{"message": {"role": "assistant", "content": "never"}}], "usage": {}}

    _stub_no_tools(monkeypatch, call_fn=slow_call)
    monkeypatch.setattr(chat_routes, "_http_client", FakeHttpClient([FakeResp(_complete_stream())]))
    monkeypatch.setattr(chat_jobs, "MAX_JOBS_PER_IP", 1)

    first = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                        json={"messages": [{"role": "user", "content": "hi"}]})
    assert first.json()["ok"] is True

    second = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                         json={"messages": [{"role": "user", "content": "hi again"}]})
    assert second.json()["ok"] is False
    assert "Too many active chat jobs" in second.json()["error"]


def test_job_requires_api_key(client, monkeypatch):
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "")
    resp = client.post("/api/v1/chat/jobs", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.json()["ok"] is False
    assert "DEEPSEEK_API_KEY" in resp.json()["error"]


def test_job_poll_unknown_job(client):
    data = client.get("/api/v1/chat/jobs/doesnotexist").json()
    assert data["ok"] is False


def test_job_saves_assistant_to_conversation(client, monkeypatch):
    from lib.db import get_db

    session_id = "test-session-jobs"
    conn = get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO conversation_sessions (id, title) VALUES (?, ?)",
                     (session_id, "jobs test"))
        conn.commit()
    except Exception as e:
        conn.close()
        pytest.skip(f"conversation_sessions unavailable: {e}")

    _stub_no_tools(monkeypatch)
    fake_http = FakeHttpClient([FakeResp(_complete_stream("saved answer"))])
    monkeypatch.setattr(chat_routes, "_http_client", fake_http)

    resp = client.post("/api/v1/chat/jobs", headers=_auth_headers(), json={
        "messages": [{"role": "user", "content": "hi"}],
        "session_id": session_id,
        "client_message_id": "user-msg-1",
    })
    job_id = resp.json()["data"]["job_id"]
    data = _poll_until(client, job_id)
    assert data["status"] == "done"

    try:
        conn = get_db()
        row = conn.execute(
            "SELECT role, content, metadata_json FROM conversation_messages WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        conn.close()
    except Exception:
        pytest.skip("conversation_messages unavailable")
    assert row is not None, "assistant message not saved"
    assert row["role"] == "assistant"
    assert "saved answer" in row["content"]
