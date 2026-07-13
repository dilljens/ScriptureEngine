# Codebase Wiki — Scripture Knowledge Engine

## For AI Agents

When working on this codebase, start here:

1. **`_index.md`** — Architecture overview + quick reference + change impact map
2. **`_standards.md`** — Rules, practices, and patterns to follow
3. **`_glossary.md`** — Project-specific terminology
4. **`features/`** — Domain-specific documentation:
   - [`features/web-api.md`](features/web-api.md) — FastAPI server, RAM cache
   - [`features/lib-core.md`](features/lib-core.md) — Database, tool registry, controls
    - [`features/generators.md`](features/generators.md) — Connection discovery algorithms
    - [`features/mcp-server.md`](features/mcp-server.md) — MCP protocol, 23 tools
    - [`features/hebrew-audio.md`](features/hebrew-audio.md) — PassageReader, DailyVerse, AudioReview
    - [`features/literary-patterns.md`](features/literary-patterns.md) — Chiasm detection, Mukdam u'Meuchar
    - [`features/js-discourses-jst.md`](features/js-discourses-jst.md) — JS discourses + JST version
    - [`features/truth-seeking.md`](features/truth-seeking.md) — Truth framework, disagreements
 5. **`plans/`** — Architecture proposals and planning docs

### Decision Tree

```
I need to...
├── Look up a verse?
│   → _index.md quick reference + tools/verse.py
├── Understand the connection graph?
│   → _index.md (data flow) + features/generators.md
├── Add a new API endpoint?
│   → features/web-api.md + features/lib-core.md (tool registry pattern)
├── Add a new connection type?
│   → features/generators.md + _standards.md (generator pattern)
├── Fix a bug in the MCP server?
│   → features/mcp-server.md
└── Understand a project term?
    → _glossary.md
```

## For Humans

This wiki documents the codebase architecture, not the scripture data itself. For the data model (connections, verses, gematria), see:
- `lib/db.py` — full SQL schema
- `lib/connections/types.py` — all 10 layers and ~80 connection types
- `lib/api/__init__.py` — all 23 MCP/HTTP tools
