"""Parallel research workers for the chat pipeline (opencode-style fan-out).

A planner call (fast, non-thinking model) splits a research-shaped question
into ≤3 independent sub-tasks; each worker runs a focused mini tool-loop
concurrently (threaded DB tools, own scope gate); a synthesizer call on the
main model merges the worker reports into the final answer.

Wall-clock ≈ 3 sequential LLM calls instead of the sequential
think→tool→think→tool loop's up to 15. The middle stage is fully parallel.

The heavy lifting (DeepSeek calls, tool execution, event emission) is injected
via callables so this module stays decoupled from web.routes.chat and is
unit-testable with stubs.
"""

import asyncio
import json
import logging
import os
import re

logger = logging.getLogger("chat.subagents")

# Fast, non-thinking model for planning + worker data-gathering. The
# synthesizer stays on the user's chosen model (deepseek-v4-flash) for the
# deep answer.
PLAN_MODEL = os.environ.get("CHAT_PLAN_MODEL", "deepseek-chat")

MAX_WORKERS = 3
MAX_WORKER_ROUNDS = 3
WORKER_TIMEOUT = 180.0  # seconds — a hung worker must not stall the run

PLANNER_PROMPT = """You are a research planner for a scripture study engine.

Split the user's question into at most 3 INDEPENDENT research sub-tasks that
can run in parallel. Each task must be self-contained (no task depends on
another's output) and name the specific tools it needs, chosen ONLY from the
provided tool list.

Respond with raw JSON only, no commentary, no markdown fences:
{"tasks": [{"id": "t1", "goal": "One clear research goal, ~1-2 sentences", "tools": ["scripture_verse", "scripture_gematria"]}]}

Rules:
- 1 task is fine for simple questions; 2-3 for multi-part or comparative ones.
- goals must be concrete ("Find the gematria of the divine name in Genesis 1:1")
  not vague ("study Genesis").
- tools must be real names from the provided list; omit tools entirely if the
  task is pure text synthesis (rare).
"""

_KNOWN_TOOLS_RE = re.compile(r"scripture_[a-z_]+")

DEEP_PATTERN = re.compile(
    r"explain|compare|contrast|trace|analyze|walk through|break down|"
    r"describe in detail|comprehensive|thorough|deep|how do|why does|"
    r"difference between|relationship between",
    re.IGNORECASE,
)


def should_plan(messages):
    """Fan-out heuristic: only research-shaped questions trigger the planner.
    Simple lookups stay on the sequential loop (fewer LLM calls, lower cost)."""
    last_user = next((m.get("content", "") for m in reversed(messages or [])
                      if m.get("role") == "user"), "")
    text = last_user if isinstance(last_user, str) else ""
    if len(text) > 200:
        return True
    if text.count("?") > 2:
        return True
    return bool(DEEP_PATTERN.search(text))


def _user_text(messages):
    for m in reversed(messages or []):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return m["content"]
    return ""


