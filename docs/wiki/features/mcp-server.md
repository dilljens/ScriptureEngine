# MCP Server — mcp_server.py

The MCP (Model Context Protocol) server exposes 23 scripture tools to AI assistants via stdio JSON-RPC. Auto-discovers all registered tools from `lib/api/TOOL_REGISTRY`.

## Architecture

```
mcp_server.py
  │
  ├── Stdio JSON-RPC loop        ← opencode spawns as subprocess
  │     │
  │     ├── initialize            → Protocol handshake + capabilities
  │     ├── list_tools/tools/list → 23 tools from TOOL_REGISTRY
  │     ├── call_tool/tools/call  → Execute tool, return content
  │     └── notifications/initialized → No-op
  │
  └── lib.api.call_tool()        ← Dispatches to registered function
        │
        └── get_db()             ← SQLite connection (per-call)
```

## Protocol Support

The server supports both MCP protocol versions:
- **Old** (2024-11-05): `list_tools`, `call_tool`
- **New** (2025-03-26+): `tools/list`, `tools/call`

Both dispatch to the same logic.

## Available Tools (23)

| Tool | Description |
|------|-------------|
| `scripture_verse` | Look up a verse with text, gematria, connections |
| `scripture_passage_guide` | Pre-computed passage guide (RAM cached) |
| `scripture_search` | Keyword search in English |
| `scripture_search_xlingual` | Cross-lingual (he/el/en) search |
| `scripture_gematria` | Compute gematria for a Hebrew word |
| `scripture_connections` | Get connections for a verse |
| `scripture_intertext` | Intertextual connections (quotations, allusions) |
| `scripture_pardes` | PaRDeS interpretation levels |
| `scripture_sod` | Hidden patterns (Atbash, acrostics, gematria) |
| `scripture_graph_path` | Shortest path between two verses |
| `scripture_graph_reachable` | All verses reachable within N hops |
| `scripture_graph_hubs` | Most-connected hub verses |
| `scripture_graph_entities` | Entities linked to a verse |
| `scripture_graph_shared_entities` | Verses sharing entities |
| `scripture_graph_entity_network` | All verses for an entity |
| `scripture_graph_centrality` | Most central verses by degree |
| `scripture_graph_stats` | Connection graph statistics |
| `scripture_info` | Database statistics |
| `scripture_study_create` | Create an AI-guided study |
| `scripture_study_add_step` | Add a step to a study |
| `scripture_study_get` | Get a study guide with steps |
| `scripture_study_list` | List all study guides |
| `scripture_study_suggest` | Suggest an exploration path |

## Configuration

In `.opencode/opencode.jsonc`:
```json
"mcp": {
  "scripture-engine": {
    "type": "local",
    "command": ["python3", "mcp_server.py"],
    "enabled": true
  }
}
```

## Testing

```bash
# Test full handshake
printf '{"jsonrpc":"2.0","id":1,"method":"initialize"}\n{"jsonrpc":"2.0","id":2,"method":"list_tools"}\n' | python3 mcp_server.py

# Test a tool call
printf '{"jsonrpc":"2.0","id":0,"method":"initialize"}\n{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"scripture_info","arguments":{}}}\n' | python3 mcp_server.py
```

## Path Scope

- `mcp_server.py` — the server
- `lib/api/__init__.py` — tool registry (tools added here appear automatically)
- `lib/api/*.py` — individual tool implementations
