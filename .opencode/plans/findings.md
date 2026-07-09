# Findings: Scripture Engine Upgrade

## Quality Baseline
- **sentrux quality signal**: 0.5805 (recorded before plan creation)
- **Files**: 443 | **Import edges**: 304 | **Lines**: 86,118

## Requirements (User Answers)
1. **Primary goal**: Wiki browsing in the React app + enhanced MCP tools for DeepSeek V4 Flash
2. **No Obsidian vault** for now — deferred for eventual user notes feature
3. **No local AI** — DeepSeek V4 Flash handles everything
4. **Wiki is a mode in the existing app** — not a separate Quartz/static site. A layout toggle on ChapterView.
5. **Timeline**: Multi-month architecture
6. **LLM Enhancement**: Enhanced MCP tools so DeepSeek can do everything in one call

## Verified Current State (from code, not stale docs)

| Metric | Stale Docs Say | Actual (from code) |
|--------|---------------|-------------------|
| Connection layers | 10 | **11** |
| Connection types | ~80 | **131** defined |
| MCP tools | 10 | **56** |
| HTTP endpoints | 12 | **52 in server.py + 17 in routes = 69 total** |
| Generators | 48 | **47** |
| CLI tools | 23 | **23** (correct) |
| Works | 5 (README) | **8** (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha) |
| Connection count | 218K (README) | CHAT_AGENTS.md says **1,356,391** — likely reflects live DB |

### 11 Layers Defined
1. linguistic — word-level language connections (same lemma, root, wordplay)
2. numerical — gematria values, divine name values
3. structural — chiasms, parallelisms, inclusios, refrains
4. intertextual — quotations, allusions, echoes, type-antitype
5. textual — manuscript variants, JST changes, DSS variants
6. geographic — locations, journeys, temple mount, exile routes
7. chronological — timelines, genealogies, feast cycles
8. interpretive — rabbinic midrash, patristic, Gileadi, LDS readings
9. frequency — word counts, hapax legomenon, 7-fold patterns
10. symbolic — shared symbols, apocalyptic imagery, typology
11. sod — hidden/temple meanings, ascent, merkabah, divine council

### 56 MCP Tools
- **Verse**: scripture_verse, scripture_passage_guide, scripture_verse_text, scripture_interlinear
- **Search**: scripture_search, scripture_search_xlingual
- **Gematria**: scripture_gematria
- **Strong's**: scripture_strongs
- **Connections**: scripture_connections, scripture_intertext, scripture_pardes
- **Sod**: scripture_sod
- **Graph**: scripture_graph_path, scripture_graph_reachable, scripture_graph_hubs, scripture_graph_entities, scripture_graph_shared_entities, scripture_graph_entity_network, scripture_graph_centrality, scripture_graph_stats
- **Info**: scripture_info
- **Sources**: scripture_sources, scripture_sources_by_scholar, scripture_sources_list
- **Consensus**: scripture_consensus, scripture_disagreements
- **Study**: scripture_study_create, scripture_study_get, scripture_study_list, scripture_study_suggest, scripture_study_add_step, scripture_study_remove_step, scripture_study_update, scripture_study_bulk_update, scripture_study_export_json, scripture_study_export_html, scripture_study_publish, scripture_study_get_published, scripture_study_list_published, scripture_study_fork, scripture_study_import_json
- **Assessment**: scripture_assess_start, scripture_assess_answer, scripture_assess_progress
- **Conversation**: conversation_create, conversation_add_message, conversation_list, conversation_get, conversation_delete, conversation_list_connections, conversation_promote_connection
- **Hebrew**: scripture_hebrew_lessons, scripture_hebrew_lesson, scripture_hebrew_quiz

### 69 HTTP Endpoints
- 52 in `web/server.py` (verse, search, gematria, sod, connections, graph, lexicon, wiki, etc.)
- 3 in `web/routes/assessment.py`
- 4 in `web/routes/audio.py`
- 2 in `web/routes/chat.py`
- 10 in `web/routes/conversations.py`
- 14 in `web/routes/hebrew.py`
- 16 in `web/routes/studies.py`

## Key Architecture Observations
1. **MCP server is thin** — auto-discovers from TOOL_REGISTRY, no higher-order patterns
2. **Graph traversal exists** via recursive CTEs on connections table
3. **No GraphRAG** — LLM retrieval uses basic context dumping
4. **No Markdown/structured export** for third-party tools
5. **Frontend graph viz** uses Cytoscape.js — good but WebGL would be better at scale
6. **Quality controls** in `lib/controls/` are a unique asset (p-values, Bonferroni, null-text)

## Pre-resolved Decisions
- **Wiki approach**: Layout toggle on existing ChapterView, not a separate tab/site
- **LLM enhancement path**: Keep MCP, add high-context tools (study_verse, research, compare, graph_context, entity_deep)
- **Graph layer**: Stay on SQLite with recursive CTEs — no Neo4j/Kuzu migration needed
- **AI**: DeepSeek V4 Flash only — no Ollama/local models
- **Frontend**: Add react-force-graph-2d alongside Cytoscape.js for large-graph perf
- **User notes**: Deferred, but leave architectural room (verse_annotations table already exists)
- **Obsidian vault**: Removed from scope; can revisit later
- **Public wiki**: Not a separate static site; wiki is the enhanced app mode

## Architecture Vision

```
                    ┌─────────────────────────────────┐
                    │   SQLite Database                │
                    │   42K+ verses · 1.3M+ conxs     │
                    │   11 layers · 131 types          │
                    └──────┬──────┬────────┬──────────┘
                           │      │        │
              ┌────────────┘      │        └──────────────┐
              ▼                   ▼                       ▼
    ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────┐
    │  MCP Tools      │  │  FastAPI     │  │  React Frontend     │
    │  Enhanced:      │  │  HTTP API    │  │  ChapterView        │
    │  study_verse,   │  │  (69 routes) │  │  ├ Simple mode       │
    │  compare,       │  │              │  │  └ Wiki mode (new)  │
    │  research,      │  └──────────────┘  │  Graph Viz (D3/WebGL)│
    │  graph_context, │                    └─────────────────────┘
    │  entity_deep    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  DeepSeek V4    │
    │  Flash (LLM)    │
    └─────────────────┘
```

## Open Questions → Resolved
- **Q: Wiki = separate site?** → A: No. It's a layout mode in the existing React ChapterView.
- **Q: Need Postgres/Neo4j/Kuzu?** → A: No. SQLite + recursive CTEs handle 1.3M connections fine.
- **Q: Need LangChain/LlamaIndex?** → A: No. Build enhanced MCP tools natively. Add LangGraph later if agent loops are needed.
- **Q: Obsidian vault?** → A: Removed from scope. User notes feature deferred but the `verse_annotations` table can support it later.
- **Q: Public wiki site?** → A: Not a separate site. The enhanced app IS the wiki.
- **Q: What connection count is right?** → A: CHAT_AGENTS.md says 1,356,391. The DB needs to be queried live for the exact number. Phase A1 will produce a stats script.
