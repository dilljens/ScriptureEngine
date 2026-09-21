#!/usr/bin/env python3
"""Controlled 429/load drill for the OpenCode Go provider pool.

Automates the manual live load/429 drill from docs/runbooks/opencode-go-pool.md
(a tracked known gap: automated coverage uses mock transports only).

What it does: fires controlled concurrent chat-completion load, observes 429s,
and verifies the ProviderRouter guardrails from web/lib/llm_provider.py —
RETRYABLE_STATUS failover and per-account cooldowns
(OPENCODE_GO_ACCOUNT_COOLDOWN, default 15s). Prints a JSON summary to stdout.

Modes:
  --dry-run (DEFAULT): simulates timings with local fake responses via
      httpx.MockTransport (same pattern as tests/test_llm_provider.py).
      No network, no cost. Always exits 0 if the simulation completes.
  --live: sends real chat completions through ProviderRouter using the same
      env/keys as the provider module. Requires --i-understand-costs or it
      refuses without touching the network. Never logs keys. Exits nonzero
      if 429s occurred but no cooldown was triggered (guardrail failed).

Usage:
    python3 scripts/provider_429_drill.py --dry-run --duration-s 5
    python3 scripts/provider_429_drill.py --live --i-understand-costs \
        --rpm 60 --duration-s 30 --model opencode-go/muse-spark-1.2-contributor
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from web.lib.llm_provider import RETRYABLE_STATUS, ProviderRouter

DEFAULT_WORKSPACES = "opencode-go-1,opencode-go-2,opencode-go-3,opencode-go-4"
# Dry-run fake: every Nth upstream response is a 429 so cooldowns get exercised.
# Dry-run fake: every Nth upstream response is a 429 so cooldowns get exercised.
# Latency is simulated with asyncio.sleep inside the in-flight window (no
# network); raise --rpm to see max_concurrency_seen climb per Little's law.
DRY_RUN_429_EVERY_NTH = 3
DRY_RUN_LATENCY_S = 0.2
MAX_CONCURRENCY = 32


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Controlled 429 drill for the OpenCode Go provider pool."
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Simulate with local fake responses (default; no network, no cost).",
    )
    parser.add_argument(
        "--live",
        dest="live",
        action="store_true",
        help="Send real chat completions (requires --i-understand-costs).",
    )
    parser.add_argument(
        "--i-understand-costs",
        action="store_true",
        help="Explicit cost acknowledgement; required for --live.",
    )
    parser.add_argument(
        "--rpm",
        type=float,
        default=60.0,
        help="Target request rate per minute (default: 60).",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=30.0,
        help="How long to sustain load, in seconds (default: 30).",
    )
    parser.add_argument(
        "--workspaces",
        default=DEFAULT_WORKSPACES,
        help="CSV workspace labels for per_workspace accounting "
        f"(default: {DEFAULT_WORKSPACES}). In --live these label the load; "
        "routing still goes through ProviderRouter.",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Chat model id (default: router default from env).",
    )
    return parser.parse_args(argv)


def _workspace_labels(raw: str) -> list[str]:
    labels = [part.strip() for part in (raw or "").split(",") if part.strip()]
    return labels or ["default"]


def _result_code(result: dict) -> int | None:
    error = result.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        return code if isinstance(code, int) else None
    return None


async def _run_load(
    router: ProviderRouter,
    make_payload: "callable[[str], dict]",
    labels: list[str],
    total: int,
    interval_s: float,
    latency_s: float = 0.0,
) -> dict:
    """Fire `total` completions paced at `interval_s`, tracking concurrency."""
    stats = {
        "sent": 0,
        "ok": 0,
        "got_429": 0,
        "max_concurrency_seen": 0,
        "per_workspace": {label: {"sent": 0, "ok": 0, "got_429": 0} for label in labels},
    }
    in_flight = 0
    semaphore = asyncio.Semaphore(min(MAX_CONCURRENCY, max(1, total)))
    lock = asyncio.Lock()

    async def one(index: int) -> None:
        nonlocal in_flight
        label = labels[index % len(labels)]
        async with semaphore:
            async with lock:
                in_flight += 1
                stats["max_concurrency_seen"] = max(
                    stats["max_concurrency_seen"], in_flight
                )
            try:
                if latency_s > 0:
                    # Simulated upstream latency inside the in-flight window so
                    # concurrent tasks genuinely overlap (asyncio.sleep keeps
                    # the event loop free, unlike the blocking sleep a sync
                    # MockTransport handler would need).
                    await asyncio.sleep(latency_s)
                result = await router.complete(make_payload(label))
            except Exception as exc:  # never let one failure abort the drill
                result = {"error": {"code": 503, "message": f"drill harness: {exc}"}}
            async with lock:
                in_flight -= 1
                stats["sent"] += 1
                ws = stats["per_workspace"][label]
                ws["sent"] += 1
                if "error" not in result:
                    stats["ok"] += 1
                    ws["ok"] += 1
                elif _result_code(result) == 429:
                    stats["got_429"] += 1
                    ws["got_429"] += 1

    tasks = []
    for index in range(total):
        tasks.append(asyncio.create_task(one(index)))
        if interval_s > 0 and index < total - 1:
            await asyncio.sleep(interval_s)
    await asyncio.gather(*tasks)
    return stats


def _counting_cooldown(router: ProviderRouter) -> dict[str, int]:
    """Wrap router._mark_retryable to count cooldown triggers (no behavior change)."""
    counter = {"cooldown_triggered": 0}
    original = router._mark_retryable

    def wrapped(target) -> None:
        counter["cooldown_triggered"] += 1
        return original(target)

    router._mark_retryable = wrapped  # type: ignore[method-assign]
    return counter


def run_dry_run(
    model: str, labels: list[str], rpm: float, duration_s: float
) -> dict:
    os.environ.setdefault("OPENCODE_API_KEY", "dry-run-not-a-key")
    issued = {"n": 0, "retryable": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        issued["n"] += 1
        if issued["n"] % DRY_RUN_429_EVERY_NTH == 0:
            issued["retryable"] += 1
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-drill",
                "model": "drill",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "drill-ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    async def main() -> dict:
        router = ProviderRouter(httpx.MockTransport(handler))
        cooldowns = _counting_cooldown(router)
        try:
            # Default to the Go pool: this drill exists for the
            # docs/runbooks/opencode-go-pool.md 429 procedure.
            resolved = model or f"opencode-go/{router.opencode_go_model}"
            total = max(1, int(round(rpm * duration_s / 60.0)))
            interval_s = 60.0 / rpm if rpm > 0 else 0.0

            def make_payload(_label: str) -> dict:
                return {
                    "model": resolved,
                    "messages": [{"role": "user", "content": "429 drill ping"}],
                }

            stats = await _run_load(
                router, make_payload, labels, total, interval_s,
                latency_s=DRY_RUN_LATENCY_S,
            )
            stats["retried"] = issued["retryable"]
            stats["cooldown_triggered"] = cooldowns["cooldown_triggered"]
            stats["mode"] = "dry-run"
            stats["model"] = resolved
            return stats
        finally:
            await router.aclose()

    return asyncio.run(main())


def run_live(
    model: str, labels: list[str], rpm: float, duration_s: float
) -> tuple[dict, int]:
    router = ProviderRouter()
    resolved = model or router.default_model
    valid, validated = router.validate_model(resolved)
    if not valid:
        summary = {
            "mode": "live",
            "model": resolved,
            "sent": 0,
            "ok": 0,
            "retried": 0,
            "got_429": 0,
            "cooldown_triggered": 0,
            "max_concurrency_seen": 0,
            "per_workspace": {},
            "error": validated,  # model id only; never credentials
        }
        return summary, 1
    if not router.configured(validated):
        summary = {
            "mode": "live",
            "model": validated,
            "sent": 0,
            "ok": 0,
            "retried": 0,
            "got_429": 0,
            "cooldown_triggered": 0,
            "max_concurrency_seen": 0,
            "per_workspace": {},
            "error": "provider not configured (no worker sockets or API key present)",
        }
        return summary, 1

    async def main() -> tuple[dict, int]:
        cooldowns = _counting_cooldown(router)
        try:
            total = max(1, int(round(rpm * duration_s / 60.0)))
            interval_s = 60.0 / rpm if rpm > 0 else 0.0

            def make_payload(_label: str) -> dict:
                return {
                    "model": validated,
                    "messages": [
                        {"role": "user", "content": "429 drill ping — reply ok"}
                    ],
                    "max_tokens": 8,
                    "temperature": 0,
                }

            stats = await _run_load(router, make_payload, labels, total, interval_s)
            # Live transport hides intermediate hops; retryable outcomes that
            # exhausted all targets surface as terminal 429s. Cooldown marks
            # are the direct guardrail signal.
            stats["retried"] = stats["got_429"]
            stats["cooldown_triggered"] = cooldowns["cooldown_triggered"]
            stats["mode"] = "live"
            stats["model"] = validated
            if 429 in RETRYABLE_STATUS and stats["got_429"] > 0 and stats["cooldown_triggered"] == 0:
                stats["error"] = (
                    "guardrail failure: 429s observed but no cooldown triggered"
                )
                return stats, 1
            return stats, 0
        finally:
            await router.aclose()

    return asyncio.run(main())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    labels = _workspace_labels(args.workspaces)

    if args.live:
        if not args.i_understand_costs:
            print(
                "refusing --live without --i-understand-costs "
                "(real API budget would be spent; no requests sent)",
                file=sys.stderr,
            )
            return 2
        summary, exit_code = run_live(args.model, labels, args.rpm, args.duration_s)
        print(json.dumps(summary, indent=2))
        return exit_code

    summary = run_dry_run(args.model, labels, args.rpm, args.duration_s)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
