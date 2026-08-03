"""Chat reliability tests: finish_reason detection, truncation retry, heartbeats.

Covers the guards added in Track A1 of docs/plans/chat-background-jobs.md:
  - finish_reason="length" triggers a one-shot retry with a bigger max_tokens
    (both the non-stream /chat endpoint and the /chat/stream final phase)
  - stream_options.include_usage is sent on streaming calls
  - _heartbeat_lines injects heartbeats during long silent thinking pauses

Run: pytest tests/chat_reliability_test.py -q
"""
import asyncio
import json

import pytest

from web.routes import chat as chat_routes


# ── Unit helpers ────────────────────────────────────────────────────────


def test_retry_budget_bumps_and_caps():
    assert chat_routes._retry_budget(4096) == 16_384
    assert chat_routes._retry_budget(16_384) == 65_536
    assert chat_routes._retry_budget(32_768) == 128_000  # capped at MAX_OUTPUT_TOKENS
    assert chat_routes._retry_budget(128_000) == 128_000


def test_finish_reason_extraction():
    assert chat_routes._finish_reason({"choices": [{"finish_reason": "length"}]}) == "length"
    assert chat_routes._finish_reason({"choices": [{"finish_reason": "stop"}]}) == "stop"
    assert chat_routes._finish_reason({"choices": []}) == ""
    assert chat_routes._finish_reason({}) == ""


def test_heartbeat_lines_injects_heartbeats_on_silence():
    """A slow line should be preceded by one or more ('hb', None) markers.

    Runs via asyncio.run() — deliberately NOT pytest.mark.asyncio so the suite
    passes without the pytest-asyncio plugin (the deploy gate's .venv lacks it)."""

    class SlowIter:
        def __init__(self):
            self.i = 0

        async def __anext__(self):
            if self.i == 0:
                self.i += 1
                return "first"
            if self.i == 1:
                await asyncio.sleep(0.3)  # silence longer than the interval
                self.i += 1
                return "second"
            raise StopAsyncIteration

    class FakeResp:
        def aiter_lines(self):
            return SlowIter()

    async def scenario():
        out = []
        async for kind, value in chat_routes._heartbeat_lines(FakeResp(), interval=0.05):
            out.append((kind, value))
        return out

    out = asyncio.run(scenario())
    kinds = [k for k, _ in out]
    assert kinds.count("hb") >= 1
    assert ("line", "first") in out
    assert ("line", "second") in out
    # Lines must stay in order around the injected heartbeats
    line_order = [v for k, v in out if k == "line"]
    assert line_order == ["first", "second"]


def test_heartbeat_lines_raises_upstream_error():
    class BrokenIter:
        def __init__(self):
            self.i = 0

        async def __anext__(self):
            if self.i == 0:
                self.i += 1
                return "line"
            raise RuntimeError("upstream died")

    class FakeResp:
        def aiter_lines(self):
            return BrokenIter()

    async def scenario():
        collected = []
        async for _ in chat_routes._heartbeat_lines(FakeResp(), interval=0.05):
            collected.append(_)
        return collected

    with pytest.raises(RuntimeError, match="upstream died"):
        asyncio.run(scenario())


# ── Non-stream endpoint (/api/v1/chat) ──────────────────────────────────


def _auth_headers():
    return {"Origin": "https://scriptureengine.org"}


def _no_tools_response(content, finish_reason="stop"):
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}],
        "usage": {"completion_tokens": 10},
    }


def test_non_stream_retries_once_on_length(client, monkeypatch):
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip: True)
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        if len(calls) == 1:
            return _no_tools_response("partial ans", finish_reason="length")
        return _no_tools_response("complete answer")

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)

    resp = client.post("/api/v1/chat", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["content"] == "complete answer"
    assert data["finish_reason"] == "stop"
    assert len(calls) == 2
    # Server default max_tokens is now MIN_THINKING_TOKENS (16384); retry bumps it 4x
    assert calls[1]["max_tokens"] == chat_routes._retry_budget(16_384) == 65_536


def test_non_stream_no_retry_on_stop(client, monkeypatch):
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip: True)
    calls = []

    async def fake_call(payload):
        calls.append(payload)
        return _no_tools_response("ok")

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)

    resp = client.post("/api/v1/chat", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    assert resp.json()["data"]["content"] == "ok"
    assert len(calls) == 1


# ── Stream endpoint (/api/v1/chat/stream) ───────────────────────────────


class FakeResp:
    """Minimal stand-in for the httpx stream response."""

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
    """Replaces chat_routes._http_client for the final stream call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.streamed_payloads = []

    def stream(self, method, url, **kwargs):
        self.streamed_payloads.append(kwargs.get("json"))
        return _FakeStreamCtx(self._responses.pop(0))


def _sse_chunk(payload: dict) -> str:
    return "data: " + json.dumps(payload)


def test_stream_truncated_regenerates_with_more_budget(client, monkeypatch):
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip: True)

    async def fake_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {}}

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)

    truncated = [
        _sse_chunk({"choices": [{"delta": {"content": "partial "}}]}),
        _sse_chunk({"choices": [{"delta": {}, "finish_reason": "length"}]}),
        "data: [DONE]",
    ]
    complete = [
        _sse_chunk({"choices": [{"delta": {"content": "full answer"}}]}),
        _sse_chunk({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
        "data: [DONE]",
    ]
    fake_http = FakeHttpClient([FakeResp(truncated), FakeResp(complete)])
    monkeypatch.setattr(chat_routes, "_http_client", fake_http)

    resp = client.post("/api/v1/chat/stream", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    text = resp.text

    # Client sees the partial, then a "truncated" signal, then the regenerated answer
    assert '"type": "truncated"' in text
    assert "partial " in text
    assert "full answer" in text
    # done event carries the final finish_reason
    assert '"finish_reason": "stop"' in text
    # The second stream call used the bumped budget
    assert len(fake_http.streamed_payloads) == 2
    assert fake_http.streamed_payloads[1]["max_tokens"] == 65_536
    # stream_options.include_usage is sent on every streaming call
    assert all(p.get("stream_options") == {"include_usage": True} for p in fake_http.streamed_payloads)


def test_stream_happy_path_emits_done_with_finish_reason(client, monkeypatch):
    monkeypatch.setattr(chat_routes, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chat_routes, "_check_rate_limit", lambda ip: True)

    async def fake_call(payload):
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {}}

    monkeypatch.setattr(chat_routes, "call_deepseek", fake_call)

    lines = [
        _sse_chunk({"choices": [{"delta": {"content": "hello"}}]}),
        _sse_chunk({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
        "data: [DONE]",
    ]
    fake_http = FakeHttpClient([FakeResp(lines)])
    monkeypatch.setattr(chat_routes, "_http_client", fake_http)

    resp = client.post("/api/v1/chat/stream", headers=_auth_headers(),
                       json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    text = resp.text
    assert '"type": "done"' in text
    assert '"finish_reason": "stop"' in text
    assert "hello" in text
    assert '"type": "truncated"' not in text
