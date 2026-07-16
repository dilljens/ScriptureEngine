# Progress: Full Codebase Audit & Search Enhancement

## Session 2026-07-13 — Codebase Audit COMPLETE

### Track A: Convention Fixes ✅
| Phase | Before | After | What |
|-------|--------|-------|------|
| A1 | 8 errors | 0 | Bare excepts in generators (8 files) |
| A2 | 73 errors | 0 | Bare excepts in lib/web/scripts/data (30+ files) |
| A3 | 47 warnings | 0 | print() → logging in web routes + lib code |
| A4 | 4 warnings | 0 | console.log → DEV guard in frontend |
| A5 | 1 error | 0 | Go panic → log.Fatalf |

### Track B: Static Analysis ✅
5969 → 2023 Ruff errors (style-only). All real bugs fixed: undefined names, duplicate dict keys, closure-captured loop variables, exception chain breaks, bare KeyboardInterrupt catches.

### Track C: Test Suite Health ✅
All 38 tests pass. FastAPI lifespan deprecation fixed, duplicate route handlers removed.

### Track D: Runtime Verification ✅
API server smoke tests (7/7 endpoints 200), frontend build clean, Go vet clean.

## Session 2026-07-15 — Search Enhancement (Unicity-Inspired) COMPLETE

### Track A: Query Sanitization ✅
- Fixed `_sanitize_fts_query` in web/server.py and lib/api/search.py
- Strips FTS5 special chars: `? / ( ) + . - " * ^ ~`
- Prevents FTS5 syntax errors (unicity found 83% of BEIR queries crashed)

### Track B: Query Cache ✅
- New `lib/api/query_cache.py` — SQLite-backed persistent cache
- SHA256 key, TTL-based (300s), auto-eviction at 10K entries
- Wired into both /api/v1/search and /api/v1/semantic-search

### Track C: Graph-Enhanced Search (3-Way RRF) ✅
- New `lib/api/graph_search.py` — leverages 1.7M connections as 3rd search signal
- Entity extraction from query → entity_links match → verse_entities → 1-hop connections
- 3-way RRF fusion with adaptive alpha weighting
- Explains each result ("Matched: entity 'Abraham' + entity 'Isaac'")

### Track D: Scalar Quantization ⏭️ Not applicable (sqlite-vec 0.1.x limitation)

### Track E: Cross-Encoder Reranker ✅
- New `lib/api/reranker.py` — optional reranker, graceful degradation
- SEE early-exit for 3.5× speedup

## Session 2026-07-16 — Infrastructure & Testing COMPLETE

### Track A: CI Pipeline ✅
- Added `python-lint` job: runs `ruff check` on every push/PR
- Added `python-tests` job: builds test DB → runs pytest
- Frontend + Go + Python now all tested in CI

### Track B: Deployment Blockers ✅
- All 6 gitignored frontend files verified present
- App.jsx verified clean (MemorizeIcon + openMemorizeTab resolved)
- Frontend builds clean in 3.5s
- No stale IPs in deployment docs

### Track C: Test Database Fixture ✅
- New `scripts/create_test_db.py` — builds 4KB test DB from production schema
- 13 verses, 8 connections, 3 assessment items, 12 entities, 16 verse-entity links
- `conftest.py` auto-detects test DB, falls back to production
- Tests run in 35s (vs 69s with 2.3GB prod DB)
- Deterministic, CI-runnable, no huge data dependency

### Net Changes
```
 .github/workflows/ci.yml          | +37    CI pipeline (ruff + pytest)
 lib/api/graph_search.py           | +396   New: graph-enhanced search
 lib/api/query_cache.py            | +180   New: SQLite query cache
 lib/api/reranker.py               | +180   New: cross-encoder reranker
 lib/api/search.py                 | +31    Sanitization + graph signal in MCP path
 scripts/create_test_db.py         | +450   New: test DB builder
 tests/conftest.py                 | +30    Auto-detect test/prod DB
 tests/test_graph.py               | +3     Skip handling
 tests/test_verses.py              | +9     Broader assertion
 web/server.py                     | +177   Cache + graph + reranker + sanitization
```

## What's Next (Highest Priority)

### 1. Add API Test Coverage (8h)
Only ~10% of 152 endpoints are tested. Priority targets:
- Study guides CRUD (18 endpoints) — create, publish, fork, export
- Hebrew learning (20 endpoints) — lessons, drills
- Memorization (10 endpoints) — FSRS, palaces, FIRe
- Conversations/chat (12 endpoints)

### 2. Agent-Written Lexicon Definitions (ongoing)
Only 411 of 11,515 lemmas have definitions. LLM can batch-generate the remaining ~11,100.

### 3. Expand entity_links (4h)
Only 87 entities for 70K verses. Algorithmic extraction from verse text would dramatically improve graph search.

### 4. Adaptive Knowledge Assessment Engine (~50h)
MASTER_PLAN items 2.9-2.16: domain definition, prerequisite graph, BLIM + Bayesian, IRT calibration, FSRS assessment, progress tracking, recommendations.
