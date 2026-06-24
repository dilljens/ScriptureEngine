#!/usr/bin/env python3
"""MCP Server for the Scripture Knowledge Engine.

Thin JSON-RPC router — all tool logic lives in lib/api/.
Auto-discovers all registered tools from the TOOL_REGISTRY.

Adding a new tool: implement it in lib/api/*.py + register in lib/api/__init__.py
→ It's immediately available here, no server code changes.

Protocol: JSON-RPC over stdio (standard MCP protocol)
"""

import sys, json, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.api import TOOL_REGISTRY, list_tools, call_tool
from lib.db import get_db


def handle_request(request):
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    # ── MCP Protocol Methods ──
    # Support both old (list_tools/call_tool) and new (tools/list/tools/call) MCP protocol names.

    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": req_id if req_id is not None else 0,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "scriptureengine",
                    "version": "1.0.2",
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                    "prompts": {},
                    "resources": {},
                },
            },
        }
        return resp

    # Both old and new method names dispatch to the same logic
    is_list_tools = method in ("list_tools", "tools/list")
    is_call_tool = method in ("call_tool", "tools/call")

    if is_list_tools:
        tools = list_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if is_call_tool:
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            conn = get_db()
            result = call_tool(tool_name, conn, **args)
            conn.close()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                result,
                                indent=2,
                                ensure_ascii=False,
                                default=str,
                            ),
                        }
                    ]
                },
            }
        except Exception as e:
            import traceback

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e), "data": traceback.format_exc()},
            }

    if method in ("notifications/initialized", "notifications/initialized"):
        return None

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


# ─── Stdio JSON-RPC Loop ───

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
