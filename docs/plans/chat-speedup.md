---
status: active
kind: plan
area: chat/api
author: plan-agent
created: 2026-08-08
---

# Project: Chat Speedup (Parallel Tools + Subagent Fan-Out)

Goal: Cut chat wall-clock latency on research questions. Fix the fake-parallel tool loop (real threading + streamed thinking during tool rounds + tool-result cache), then replace the sequential "think→tool→think→tool" loop with an opencode-style planner → parallel workers → synthesizer pipeline. ~3 sequential LLM calls instead of up to 15, middle stage fully parallel.

## Requirements
- [ ] R1: Multi-tool rounds execute in real parallel (threads), not serial gather.
- [ ] R2: Tool-round reasoning streams as `thinking` events (no more silent heartbeat-only waits).
- [ ] R3: Repeat deterministic lookups skip execution (tool-result cache).
- [ ] R4: Tool-enabled requests run planner → parallel workers → synthesizer; wall-clock ≈ 3 LLM calls.
- [ ] R5: Worker failures don't kill the run; synthesizer uses whatever succeeded.
- [ ] R6: Legacy paths (`/api/v1/chat`, subagents=false) unchanged; jobs path gets the same pipeline.
- [ ] R7: All existing chat tests pass; `sentrux check .` shows no new violations (baseline 3 pre-existing).

