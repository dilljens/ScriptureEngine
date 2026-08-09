# Findings: Chat Speedup (Parallel Tools + Subagent Fan-Out)

## Requirements (from discovery)

| # | Question | Answer |
|---|----------|--------|
| 1 | Goal | Cut chat wall-clock latency: parallel tool execution + opencode-style subagent fan-out (planner → parallel workers → synthesizer) |
| 2 | Workstreams | A: server quick wins (independent) · B: subagent pipeline (builds on A1 helper) · C: minimal frontend UX |
| 3 | Pre-resolved decisions | See below (swarm, model tiering, caching, UX) |
| 4 | Constraints | No new runtime deps; must work with `uvicorn --workers 2`; reuse existing job system (`web/lib/jobs.py`) + SSE event shapes; keep legacy endpoints working |
| 5 | Acceptance | Research questions respond in ~3 sequential LLM calls instead of up to 15; multi-tool rounds run in parallel; all existing chat tests pass; `sentrux check .` shows no new violations (baseline 3 pre-existing) |
| 6 | Anti-scope | Do NOT wire dev-side axe-swarm into the product runtime; do NOT add an external agent framework; do NOT change the client-message-save contract |

## Latency diagnosis (source of truth: `web/routes/chat.py`)

1. **Sequential LLM round-trips dominate** — `_chat_pipeline` (chat.py:1483) loops `call_deepseek` (non-streaming thinking calls, 1–8 min each) → tools → repeat, up to `max_tool_rounds = 15` (chat.py:1497; comment: "10 was too low for multi-work searches"). Wall clock ≈ Σ(LLM call times). This is where minutes go.
2. **Tool execution is nominally parallel, actually serial** — chat.py:1536-1549: `asyncio.gather` over `async def run_ro` wraps **synchronous** `call_tool` (`lib/api/__init__.py:1420`, SQLite, no awaits). Gather over sync functions with no await points runs them one-after-another on the event loop and blocks it. A 4-tool round takes 4× a single tool.
3. **Silent thinking** — tool rounds use `stream=False` (chat.py:1496), so users see only heartbeats during reasoning. Perceived latency > wall clock.
4. **Big prompt per round** — 55 tool definitions (chat.py:67-926) + 16.5KB system prompt (`CHAT_AGENTS.md`) sent on every call.

## Pre-resolved Decisions

- **Swarm = in-process asyncio worker tasks** (NOT axe-swarm). Rationale: axe-swarm is this repo's dev-side orchestrator (spawns subprocess agents tied to plan DAGs, file scopes, authority bounds). Embedding it in a user-facing FastAPI request on scriptureengine.org would mean spawning a full subprocess agent per chat message (seconds of boot before first token) plus a daemon on the prod box. The product chat's swarm is concurrent asyncio tasks sharing the existing seq-numbered job buffer — same concurrency benefit, zero infra. axe-swarm IS used to parallelize execution of this plan itself (see progress.md).
- **Subagent architecture**: planner (1 call) → N parallel workers (each a focused mini tool-loop, capped at 3) → synthesizer (1 streamed call). ~3 sequential LLM calls instead of up to 15.
- **Model tiering**: planner + worker planning rounds use a fast non-thinking model (`deepseek-chat`, env-configurable `CHAT_PLAN_MODEL`); synthesizer keeps `deepseek-v4-flash`. Thinking models are the slow part; planning needs speed, not depth.
- **Real tool parallelism**: run sync DB tools via `asyncio.to_thread` with per-thread SQLite connections (`get_db()` opens a fresh conn per call — thread-safe pattern). Staging (write) tools stay serialized (SQLite single-writer).
- **Stream tool rounds**: switch tool-call requests to `stream: true` + parse SSE deltas so reasoning streams as `thinking` events during the "waiting" phase; accumulate `tool_calls` from the final delta (DeepSeek supports tool calls in stream mode).
- **Tool-result cache**: in-memory dict + TTL for deterministic read-only tools (whitelist: verse, verse_text, gematria, strongs, interlinear, sources, sources_by_scholar, versions, info, graph_stats) keyed by sha256(name+json-args). Per-worker (uvicorn --workers 2 → acceptable; SQLite cache table noted as future option). No caching of connection-heavy or mutable tools.
- **UX: minimal** — workers reuse the existing `tool_progress` event shape; frontend renders worker calls as a burst of tool chips (existing path in api.js:398, ChatPanel.jsx:1032). No new panels.
- **Opt-in**: `body.subagents: bool = True` (default on for tool-enabled requests); legacy sequential path stays for disabled/subagent=false.
- **Error handling**: worker failure → emit error event tagged with worker id, continue other workers, synthesize with what succeeded. Per-worker timeout (~180s). Planner parse failure → fall back to legacy sequential loop.
- **Testing**: `tests/chat_speedup_test.py` with stubbed DeepSeek; existing `chat_reliability_test.py` + `chat_background_jobs_test.py` must keep passing.

## Architecture Notes

- New module `web/lib/subagents.py` — worker task factory, planner prompt/parser, report merge. Keeps `chat.py` at the orchestration layer.
- Worker events ride the existing pipeline: `_chat_pipeline` yields plain dicts; SSE wrapper (`_sse_event`) and job buffer (`web/lib/jobs.py`) forward them unchanged. New fields only: optional `worker` tag on `thinking`/`tool_progress`/`text`, plus one `plan` event (research plan) that the frontend may ignore.
- Synthesizer input = worker reports injected as tool-style context; reuses the final-stream code path (chat.py:1597-1687) incl. truncation retry + forced-summary guard.
- Job mode (`POST /api/v1/chat/jobs`) gets the same pipeline for free since it shares `_chat_pipeline`.

## Open Questions → Resolved

- Q: Do workers each pay a full system-prompt + tool-list cost? → A: Workers get a *focused* prompt (sub-task goal) and a *sub-slice* of tools relevant to their task (planner names the tools; slice from TOOL_DEFINITIONS). Cheaper + faster per worker, and the plan call tells us the slice.
- Q: Can the LLM be trusted to emit a valid JSON research plan? → A: Yes with a strict schema + retry-once on parse failure; fallback to legacy loop keeps worst case = today's behavior.
- Q: Token cost increase? → A: N workers × 1–2 short calls. At v4-flash pricing (0.14/0.28 per M) ≈ pennies per answer; planning model even cheaper. Accepted.