def _parse_plan(text):
    """Extract + validate the planner's JSON research plan. Returns a list of
    task dicts or None (fall back to the sequential loop)."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.startswith("json"):
            t = t[4:].strip()
    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            data = json.loads(t[start:end + 1])
        except json.JSONDecodeError:
            return None
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list) or not tasks:
        return None
    cleaned = []
    for task in tasks[:MAX_WORKERS]:
        if not isinstance(task, dict):
            continue
        goal = str(task.get("goal") or "").strip()
        if not goal:
            continue
        tools = task.get("tools") if isinstance(task.get("tools"), list) else []
        cleaned.append({
            "id": str(task.get("id") or f"w{len(cleaned) + 1}"),
            "goal": goal,
            "tools": [str(t) for t in tools if isinstance(t, str)],
        })
    return cleaned or None


async def plan_research(call_llm, messages, tool_names, max_tokens=1024):
    """One planner LLM call → research plan (list of task dicts) or None.

    Never raises: any failure (bad JSON, upstream error) returns None and the
    caller falls back to the sequential tool loop.
    """
    system = (PLANNER_PROMPT +
              f"\nAvailable tools: {', '.join(tool_names) if tool_names else '(none)'}")
    payload = {
        "model": PLAN_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": _user_text(messages)},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    try:
        data = await call_llm(payload)
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        plan = _parse_plan(content)
        if plan:
            logger.info("planner produced %d task(s)", len(plan))
            return plan
        logger.warning("planner returned unparseable plan: %.200s", content)
    except Exception as e:  # noqa: BLE001 — planner is best-effort
        logger.warning("planner call failed: %s", e)
    return None


def _tool_slice(tools, task_tools):
    """Slice the full tool definitions to the task's named tools. Falls back
    to the full list when the planner named none or only unknown names."""
    if not task_tools:
        return tools
    by_name = {t["function"]["name"]: t for t in tools}
    sliced = [by_name[n] for n in task_tools if n in by_name]
    return sliced or tools


async def _run_tool_round(worker_id, messages, tool_defs, call_llm, run_tool, emit):
    """One tool-calling round for a worker. Returns (messages, tool_results,
    final_content, tool_calls_seen) — final_content set when no tool calls."""
    payload = {
        "model": PLAN_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
        "tools": tool_defs,
        "tool_choice": "auto",
    }
    data = await call_llm(payload)
    if "error" in data:
        return messages, [], "", {"error": str(data["error"])}
    msg = (data.get("choices") or [{}])[0].get("message", {})
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        return messages, [], msg.get("content") or "", {}

    messages.append(msg)
    results = []
    emit({"type": "tool_progress", "worker": worker_id, "tools": [
        {"name": tc["function"]["name"], "args": _safe_args(tc)} for tc in tool_calls]})
    for tc in tool_calls:
        result = await run_tool(tc)
        results.append({
            "id": tc["id"],
            "name": tc["function"]["name"],
            "result": result if len(json.dumps(result, default=str, ensure_ascii=False)) <= 3000
                     else {"_truncated": True, "preview": json.dumps(result, default=str, ensure_ascii=False)[:500]},
        })
        result_str = json.dumps(result, default=str, ensure_ascii=False)[:3000]
        messages.append({"role": "tool", "content": result_str, "tool_call_id": tc["id"]})
    return messages, results, "", {}


def _safe_args(tc):
    try:
        return json.loads(tc["function"]["arguments"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


async def run_worker(task, tools, scopes, call_llm, run_tool, emit, max_tokens=4096):
    """Run one research sub-task: focused mini tool-loop + final report.

    Returns a report dict: {task_id, content, tool_results, error?}. Never
    raises. Events (tool_progress tagged with the worker id) go through `emit`.
    """
    worker_id = task["id"]
    tool_defs = _tool_slice(tools, task["tools"])
    system = (
        "You are a focused scripture research worker. Task: {goal}\n"
        "Gather the specific data the task asks for using the available tools. "
        "Do not narrate your tool use. End with a concise report: the key verses "
        "(full book names like 'Genesis 1:1'), the specific data (gematria values, "
        "connection types, quoted text), and any caveats. Under 400 words."
    ).format(goal=task["goal"])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task["goal"]},
    ]
    tool_results = []
    for _round in range(MAX_WORKER_ROUNDS):
        messages, results, content, err = await _run_tool_round(
            worker_id, messages, tool_defs, call_llm, run_tool, emit)
        tool_results.extend(results)
        if err:
            return {"task_id": worker_id, "content": "", "error": err, "tool_results": tool_results}
        if content:
            return {"task_id": worker_id, "content": content, "tool_results": tool_results}
    return {"task_id": worker_id, "content": "", "error": "worker hit round limit",
            "tool_results": tool_results}


async def run_workers(tasks, tools, scopes, call_llm, run_tool, emit, max_tokens=4096):
    """Run tasks concurrently (semaphore-capped), isolating failures/timeouts.
    Returns a list of report dicts in task order."""
    sem = asyncio.Semaphore(MAX_WORKERS)

    async def _one(task):
        async with sem:
            try:
                return await asyncio.wait_for(
                    run_worker(task, tools, scopes, call_llm, run_tool, emit, max_tokens),
                    timeout=WORKER_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("worker %s timed out", task["id"])
                return {"task_id": task["id"], "content": "", "error": "timeout", "tool_results": []}
            except Exception as e:  # noqa: BLE001
                logger.warning("worker %s failed: %s", task["id"], e)
                return {"task_id": task["id"], "content": "", "error": str(e), "tool_results": []}

    return await asyncio.gather(*[_one(t) for t in tasks])


def build_synthesis_messages(messages, reports):
    """Append worker findings as context for the synthesizer call.

    Returns a new message list (original untouched). Failed workers are marked
    so the synthesizer doesn't invent content for them.
    """
    msgs = [dict(m) for m in messages]
    parts = []
    for r in reports:
        if r.get("error") and not r.get("content"):
            parts.append(f"[research worker {r['task_id']} failed: {r['error']}]")
        else:
            parts.append(f"### {r['task_id']}\n{r.get('content') or '(no findings)'}")
    msgs.append({"role": "user", "content":
        "I dispatched parallel research workers to gather data for your question. "
        "Their findings:\n\n" + "\n\n".join(parts) +
        "\n\nSynthesize a complete, thorough answer to the original question using "
        "these findings. Cite specific verses with full book names, include gematria "
        "values and connection details. Do not mention the workers, tools, or research "
        "process — present the findings directly."})
    return msgs
