import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from web.lib.llm_provider import ProviderRouter


def test_native_model_is_allowlisted_and_stripped_for_upstream(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")
    monkeypatch.delenv("CHAT_ALLOWED_MODELS", raising=False)
    router = ProviderRouter()

    provider, model, targets = router.targets_for("opencode-go/muse-spark-1.2-contributor")

    assert provider == "opencode-go"
    assert model == "muse-spark-1.2-contributor"
    assert targets[0].base_url.endswith("/v1")


def test_complete_uses_mock_transport_and_native_model(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")

    seen = {}

    def handler(request):
        seen["authorization"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "model": "muse-spark-1.2-contributor",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "grounded"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        result = await router.complete(
            {
                "model": "opencode-go/muse-spark-1.2-contributor",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )
        await router.aclose()
        return result

    result = asyncio.run(run())
    assert result["choices"][0]["message"]["content"] == "grounded"
    assert seen["authorization"] == "Bearer test-key"
    assert seen["body"]["model"] == "muse-spark-1.2-contributor"


def test_worker_socket_pool_is_configured_without_exposing_keys(monkeypatch, tmp_path):
    socket_a = tmp_path / "worker-a.sock"
    socket_b = tmp_path / "worker-b.sock"
    listeners = []
    for socket_path in (socket_a, socket_b):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(socket_path))
        listener.listen()
        listeners.append(listener)

    monkeypatch.setenv("OPENCODE_GO_WORKER_SOCKETS", f"{socket_a},{socket_b}")
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)

    try:
        router = ProviderRouter()
        assert router.configured("opencode-go/muse-spark-1.2-contributor")
        _, _, targets = router.targets_for("opencode-go/muse-spark-1.2-contributor")
        assert [target.uds for target in targets] == [str(socket_a), str(socket_b)]
        assert all(not target.api_key for target in targets)
    finally:
        for listener in listeners:
            listener.close()


def test_worker_socket_pool_is_not_configured_when_paths_are_missing(monkeypatch, tmp_path):
    socket_path = tmp_path / "missing-worker.sock"
    monkeypatch.setenv("OPENCODE_GO_WORKER_SOCKETS", str(socket_path))
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)

    assert not ProviderRouter().configured("opencode-go/muse-spark-1.2-contributor")


def test_worker_health_is_checked_before_completion(monkeypatch, tmp_path):
    socket_path = tmp_path / "worker.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    listener.listen()
    monkeypatch.setenv("OPENCODE_GO_WORKER_SOCKETS", str(socket_path))
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True, "ready": True})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-worker",
                "choices": [{"message": {"role": "assistant", "content": "ready"}}],
            },
        )

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        try:
            return await router.complete(
                {
                    "model": "opencode-go/muse-spark-1.2-contributor",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await router.aclose()

    try:
        result = asyncio.run(run())
    finally:
        listener.close()

    assert result["choices"][0]["message"]["content"] == "ready"
    assert paths == ["/health", "/chat/completions"]


def test_complete_returns_structured_error_for_malformed_success(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")

    def handler(_request):
        return httpx.Response(200, content=b"not-json")

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        try:
            return await router.complete(
                {
                    "model": "opencode-go/muse-spark-1.2-contributor",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await router.aclose()

    result = asyncio.run(run())
    assert result == {
        "error": {"code": 502, "message": "Provider returned malformed JSON"},
    }


def test_worker_reports_not_ready_without_credential_and_stops_on_sigterm(tmp_path):
    socket_path = tmp_path / "worker.sock"
    worker_path = Path(__file__).parents[1] / "scripts" / "opencode_go_worker.py"
    environment = os.environ.copy()
    environment.pop("OPENCODE_API_KEY", None)
    worker = subprocess.Popen(
        [sys.executable, str(worker_path), "--socket", str(socket_path)],
        env=environment,
    )

    try:
        deadline = time.monotonic() + 2
        while not socket_path.exists() and time.monotonic() < deadline:
            if worker.poll() is not None:
                raise AssertionError(f"worker exited early with code {worker.returncode}")
            time.sleep(0.01)
        assert socket_path.exists()

        with httpx.Client(
            transport=httpx.HTTPTransport(uds=str(socket_path)),
            base_url="http://worker",
            timeout=1,
        ) as client:
            health = client.get("/health")
        assert health.status_code == 503
        assert health.json() == {"ok": False, "ready": False}

        worker.send_signal(signal.SIGTERM)
        assert worker.wait(timeout=2) == 0
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()


# ── Track G4: failover / timeout contract tests ─────────────────────────────

def test_complete_429_sets_cooldown_and_returns_provider_error(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")

    def handler(_request):
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        try:
            _, _, targets = router.targets_for(
                "opencode-go/muse-spark-1.2-contributor"
            )
            result = await router.complete(
                {
                    "model": "opencode-go/muse-spark-1.2-contributor",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
            return (
                result,
                router._cooldown_until.get(targets[0].identity, 0),
            )
        finally:
            await router.aclose()

    result, cooldown_until = asyncio.run(run())
    assert result["error"]["code"] == 429
    assert result["error"]["message"] == "rate limited"
    # The account is cooling down, so the next request tries another first.
    assert cooldown_until > time.monotonic()


def test_network_timeout_falls_through_to_structured_503(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")

    def handler(_request):
        raise httpx.ConnectError("connection reset by peer")

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        try:
            return await router.complete(
                {
                    "model": "opencode-go/muse-spark-1.2-contributor",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await router.aclose()

    result = asyncio.run(run())
    assert result["error"]["code"] == 503
    assert "connection reset" in result["error"]["message"]


def test_stream_fails_over_to_second_account_after_429(monkeypatch, tmp_path):
    """A 429 on account A must fail over to B before any bytes are streamed."""
    socket_a = tmp_path / "worker-a.sock"
    socket_b = tmp_path / "worker-b.sock"
    listeners = []
    for socket_path in (socket_a, socket_b):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(socket_path))
        listener.listen()
        listeners.append(listener)

    monkeypatch.setenv("OPENCODE_GO_WORKER_SOCKETS", f"{socket_a},{socket_b}")
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)

    chat_calls = {"n": 0}

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True, "ready": True})
        chat_calls["n"] += 1
        if chat_calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-b",
                "choices": [
                    {"message": {"role": "assistant", "content": "from-b"}}
                ],
            },
        )

    async def run():
        router = ProviderRouter(httpx.MockTransport(handler))
        try:
            async with router.stream(
                {
                    "model": "opencode-go/muse-spark-1.2-contributor",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            ) as response:
                assert response.status_code == 200
                body = response.json()
            return body
        finally:
            await router.aclose()

    try:
        body = asyncio.run(run())
    finally:
        for listener in listeners:
            listener.close()

    # Exactly one upstream attempt failed (A), then B served the completion:
    # failover happened before any response bytes reached the caller.
    assert chat_calls["n"] == 2
    assert body["choices"][0]["message"]["content"] == "from-b"