## Pre-resolved Decisions
- Swarm = in-process asyncio worker tasks; dev-side axe-swarm NOT wired into product runtime (used only to parallelize this plan's execution). See findings.md.
- Subagent flow: planner (1 fast-model call) → N≤3 parallel workers (focused prompts, tool slices, `asyncio.to_thread` tools) → synthesizer (1 streamed v4-flash call).
- Model tiering: `CHAT_PLAN_MODEL` (fast, env-config) for planner + worker planning; v4-flash for synthesis.
- Tools run via `asyncio.to_thread` with per-call `get_db()` connections; staging (write) tools stay serialized.
- Tool rounds use `stream: true` + SSE delta parsing (reasoning streams, tool_calls from final delta).
- Tool cache: in-memory dict + TTL, whitelist of deterministic read-only tools, key = sha256(name+args).
- UX minimal: workers reuse `tool_progress`; optional `plan` event (frontend may ignore).
- Opt-in via `body.subagents` (default true for tool-enabled); parse-failure falls back to legacy loop.
- No new dependencies.

## Track A: Server quick wins `[ ]`
- Description: Real parallel tool execution, streamed thinking during tool rounds, tool-result cache. Independent of the subagent restructure.
- 📏 Scope: ~3 files, ~390 lines

### Phase A1: Real parallel tool execution `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [ ] Replace `run_ro` in `_chat_pipeline` (chat.py:1536-1549): run sync `call_tool` via `asyncio.to_thread` with a fresh `get_db()` connection per call (sqlite3 conns aren't thread-safe); close per call.
- [ ] Keep staging (write) tools serialized — they already run in a separate loop (chat.py:1551-1568); ensure they use their own conn and a small in-process lock (SQLite single-writer) to avoid `database is locked`.
- [ ] Preserve result truncation + budget check behavior (chat.py:1570-1595) unchanged.
- [ ] Add `tests/chat_speedup_test.py`: stub tools with `asyncio.sleep`; assert N-tool round wall-clock ≈ 1× (not N×); assert staging still writes.
- 📏 Scope: `web/routes/chat.py` (~60 lines changed), `tests/chat_speedup_test.py` (new ~80). ~2 files, ~140 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_speedup_test.py tests/chat_reliability_test.py tests/chat_background_jobs_test.py -q`
- ⚙ Fallback: If SQLite locking bites under threads, give staging tools a dedicated writer conn + `BEGIN IMMEDIATE`; readers unaffected. If `to_thread` causes event-loop starvation on huge results, keep gather for ≤2 tools and thread only >2.
- Depends on: nothing

### Phase A2: Stream tool rounds + tool-result cache `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] Switch tool-round payloads to `stream: true` (chat.py:1496 `_build_payload`); parse SSE deltas with `_heartbeat_lines`; yield `thinking` events for `reasoning_content` chunks and accumulate content/reasoning/tool_calls from the final delta (mirror the final-stream parse at chat.py:1632-1668). Keep `stream_options: {"include_usage": true}`.
- [ ] New `lib/chat_cache.py`: in-memory `dict[str, (value, expires_at)]` + TTL (24h) + size cap; whitelist of deterministic read-only tools (verse, verse_text, gematria, strongs, interlinear, sources, sources_by_scholar, versions, info, graph_stats); key = sha256(name + json args). Wire into `run_ro` (check before execute, store after, skip storing errors).
- [ ] Tests: cached tool returns without executing (spy on registry); streamed tool round yields `thinking` events then correct `tool_calls`.
- 📏 Scope: `web/routes/chat.py` (+70), `lib/chat_cache.py` (new ~70), `tests/chat_speedup_test.py` (+100). ~3 files, ~240 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_speedup_test.py -q` + manual `curl` SSE smoke: multi-tool question shows `thinking` events between `tool_progress` bursts.
- ⚙ Fallback: If DeepSeek doesn't deliver `tool_calls` reliably in stream mode, keep non-stream tool rounds but fetch the reasoning via a second `stream:true` probe — simpler: revert to non-stream rounds and keep only the cache win (latency still improves via A1).
- Depends on: A1

## Track B: Subagent fan-out pipeline `[ ]`
- Description: Replace the sequential tool loop with planner → parallel workers → synthesizer. Builds on A1's threaded tool helper.
- 📏 Scope: ~4 files, ~720 lines

### Phase B1: Planner stage `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] `ChatRequest.subagents: bool = True` (chat.py:1104); default true when `tools_enabled`.
- [ ] Planner call: fast model (`CHAT_PLAN_MODEL`, env, default `deepseek-chat`), `stream: true`, focused system instruction (findings: planner prompt) → parse JSON research plan: `{tasks: [{id, goal, tools: [...]}]}`, cap 3 tasks, validate tool names against TOOL_DEFINITIONS.
- [ ] Yield one `plan` event `{tasks: [...]}`; on parse failure or invalid plan → retry once, then fall back to legacy loop (flag `subagents=False` for this request).
- [ ] Tests: planner prompt → valid JSON; invalid JSON → retry → fallback; >3 tasks → capped.
- 📏 Scope: `web/routes/chat.py` (+90), `web/lib/subagents.py` (planner half, new ~90), `tests/chat_speedup_test.py` (+60). ~3 files, ~240 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_speedup_test.py -q -k planner`
- ⚙ Fallback: If the fast model refuses tool names, planner output can be tool-free (workers get the full tools list); the plan still splits work.
- Depends on: A1

### Phase B2: Worker pool `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 20
- [ ] `web/lib/subagents.py` worker half: `async def run_worker(task, tools_slice, sem) -> report` — focused system prompt (task.goal), mini tool-loop (≤3 rounds) reusing A1/A2 helpers (to_thread tools, streamed thinking, cache), each event tagged `{"worker": task.id}`; returns `{task_id, content, reasoning, tool_results}`.
- [ ] Pool: `asyncio.Semaphore(3)`, spawn via `asyncio.gather` from `_chat_pipeline`; per-worker timeout (~180s) → cancel, mark failed; worker failure emits `error`-ish event with worker tag, others continue.
- [ ] Stream worker reasoning/tool chips as they arrive (thinking + tool_progress with worker tag).
- [ ] Tests: two slow workers complete in ~max not ~sum; one failing worker doesn't abort others; timeout path.
- 📏 Scope: `web/lib/subagents.py` (+170), `web/routes/chat.py` (+70), `tests/chat_speedup_test.py` (+100). ~3 files, ~340 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_speedup_test.py -q -k workers` (wall-clock assertion in the test)
- ⚙ Fallback: If workers fight over the shared httpx client, give each worker its own `httpx.AsyncClient`; if the DB locks under concurrent readers, WAL is already on (verify `PRAGMA journal_mode`).
- Depends on: B1

### Phase B3: Synthesizer + pipeline wiring `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] When `body.subagents` and planner produced tasks: skip the sequential loop; inject worker reports as tool-style context; run the existing final-stream path (chat.py:1597-1687) with v4-flash — truncation retry + forced-summary guard reused.
- [ ] Zero-worker-success case → fall back to legacy loop. Merge worker usage/cost into `done` event.
- [ ] Verify jobs path (`web/lib/jobs.py` `_chat_pipeline` consumer) gets identical behavior; no changes beyond event tagging.
- [ ] Integration test: full planner→workers→synthesize with stubbed DeepSeek (plan JSON, worker deltas, final stream), assert `done` has merged usage + all worker tool_results.
- 📏 Scope: `web/routes/chat.py` (+80), `web/lib/jobs.py` (+20), `tests/chat_speedup_test.py` (+80). ~3 files, ~180 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_speedup_test.py tests/chat_reliability_test.py tests/chat_background_jobs_test.py -q` + manual SSE smoke with `subagents` on.
- ⚙ Fallback: If synthesis quality drops vs. sequential loop (missing cross-tool reasoning), add the forced-summary prompt (already exists, chat.py:1692-1719) or pass workers' raw tool_results (not summaries) into the synthesizer.
- Depends on: B2

## Track C: Frontend minimal UX `[ ]`
- Description: Reuse existing tool chips for worker activity; no new panels.
- 📏 Scope: ~2 files, ~40 lines

### Phase C1: Render worker tool bursts + optional plan hint `[ ]`
- 🏷 Priority: low
- 🔁 Max turns: 8
- [ ] Confirm `tool_progress` renders worker bursts without change (api.js:398, ChatPanel.jsx:1032 already handle it); if chips feel noisy, prefix tool label with worker id (`w1·scripture_verse`).
- [ ] Optional: show a small "researching (N parallel)" chip when a `plan` event arrives (ignored gracefully if handler unchanged).
- 📏 Scope: `frontend/src/components/ChatPanel.jsx` (+30), `frontend/src/api.js` (+10). ~2 files, ~40 lines.
- ✅ Checkpoint: `npm run build` (frontend) + manual chat question with multiple lookups — chips appear as a burst, answer streams.
- ⚙ Fallback: Ship Track C with zero frontend changes if tool_progress rendering already satisfies (verify first; this phase may become a no-op + docs note).
- Depends on: B1 (plan event)

## Acceptance Criteria (all tracks)
- Research-style question: first token ≈ 1 plan call + first worker round (minutes→~1/3); full answer ≈ 3 sequential LLM calls.
- `python3 -m pytest tests/chat_speedup_test.py tests/chat_reliability_test.py tests/chat_background_jobs_test.py -q` green.
- `sentrux check .` → still 3 violations (App.jsx god-file fan-out=41 pre-existing), no new ones.
- Legacy `/api/v1/chat` + `subagents=false` behavior identical.
