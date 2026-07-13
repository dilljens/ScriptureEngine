# MCP Server — mcp_server.py

The MCP (Model Context Protocol) server exposes **60 scripture tools** to AI assistants via stdio JSON-RPC. Auto-discovers all registered tools from `lib/api/TOOL_REGISTRY`.

## Architecture

```
mcp_server.py
  │
  ├── Stdio JSON-RPC loop        ← opencode spawns as subprocess
  │     │
  │     ├── initialize            → Protocol handshake + capabilities
  │     ├── tools/list            → 60 tools from TOOL_REGISTRY
  │     ├── tools/call            → Execute tool, return content
  │     └── notifications/initialized → No-op
  │
  └── lib.api.call_tool()       ← Dispatches to registered function
        │
        └── get_db()            ← SQLite connection (per-call)
```

## Protocol Support

The server supports both MCP protocol versions:
- **Old** (2024-11-05): `list_tools`, `call_tool`
- **New** (2025-03-26+): `tools/list`, `tools/call`

Both dispatch to the same logic.

## Available Tools (60)

### Core Scripture
| Tool | Description |
|------|-------------|
| `scripture_verse` | Look up a verse with text, gematria, connections |
| `scripture_verse_text` | Get verse text in a specific Bible version |
| `scripture_passage_guide` | Pre-computed passage guide (RAM cached) |
| `scripture_versions` | List all available Bible text versions |
| `scripture_info` | Database statistics |
| `scripture_tools` | List all 60 available tools with schemas |

### Search & Gematria
| Tool | Description |
|------|-------------|
| `scripture_search` | Keyword search in English |
| `scripture_search_xlingual` | Cross-lingual (he/el/en) search |
| `scripture_gematria` | Compute gematria for a Hebrew word |
| `scripture_strongs` | Strong's definition lookup |
| `scripture_interlinear` | Word-by-word interlinear analysis |

### Connections & PaRDeS
| Tool | Description |
|------|-------------|
| `scripture_connections` | Get connections for a verse (filtered) |
| `scripture_compare` | Compare two verses — shortest path, shared entities, side-by-side text |
| `scripture_intertext` | Intertextual connections (quotations, allusions, echoes) |
| `scripture_pardes` | PaRDeS interpretation levels (P'shat, Remez, Drash, Sod) |
| `scripture_sod` | Hidden patterns (Atbash, acrostics, advanced gematria, hidden names) |
| `scripture_sources` | Source provenance breakdown for a verse |
| `scripture_sources_by_scholar` | All connections from a specific scholar |
| `scripture_sources_list` | List all scholars with connections in the graph |

### Graph Traversal
| Tool | Description |
|------|-------------|
| `scripture_graph_path` | Shortest path between two verses through typed graph |
| `scripture_graph_reachable` | All verses reachable within N hops |
| `scripture_graph_hubs` | Most-connected hub verses |
| `scripture_graph_entities` | Entities (people, places, concepts) linked to a verse |
| `scripture_graph_shared_entities` | Other verses sharing entities with this verse |
| `scripture_graph_entity_network` | All verses connected to a specific entity |
| `scripture_graph_centrality` | Most central verses by degree centrality |
| `scripture_graph_stats` | Connection graph statistics |
| `scripture_graph_context` | N-hop neighborhood as structured text for LLM reasoning |

### Research & Entity
| Tool | Description |
|------|-------------|
| `scripture_research` | Multi-hop thematic research — walk graph, collect texts, return brief |
| `scripture_entity_deep` | Deep dive on a biblical entity — all verses + connections + co-occurrence |
| `scripture_consensus` | Ecumenical consensus data — which traditions engage |
| `scripture_disagreements` | Interpretive disagreements — contradictory readings across traditions |

### Study Guides (15+ tools)
| Tool | Description |
|------|-------------|
| `scripture_study_create` | Create a new AI-guided study guide |
| `scripture_study_get` | Get a study guide with enriched steps |
| `scripture_study_list` | List study guides, filtered by theme |
| `scripture_study_update` | Update study guide metadata |
| `scripture_study_add_step` | Add a step to a study |
| `scripture_study_remove_step` | Remove a step and re-number |
| `scripture_study_suggest` | Suggest an exploration path from a seed verse |
| `scripture_study_export_json` | Export as JSON with full graph paths |
| `scripture_study_export_html` | Export as self-contained HTML page |
| `scripture_study_publish` | Publish as immutable snapshot with shareable URL |
| `scripture_study_get_published` | Get a published study by slug |
| `scripture_study_list_published` | List all published studies |
| `scripture_study_fork` | Fork a published study into editable copy |
| `scripture_study_import_json` | Import from JSON string |
| `scripture_study_bulk_update` | Replace all steps of a study |
| `scripture_study_verse` | Complete verse study package (verse + connections + gematria + entities + sources + reachable) |

### Hebrew Learning
| Tool | Description |
|------|-------------|
| `scripture_hebrew_lessons` | List available Hebrew lesson nodes (102 across 7 categories) |
| `scripture_hebrew_lesson` | Get full lesson content for a Hebrew concept node |
| `scripture_hebrew_quiz` | Generate Hebrew knowledge quiz questions |

### Conversation
| Tool | Description |
|------|-------------|
| `scripture_conversation_create` | Create a new conversation session |
| `scripture_conversation_get` | Get session with messages, refs, connections |
| `scripture_conversation_list` | List sessions, paginated |
| `scripture_conversation_add_message` | Add message (auto-extracts verse refs) |
| `scripture_conversation_list_connections` | List connections discovered/retrieved in session |
| `scripture_conversation_promote_connection` | Promote discovered connection to main graph |
| `scripture_conversation_delete` | Delete session and all cascade data |

### Assessment
| Tool | Description |
|------|-------------|
| `scripture_assess_start` | Start adaptive assessment session |
| `scripture_assess_answer` | Submit answer and get next question |
| `scripture_assess_progress` | Get current assessment progress |

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

## All Tools Also Available via HTTP

Every MCP tool is also an HTTP endpoint:
```
GET  /api/v1/tools/scripture_graph_path?start=gen.1.1&end=john.1.1
POST /api/v1/tools/scripture_graph_path  {"start": "gen.1.1", "end": "john.1.1"}
```

List all 60 at `GET /api/v1/tools` with their JSON schemas.

## Path Scope

- `mcp_server.py` — the server (123 lines)
- `lib/api/__init__.py` — tool registry (tools added here appear automatically)
- `lib/api/*.py` — individual tool implementations (60 total)
