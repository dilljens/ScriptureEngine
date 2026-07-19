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

Phase 6: Hebrew & Language   [✅ COMPLETE — ~4h integration]
  Track C: 7 Hebrew features [✅ All built, most needed integration wiring]
  Track D: Entity expansion  [✅ Already built]
  Track E: Lexicon defs      [⏳ Ongoing agent work between sessions]

Phase 7: Assessment Engine   [✅ COMPLETE — ~6h remaining deferred]
  Track F: Foundation        [✅ SUBSTANTIALLY BUILT]
    F1: Knowledge domain     [✅ 685K items (target was 15K)]
    F2: Prerequisite graph   [✅ 18,717 rules (target was 300)]
    F3: Adaptive engine      [✅ BLIM + Bayesian implemented]
    F4: Auto-gen items       [✅ 247 → 1,000 via new script]
    F5: Assessment frontend  [✅ AssessmentView.jsx wired in App.jsx]
  Track G: IRT & FSRS        [✅ Built]
    G1: IRT calibration      [✅ lib/assessment/irt.py — online calibration, EAP ability estimation]
    G2: FSRS spacing         [✅ next_review + spaced review schedule in quiz_progress]
  Track H: Progress & Recs   [✅ Built]
    H1: Progress tracking    [✅ quiz/progress endpoint with per-layer mastery]
    H2: Recommendations      [✅ quiz/recommendations endpoint]
```

### Current state
- Phase: 5 ✅, 6 ✅, 7 ✅ (core complete; ~6h deferred for dashboard frontend, deeper recommendations)
- Tests: 6/6 pass (quick tests), frontend builds clean
- Assessment items: 1,000 (up from 247)
- Assessment API: 7 REST endpoints (quiz, answer, progress, due, recommendations, start, answer-old)
- IRT: Online calibration from response data + EAP ability estimation
- FSRS: Spaced review scheduling with exponential intervals (1d→3d→7d→14d→30d→60d→90d→180d)

### Round 4: Phase 6 — Hebrew & Language Enhancements ✅ (~4h integration)

Discovered most features were **already built** — needed frontend integration wiring:

| Task | Status | What was done |
|------|--------|---------------|
| **C1: Cloze cards** | ✅ Already built | `ClozeCardRenderer` + `clozeFromVerse` existed. Used in `HebrewLessonView` practice flow. |
| **C2: Frequency vocab** | ✅ Integrated | Added "📊 Top Vocab" button in `HebrewLearnView` → fetches `/api/v1/vocabulary` → renders via `CardQueue` |
| **C3: Passage study** | ✅ Already built | `PassageReader.jsx` wired in `HebrewLearnView` with "📖 Read Passage" button |
| **C4: Translation cards** | ✅ Already built | `TranslationCardRenderer` + `translationFromVerse` existed in `CardRenderer`/`card-factory` |
| **C5: Daily verse** | ✅ Integrated | `DailyVerse.jsx` existed. Added "📆 Verse of Day" button in `HebrewLearnView` |
| **C6: Audio-first** | ✅ Integrated | `AudioReviewSession.jsx` existed. Added "🎧 Audio Review" button in `HebrewLearnView` |
| **C7: Hebrew-only** | ✅ Integrated | Added toggle in `SettingsPanel` → flows through `CardQueue` → `CardRenderer` → `VocabCardRenderer` |
| **D1: Entity expansion** | ✅ Already built | `scripts/expand_entities.py` existed (864 lines) |
| **E1: Lexicon defs** | ⏳ Ongoing | Agent-driven — between sessions, batch-generate 500 lemma definitions |

## Session 2026-07-19 (later) — Connection Automation & Bug Fixes ✅

### What was done
- [x] **P3.1**: Wired `compute_agreement_counts()` into `scripts/generate_connections.py` — auto-runs after generation
- [x] **P3.2**: Verified `graph_centrality` WHERE clause is already correct (plan doc was outdated)
- [x] **P3.3**: Fixed `queue.pop(0)` → `deque.popleft()` in `web/routes/graph.py` BFS
- [x] **P1**: Verified scheduler already exists (`scripts/schedule.py`, 310 lines + `schedule.yaml`)
- [x] **P4**: Verified generator tests already exist (`tests/test_generators.py`, 18 tests)
- [x] **P2**: Built `generator_meta` table + change detection for incremental generation
  - Added table schema to `lib/db.py`
  - Added `_compute_source_hash()`, `_record_generator_run()`, `_should_skip_generator()` in `generators/__init__.py`
  - `run_all()` now supports `incremental=True` flag to skip unchanged generators
- [x] **P5.1**: Verified entity cache already loads from DB (`_load_entity_cache` in `graph_search.py`)
- [x] **P5.2**: Verified 2-hop graph search already implemented (`_find_hop_neighbors` with `MAX_HOPS=2`)

### Plan Assessment
The Connection Automation & Quality plan was **mostly already implemented**. Real remaining items:
- P2 (incremental generation) — now built
- P3.4 (calibrate LR values with empirical data) — still a stretch goal

### Net Changes (cumulative across all sessions)
```
modified:   MASTER_PLAN.md
modified:   findings.md
modified:   progress.md
modified:   task_plan.md
modified:   lib/api/fire_unified.py
modified:   lib/api/search.py
modified:   web/server.py
modified:   web/routes/graph.py              deque fix
modified:   web/routes/assessment.py          IRT + FSRS + recommendations + due reviews
modified:   generators/__init__.py            Incremental gen + sefirot mapper
modified:   generators/sefirot_mapper.py
modified:   lib/api/__init__.py
modified:   lib/api/sefirot.py
modified:   web/routes/sefirot.py
modified:   lib/db.py                         generator_meta table
modified:   lib/assessment/irt.py             New IRT module
modified:   scripts/generate_connections.py   Agreement count hook
modified:   scripts/generate_assessment_items.py  New auto-generator
modified:   web/routes/auth.py                Recovery keys + settings sync + sessions table
modified:   frontend/src/settings.jsx
modified:   frontend/src/components/SettingsPanel.jsx
modified:   frontend/src/components/HebrewLearnView.jsx
modified:   frontend/src/components/CardQueue.jsx
modified:   frontend/src/App.jsx
modified:   tests/__snapshots__/openapi.json  146→152 endpoints
```

