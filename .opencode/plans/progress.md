# Progress: Scripture Engine Upgrade

## Session 2026-07-09 — Execution

### Completed
- [x] **Track A: Document Audit** — All 4 phases done
  - A1: scripts/project_stats.py created — verifiable source of truth for all stats
  - A2: README.md rewritten with accurate numbers (1,028,083 connections, 11 layers, 56→61 tools, 102 endpoints, 8 works)
  - A3: CHAT_AGENTS.md updated — all 61 tools listed with descriptions, stale staging tools removed
  - A4: web/server.py docstring, knowledge/wiki/_index.md, knowledge/wiki/_standards.md all updated

- [x] **Track B: Wiki Browsing** — All 4 phases done
  - B1: WikiLayout.jsx — Wikipedia-style two-column component with connection sidebar, entity sidebar, layer badges, quality stars, breadcrumb
  - B2: Simple ↔ Wiki mode toggle in ChapterView toolbar, persists via localStorage
  - B3: Collapsible inline graph panel showing chapter-level connections
  - B4: Browse-by-Layer tabbed view with connections grouped by type
  - Frontend builds successfully (vite 6.4.3)

- [x] **Track C: Enhanced MCP Tools** — All 6 phases done
  - C1: `scripture_study_verse` — complete verse package replaces 6+ tool calls
  - C2: `scripture_compare` — two-verse comparison with path, shared entities, overlap
  - C3: `scripture_research` — multi-hop thematic research walks the graph
  - C4: `scripture_graph_context` — N-hop neighborhood as structured LLM-readable text
  - C5: `scripture_entity_deep` — entity deep dive with verses, connections, related entities
  - C6: conversation_* → scripture_conversation_* rename (7 tools), CHAT_AGENTS.md updated
  - Tools count: 56 → **61**

### Deferred/Not Started
- [ ] Track E: Structured Data & Interop (JSON-LD, GraphQL) — lower priority

## Session 2026-07-15 — Hebrew Flashcards & Infrastructure

### Completed
- [x] **Hebrew seed system** — 0% generic, 4,592 practice items (from 428)
- [x] **Production practice** — 1,041 verb conjugation/root extraction/parsing items
- [x] **Graded reading** — 26 ETCBC-ordered chapters across 5 phases
- [x] **Audio** — 39/39 OT books, Shmuelof naming fixed, BOOK_MAP bug fixed
- [x] **Images** — word_images table + API, 424 words with FreeBibleImages (72%)
- [x] **Clickable Hebrew** — WordPopup with images, lessons render Hebrew words clickable
- [x] **Add to Learning** — POST /api/v1/hebrew/add-word, custom nodes for any word
- [x] **AnkiReview** — 3-mode flip cards (hearing/reverse/forward), FSRS-5, images on back
- [x] **audio_timestamps in schema** — lib/db.py now has CREATE TABLE
- [x] **Track D archived** — Wiki layout covers graph exploration needs

### New Ideas (planned)
- [ ] Tab sync / library loading error fix
- [ ] CLT techniques (vocalization prompts, TPR, chanting)
- [ ] Session persistence / context recovery

### Quality Signal
- Before: 0.5805
- After: 0.5834 (+29 points, improvement)
- Files: 443 (unchanged) | Lines: 86,817 (+699)
- One complexity increase (85 complex functions vs 84 before) — expected from new MCP tools

### Net Changes
- +1 new file: `frontend/src/components/WikiLayout.jsx`
- +1 new file: `scripts/project_stats.py`
- +699 lines of new code
- +5 new MCP tools (61 total)
- 3 documentation files rewritten
- 5 stale number references fixed across the codebase
