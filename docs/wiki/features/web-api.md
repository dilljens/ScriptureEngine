# Web API

The HTTP server at `web/server.py` serves the scripture knowledge graph via FastAPI.

## Architecture

```
web/server.py
  │
  ├── RAM Cache (startup)
  │   ├── GUIDE_CACHE    — passage_guides (41K verses)
  │   ├── VERSE_CACHE    — all verses (42K)
  │   ├── ENTITY_CACHE   — entity links (~87)
  │   └── LEXICON_CACHE  — lexicon entries (11.5K lemmas)
  │
  ├── GET  /api/v1/verses/{ref}              — Verse + connections [?context=N for surrounding verses]
  ├── GET  /api/v1/verses/{ref}/connections  — Filtered connections
  ├── GET  /api/v1/verses/{ref}/guide        — Passage guide (RAM cache)
  ├── GET  /api/v1/verses/{ref}/grammar      — Morphologically-tagged words
  ├── GET  /api/v1/verses/{ref}/annotations  — Verse comments
  ├── GET  /api/v1/chapter/{ref}             — Full chapter with parallelism + lines
  ├── GET  /api/v1/connections/chapter/{ref} — All non-structural connections for a chapter
  ├── GET  /api/v1/parallelism/isaiah/{ch}   — Isaiah chapter parallelism
  ├── GET  /api/v1/parallelism/isaiah/structure — Book-wide structure overview
  ├── GET  /api/v1/footnotes/{ref}           — LDS footnotes (verse or chapter)
  ├── GET  /api/v1/tsk-crossrefs/{ref}       — Treasury of Scripture Knowledge refs
  ├── GET  /api/v1/grammar/{ref}             — Chapter grammar + gematria
  ├── GET  /api/v1/search                    — Cross-lingual search
  ├── GET  /api/v1/semantic-search           — Vector similarity search
  ├── GET  /api/v1/gematria                  — Gematria lookup
  ├── GET  /api/v1/sod                       — Hidden patterns (Sod)
  ├── GET  /api/v1/pardes/{ref}              — PaRDeS levels
  ├── GET  /api/v1/lexicon/search            — Search lexicon (lemma/Hebrew/English)
  ├── GET  /api/v1/lexicon/lemma/{lemma}     — Full lexicon entry
  ├── GET  /api/v1/lexicon/root/{letters}    — Root family
  ├── GET  /api/v1/lexicon/domain/{name}     — Semantic domain members
  ├── GET  /api/v1/lexicon/domains           — List all domains
  ├── GET  /api/v1/lexicon/concordance/{lemma} — All verses for a lemma
  ├── GET  /api/v1/books                     — All books grouped by work (for navigation)
  ├── GET  /api/v1/genealogy/{person}        — Person entity connections
  ├── GET  /api/v1/ot-in-nt                  — OT quotations in NT
  ├── GET  /api/v1/studies/thematic          — Thematic study guides
  ├── GET  /api/v1/tabs                      — UI tab state (CRUD)
  ├── GET  /api/v1/tools                     — List all tools
  ├── GET/POST /api/v1/tools/{name}          — Call any tool
  ├── GET  /api/v1/info                      — Database stats
  ├── GET  /api/v1/health                    — Health check
  ├── POST /api/v1/connections/feedback      — Rate a connection (confirm/reject/unclear)
  ├── GET  /api/v1/agent/actions             — LLM agent testing queue
  ├── POST /api/v1/agent/state               — Frontend reports state for agent
```

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `load_ram_cache()` | `server.py:55` | Load guides/verses/entities/lexicon at startup |
| `get_verse()` | `server.py:137` | Main verse lookup — RAM or SQLite fallback; `?context=N` returns N surrounding verses |
| `search()` | `server.py:240` | Cross-lingual search (en/he/el) |
| `semantic_search()` | `server.py:358` | sqlite-vec character n-gram hash similarity |
| `get_grammar()` | `server.py:548` | Morphologically-tagged word-by-word breakdown |
| `genealogy()` | `server.py:601` | Person entity genealogical connections |
| `ot_in_nt()` | `server.py:654` | Aggregated OT→NT quotation catalog |
| `lexicon_search()` | `server.py:460` | Search lemma dictionary (Hebrew/English/Strong's) |

## RAM Cache

On startup, everything loads into memory:
- 42K verses → `VERSE_CACHE` dict
- 41K passage guides → `GUIDE_CACHE` dict  
- ~87 entity links → `ENTITY_CACHE` list
- 11.5K lexicon entries → `LEXICON_CACHE` dict (with `LEXICON_CACHE_BY_HEBREW` index)
- Total: ~500MB RAM, sub-ms lookups

In multi-worker mode (`SCRIPTURE_WORKERS > 1`), the cache is skipped and direct SQLite is used.

## Testing

```bash
# Start server
./run.sh web

# Test endpoints
curl http://localhost:8002/api/v1/verses/gen.1.1
curl http://localhost:8002/api/v1/info
curl http://localhost:8002/api/v1/search?q=covenant
```

## Path Scope

- `web/server.py` — main API
- `web/nginx.conf` — reverse proxy config
- `web/requirements.txt` — dependencies
- `web/PLAN.md` — historical notes

## Path Scope Additions

- `lib/lexicon/` — lexicon builder + search functions (consumed by web API)
- `lib/connections/types.py` — connection type layer definitions
- `lib/controls/calibration.py` — quality level emoji mapping

## Staleness

| Section | Last Updated |
|---------|-------------|
| RAM Cache | 2026-06-17 |
| Verse Endpoints | 2026-06-21 — added `?context=N` param |
| Search | 2026-06-17 |
| Tab System | 2026-06-17 |
| Lexicon | 2026-06-17 |
| Grammar/Morphology | 2026-06-17 |
| Genealogy | 2026-06-17 |
| OT-in-NT | 2026-06-17 |
| Footnotes/TSK | 2026-06-21 — documented endpoints |
| Chapter Connections | 2026-06-21 — documented endpoints |
| Agent Control | 2026-06-21 — documented endpoints |
