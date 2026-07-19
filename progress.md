# Progress: Scripture Engine — Implementation

## Session 2026-07-19 — Plan Created + Execution Rounds 1-3

### Round 1: Plan Created
- [x] Created `task_plan.md` — full implementation plan covering all remaining ~40h
- [x] Created `findings.md` — pre-resolved decisions, architecture notes, risk assessment
- [x] Created `progress.md` — session tracking
- [x] Rewrote `MASTER_PLAN.md` — concise system status cross-ref to task_plan.md

### Round 2: Track 0 — Trigram FTS5 ✅
- [x] **0A**: `scripts/build_fts_index.py` **already existed** (fully built, 223 lines)
- [x] **0B**: `web/server.py` — `_trigram_search`, `_keyword_search` **already wired**
- [x] **0C**: `lib/api/search.py` — `search_text` uses trigram **already done**; updated `search_xlingual` for trigram English branch
- [x] **0D**: `_search_hebrew` / `_search_greek` in server.py **already use trigram first**
- [x] **Table built**: `verses_fts_trigram` has 70,956 rows
- [x] **Search verified**: Hebrew (ברית), Greek (λόγος), English substring all working

### Round 3: Phase 5 — Polish & Quick Wins ✅
- [x] **5A1**: ntfy.sh push notifications on health failure — `_send_ntfy_alert()` in `web/server.py`
- [x] **5B2**: FIRe penalty flow — added `_apply_verse_stability_penalty()` to `lib/api/fire_unified.py` (was missing from unified module; the memorize route had it but was never called)
- [x] **5B1**: Sefirotic mapping — full implementation:
  - `generators/sefirot_mapper.py` — 10 sefirot definitions, keyword matching, connection creation
  - Registered in `generators/__init__.py`
  - `lib/api/sefirot.py` — MCP tools: `scripture_sefirot`, `scripture_sefirah_info`
  - `web/routes/sefirot.py` — REST endpoints: GET sefirot for verse, list sefirot, get sefirah verses
  - Registered route + tools in server and tool registry
  - 17,706 verse labels, 49,500 connections created

### Plan Execution Status

```
Phase 5: Polish & Quick Wins [✅ COMPLETE — ~5h]
  Track A: Infrastructure    [✅]
    A1: ntfy.sh              [✅]
  Track B: Memorization      [✅]
    B1: Sefirotic mapping    [✅]
    B2: FIRe penalty flow    [✅]

Track 0: Trigram FTS5        [✅ COMPLETE — ~2h]
  All 4 phases               [✅]

Phase 6: Hebrew & Language   [⬜ NOT STARTED — ~15h]
  Track C: 7 Hebrew features [⬜]
  Track D: Entity expansion  [⬜]
  Track E: Lexicon defs      [⬜]

Phase 7: Assessment Engine   [⬜ NOT STARTED — ~20h]
  Track F: Foundation        [⬜]
  Track G: IRT & FSRS        [⬜]
  Track H: Progress & Recs   [⬜]
```

### Current state
- Phase: 5 complete, 6+7 not started
- Tests: 198 passed, 1 skipped, 1 deselected (pre-existing Hebrew test failure)
- OpenAPI: 149 endpoints (updated snapshot)

### Net Changes (this session)
```
modified:   MASTER_PLAN.md          Rewritten as top-level reference
modified:   findings.md             New — pre-resolved decisions, architecture
modified:   progress.md             New — session tracking
modified:   task_plan.md            New — full implementation plan
modified:   lib/api/fire_unified.py Added stability penalty on verse failure
modified:   lib/api/search.py       Trigram for xlingual English search
modified:   web/server.py           ntfy.sh + sefirot route + import
modified:   generators/__init__.py  Registered sefirot mapper
modified:   lib/api/__init__.py     Registered sefirot MCP tools
modified:   tests/__snapshots__/openapi.json Updated (146→149 endpoints)
new file:   generators/sefirot_mapper.py  10 sefirot → 49.5K connections
new file:   lib/api/sefirot.py            MCP tool + lookup
new file:   web/routes/sefirot.py         3 REST endpoints
```
