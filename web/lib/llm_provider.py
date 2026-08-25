"""Small provider router for the ScriptureEngine chat proxy.

The chat API speaks the OpenAI chat-completions shape, but the upstream can be
DeepSeek or the native OpenCode Go gateway.  OpenCode Go credentials are
intentionally expected behind local worker sockets (workers are launched with
``ai-secret exec``); the web process never needs to read the keys.

This module does not know about OpenCode's TUI balancer database.  That database
is a private credential store, not an application-facing proxy.
"""

from __future__ import annotations

import asyncio
import os
import stat
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx

RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})
DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_OPENCODE_GO_BASE = "https://opencode.ai/zen/go/v1"
DEFAULT_OPENCODE_GO_MODEL = "muse-spark-1.2-contributor"
WORKER_HEALTH_TIMEOUT = 2.0

DEEPSEEK_PRICING = {
    "input": 0.14,
    "output": 0.28,
    "cache_hit": 0.07,
}


@dataclass(frozen=True)
class ProviderTarget:
    """One routable upstream account or isolated local worker."""

    provider: str
    account: str
    base_url: str
    api_key: str = ""
    uds: str = ""

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.account}"


class ProviderRouter:
    """Route chat-completion requests with bounded account failover.

    ``transport`` is injectable for tests.  Production OpenCode Go workers are
    selected through ``OPENCODE_GO_WORKER_SOCKETS``; direct API-key mode exists
    for local development and single-account deployments only.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._next: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [part.strip() for part in (value or "").split(",") if part.strip()]

    @property
    def default_model(self) -> str:
        configured = os.environ.get("CHAT_MODEL", "").strip()
        if configured:
            return configured
        if os.environ.get("CHAT_PROVIDER", "deepseek").strip().lower() == "opencode-go":
            return f"opencode-go/{self.opencode_go_model}"
        return os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)

    @property
    def deepseek_model(self) -> str:
        return os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()

    @property
    def opencode_go_model(self) -> str:
        return os.environ.get("OPENCODE_GO_MODEL", DEFAULT_OPENCODE_GO_MODEL).strip()

    @property
    def opencode_go_base(self) -> str:
        return os.environ.get("OPENCODE_GO_BASE_URL", DEFAULT_OPENCODE_GO_BASE).rstrip("/")

    def allowed_models(self) -> set[str]:
        configured = self._csv(os.environ.get("CHAT_ALLOWED_MODELS", ""))
        if configured:
            return set(configured)
        return {
            self.deepseek_model,
            f"deepseek/{self.deepseek_model}",
            self.opencode_go_model,
            f"opencode-go/{self.opencode_go_model}",
        }

    def validate_model(self, model: str) -> tuple[bool, str]:
        model = (model or self.default_model).strip()
        if model not in self.allowed_models():
            return False, f"Model is not enabled: {model}"
        return True, model

    def _provider_model(self, model: str) -> tuple[str, str]:
        model = (model or self.default_model).strip()
        if model.startswith("opencode-go/"):
            return "opencode-go", model.split("/", 1)[1]
        if model.startswith("deepseek/"):
            return "deepseek", model.split("/", 1)[1]
        if model == self.opencode_go_model:
            return "opencode-go", model
        return "deepseek", model

    def is_opencode_go_model(self, model: str | None) -> bool:
        provider, _ = self._provider_model(model or self.default_model)
        return provider == "opencode-go"

    def targets_for(self, model: str) -> tuple[str, str, list[ProviderTarget]]:
        provider, upstream_model = self._provider_model(model)
        if provider == "opencode-go":
            sockets = self._csv(os.environ.get("OPENCODE_GO_WORKER_SOCKETS", ""))
            if sockets:
                targets = [
                    ProviderTarget(
                        provider=provider,
                        account=f"worker-{index + 1}",
                        base_url="http://worker",
                        uds=socket_path,
                    )
                    for index, socket_path in enumerate(sockets)
                ]
            else:
                api_key = os.environ.get("OPENCODE_API_KEY", "").strip()
                if not api_key:
                    api_key = os.environ.get("OPENCODE_GO_API_KEY", "").strip()
                targets = (
                    [
                        ProviderTarget(
                            provider=provider,
                            account="direct",
                            base_url=self.opencode_go_base,
                            api_key=api_key,
                        )
                    ]
                    if api_key
                    else []
                )
            return provider, upstream_model, targets

        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE).rstrip("/")
        targets = (
            [
                ProviderTarget(
                    provider=provider,
                    account="direct",
                    base_url=base_url,
                    api_key=api_key,
                )
            ]
            if api_key
            else []
        )
        return provider, upstream_model, targets

    def configured(self, model: str | None = None) -> bool:
        _, _, targets = self.targets_for(model or self.default_model)
        return any(not target.uds or self._worker_socket_exists(target.uds) for target in targets)

    @staticmethod
    def _worker_socket_exists(socket_path: str) -> bool:
        try:
            return stat.S_ISSOCK(os.stat(socket_path).st_mode)
        except (OSError, ValueError):
            return False

    def pricing(self, model: str | None = None) -> dict[str, float]:
        provider, _ = self._provider_model(model or self.default_model)
        if provider == "opencode-go":
            # Go subscription usage is not represented as a per-token price by
            # the gateway.  Operators may set these for internal accounting.
            return {
                "input": float(os.environ.get("OPENCODE_GO_INPUT_PRICE", "0")),
                "output": float(os.environ.get("OPENCODE_GO_OUTPUT_PRICE", "0")),
                "cache_hit": float(os.environ.get("OPENCODE_GO_CACHE_PRICE", "0")),
            }
        return dict(DEEPSEEK_PRICING)

    def summary(self) -> dict[str, Any]:
        """Safe operator metadata; never includes credentials."""
        models = sorted(self.allowed_models())
        worker_sockets = self._csv(os.environ.get("OPENCODE_GO_WORKER_SOCKETS", ""))
        result: dict[str, Any] = {
            "models": models,
            "default_model": self.default_model,
            "deepseek_configured": self.configured(self.deepseek_model),
            "opencode_go_configured": self.configured(f"opencode-go/{self.opencode_go_model}"),
            "opencode_go_worker_count": sum(
                self._worker_socket_exists(socket_path) for socket_path in worker_sockets
            ),
        }
        return result

    def public_summary(self) -> dict[str, Any]:
        """User-safe availability only, for unauthenticated surfaces.

        Deliberately omits the model inventory and worker-pool counts that
        summary() carries: capacity details are operator information
        (plan Track G3 — report available/unavailable, not account or pool
        size). Public endpoints must call this, never summary().
        """
        return {
            "available": bool(
                self.configured(self.deepseek_model)
                or self.configured(f"opencode-go/{self.opencode_go_model}")
            ),
        }

    async def _client_for(self, target: ProviderTarget) -> httpx.AsyncClient:
        key = target.uds or target.base_url
        client = self._clients.get(key)
        if client is not None:
            return client
        if target.uds:
            transport = self._transport or httpx.AsyncHTTPTransport(uds=target.uds)
            client = httpx.AsyncClient(transport=transport, base_url=target.base_url, timeout=600.0)
        else:
            client = httpx.AsyncClient(transport=self._transport, timeout=600.0)
        self._clients[key] = client
        return client

    async def _ordered_targets(
        self, provider: str, targets: list[ProviderTarget]
    ) -> list[ProviderTarget]:
        now = time.monotonic()
        healthy = [
            target for target in targets if self._cooldown_until.get(target.identity, 0) <= now
        ]
        if not healthy:
            healthy = targets
        if not healthy:
            return []
        async with self._lock:
            start = self._next.get(provider, 0) % len(healthy)
            self._next[provider] = start + 1
        ordered = healthy[start:] + healthy[:start]
        if provider != "opencode-go":
            return ordered

        ready = []
        for target in ordered:
            if await self._worker_ready(target):
                ready.append(target)
            else:
                self._mark_retryable(target)
        return ready

    async def _worker_ready(self, target: ProviderTarget) -> bool:
        """Check worker liveness/readiness without exposing its credential."""
        if not target.uds:
            return True
        if not self._worker_socket_exists(target.uds):
            return False
        try:
            client = await self._client_for(target)
            response = await client.get("/health", timeout=WORKER_HEALTH_TIMEOUT)
            body = response.json()
        except (httpx.HTTPError, OSError, ValueError):
            return False
        return (
            response.status_code == 200
            and isinstance(body, dict)
            and body.get("ok") is True
            and body.get("ready", True) is True
        )

    def _mark_retryable(self, target: ProviderTarget) -> None:
        self._cooldown_until[target.identity] = time.monotonic() + float(
            os.environ.get("OPENCODE_GO_ACCOUNT_COOLDOWN", "15")
        )

    @staticmethod
    def _headers(target: ProviderTarget) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if target.api_key:
            headers["Authorization"] = f"Bearer {target.api_key}"
        return headers

    @staticmethod
    def _response_error(resp: httpx.Response) -> dict[str, Any]:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        error = body.get("error", body) if isinstance(body, dict) else body
        if isinstance(error, dict):
            message = error.get("message") or str(error)
        else:
            message = str(error or resp.reason_phrase)
        return {"error": {"code": resp.status_code, "message": message}}

    @staticmethod
    def _malformed_response_error() -> dict[str, Any]:
        return {
            "error": {
                "code": 502,
                "message": "Provider returned malformed JSON",
            }
        }

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform one non-streaming completion with safe retryable failover."""
        requested_model = str(payload.get("model") or self.default_model)
        valid, model = self.validate_model(requested_model)
        if not valid:
            return {"error": {"code": 400, "message": model}}
        provider, upstream_model, targets = self.targets_for(model)
        if not targets:
            return {"error": {"code": 503, "message": f"Provider is not configured: {provider}"}}

        request_payload = dict(payload)
        request_payload["model"] = upstream_model
        last_error: dict[str, Any] | None = None
        for target in await self._ordered_targets(provider, targets):
            try:
                client = await self._client_for(target)
                resp = await client.post(
                    (
                        f"{target.base_url.rstrip('/')}/chat/completions"
                        if not target.uds
                        else "/chat/completions"
                    ),
                    headers=self._headers(target),
                    json=request_payload,
                )
                if resp.status_code in RETRYABLE_STATUS:
                    self._mark_retryable(target)
                    last_error = self._response_error(resp)
                    continue
                if not 200 <= resp.status_code < 300:
                    return self._response_error(resp)
                try:
                    body = resp.json()
                except ValueError:
                    self._mark_retryable(target)
                    last_error = self._malformed_response_error()
                    continue
                if not isinstance(body, dict):
                    self._mark_retryable(target)
                    last_error = self._malformed_response_error()
                    continue
                return body
            except (httpx.HTTPError, OSError) as exc:
                self._mark_retryable(target)
                last_error = {"error": {"code": 503, "message": str(exc)}}
        return last_error or {"error": {"code": 503, "message": "No healthy provider account"}}

    @asynccontextmanager
    async def stream(self, payload: dict[str, Any]) -> AsyncIterator[httpx.Response]:
        """Open a stream, failing over only before any response bytes arrive."""
        requested_model = str(payload.get("model") or self.default_model)
        valid, model = self.validate_model(requested_model)
        if not valid:
            yield httpx.Response(400, json={"error": {"code": 400, "message": model}})
            return
        provider, upstream_model, targets = self.targets_for(model)
        if not targets:
            yield httpx.Response(
                503,
                json={
                    "error": {
                        "code": 503,
                        "message": f"Provider is not configured: {provider}",
                    }
                },
            )
            return

        request_payload = dict(payload)
        request_payload["model"] = upstream_model
        last_error = {"error": {"code": 503, "message": "No healthy provider account"}}
        for target in await self._ordered_targets(provider, targets):
            client = await self._client_for(target)
            manager = client.stream(
                "POST",
                (
                    f"{target.base_url.rstrip('/')}/chat/completions"
                    if not target.uds
                    else "/chat/completions"
                ),
                headers=self._headers(target),
                json=request_payload,
            )
            try:
                response = await manager.__aenter__()
            except (httpx.HTTPError, OSError) as exc:
                self._mark_retryable(target)
                last_error = {"error": {"code": 503, "message": str(exc)}}
                continue
            if response.status_code in RETRYABLE_STATUS:
                self._mark_retryable(target)
                await response.aread()
                await manager.__aexit__(None, None, None)
                last_error = self._response_error(response)
                continue
            try:
                # The caller already knows how to format upstream errors.
                yield response
            finally:
                await manager.__aexit__(None, None, None)
            return

        yield httpx.Response(last_error["error"]["code"], json=last_error)

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
