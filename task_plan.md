# Project: Testing & Validation Infrastructure

**Goal:** Implement a pre-deploy test gate, API endpoint tests, database validation, and monitoring so that broken code cannot be deployed.

## Requirements
- [ ] R1: `deploy.sh` must run tests before rsync — fail deploy if tests fail
- [ ] R2: Python test suite covers 10+ core API endpoints
- [ ] R3: Database integrity checks run before deploy (no orphaned refs, no duplicates)
- [ ] R4: Graph regression checks — layer counts, quality levels, tradition labels
- [ ] R5: API contract snapshot prevents accidental endpoint changes
- [ ] R6: Health endpoint enhanced with DB integrity + cache status
- [ ] R7: Structured logging replaces print() statements
- [ ] R8: ntfy.sh push notifications on health failure

## Pre-resolved Decisions
- **Test framework:** pytest + httpx.AsyncClient (FastAPI standard)
- **Test DB:** In-memory SQLite with production schema for unit tests; read-only production DB for integration
- **Coverage:** pytest-cov, start at 50% threshold
- **Playwright:** Page Object Model, replace waitForTimeout with explicit waits
- **Monitoring:** ntfy.sh (free, no registration)
- **No new dependencies beyond:** pytest, pytest-cov, httpx, hypothesis, schemathesis

## Phase 1: Pre-Deploy Gate (P0)
- Description: Tests must pass before deploy.sh can rsync
- ⏱ Timebox: 4 hours

### P1.1: Test infrastructure `[ ]`
- [ ] Create `tests/conftest.py` — FastAPI TestClient fixture with in-memory SQLite
- [ ] Create `tests/__init__.py` — package marker
- [ ] Add `pytest` config to `pyproject.toml`
- ✅ **Checkpoint:** `python3 -m pytest tests/ -x -q` runs without error

### P1.2: Core endpoint tests `[ ]`
- [ ] `tests/test_verses.py` — verse lookup, 404, connections field exists
- [ ] `tests/test_search.py` — search returns results, no query crashes
- [ ] `tests/test_gematria.py` — gematria computation, value lookup
- [ ] `tests/test_graph.py` — graph explore, centrality, search endpoints
- [ ] `tests/test_quiz.py` — quiz endpoint returns questions by tier
- ✅ **Checkpoint:** `python3 -m pytest tests/ -x -q` passes with 10+ tests

### P1.3: DB schema + integrity tests `[ ]`
- [ ] `tests/test_db_schema.py` — all tables and expected columns exist
- [ ] `tests/test_db_integrity.py` — no orphaned verse refs, no duplicates
- ✅ **Checkpoint:** All DB tests pass against production schema

### P1.4: Graph regression tests `[ ]`
- [ ] `scripts/test_graph_regression.py` — layer counts, quality levels, tradition labels, no duplicates
- [ ] Expected count baselines per connection type
- ✅ **Checkpoint:** `python3 scripts/test_graph_regression.py` exits 0

### P1.5: API contract snapshot `[ ]`
- [ ] `tests/__snapshots__/openapi.json` — committed OpenAPI spec
- [ ] `tests/test_openapi_snapshot.py` — fail if spec changes
- ✅ **Checkpoint:** Snapshot test passes

### P1.6: Deploy gate `[ ]`
- [ ] Update `scripts/deploy.sh` to run tests, graph regression, and DB check before rsync
- ✅ **Checkpoint:** `bash scripts/deploy.sh --dry-run` validates checks pass

## Phase 2: Monitoring (P2)
- Description: Health endpoint, structured logging, push notifications
- ⏱ Timebox: 2 hours

### P2.1: Enhanced health endpoint `[ ]`
- [ ] Add DB integrity check, cache status, version, uptime to `/api/v1/health`
- [ ] Add slow request logging middleware (>1s)
- ✅ **Checkpoint:** `curl /api/v1/health` returns full status

### P2.2: Structured logging `[ ]`
- [ ] Replace `print()` with JSON logger in key endpoints
- [ ] Log format: `{"level":"info","msg":"...","timestamp":"..."}`
- ✅ **Checkpoint:** Server logs are valid JSON

### P2.3: ntfy.sh notifications `[ ]`
- [ ] Add curl-based ntfy.sh alert to `scripts/health-check.sh`
- [ ] Add cron entry suggestion for 5-min health checks
- ✅ **Checkpoint:** `bash scripts/health-check.sh --alert` sends notification

## Build Order
```
Day 1:  P1.1 + P1.2 (test infra + core tests) — 3h
Day 2:  P1.3 + P1.4 (DB integrity + graph regression) — 2h
Day 3:  P1.5 + P1.6 (API snapshot + deploy gate) — 2h
Day 4:  P2.1 + P2.2 + P2.3 (monitoring) — 2h
```
