# ScriptureEngine — Connection Automation & Quality Plan

*Based on codebase analysis conducted 2026-07-19*

---

## Executive Summary

ScriptureEngine has 52 connection generators, 1.77M connections across 11 layers, 8 quality control modules, and 131 scripts — but **no automation**. Every generator runs manually. Temporal decay is computed but never acted on. Quality calibration has a hardcoded 0 in a critical path. Tests exist for the API but **zero tests for any generator or quality control module**.

This plan addresses the three biggest gaps:
1. **No scheduler** — nothing ever re-generates connections or acts on staleness
2. **No generator tests** — 52 generators, zero tests
3. **No incremental generation** — running all 52 generators wastes time on unchanged sources

---

## Current State

```
                Manual CLI trigger
                       │
                       ▼
            ┌──────────────────┐
            │  run all 52 gens  │  git status | grep modified
            │  (no deps, no    │  no cache of what changed
            │   incremental)   │  no dependency ordering
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │  connections     │  1.77M rows
            │  table           │  11 layers, 124 types
            └────────┬─────────┘
                     │
            ┌────────▼─────────┐
            │  null_text       │  per-type p-values
            │  validation      │  single-threaded, memory-bound
            └────────┬─────────┘
                     │
            ┌────────▼─────────┐
            │  calibration     │  Bayesian ensemble
            │                  │  BUT agreement_count = 0 (unimplemented)
            └────────┬─────────┘
                     │
            ┌────────▼─────────┐
            │  temporal decay  │  half-life computed but never used
            │  (query-time)    │  needs_revalidation() exists but has no caller
            └──────────────────┘
```

---

## Phase 1: Scheduler Foundation

### 1.1 Add a Lightweight Scheduler

**File:** `scripts/schedule.py`

A simple YAML-configured scheduler that replaces the manual `python3 scripts/generate_connections.py` workflow:

```yaml
# schedule.yaml
pipeline:
  - name: regenerate_all
    interval_days: 7
    command: "python3 scripts/generate_connections.py --all"
    
  - name: revalidate_stale
    interval_days: 1
    command: "python3 scripts/schedule.py --revalidate-stale"
    
  - name: rebuild_ft5
    trigger_on: [ingest_*, ingest_*.py]
    command: "python3 scripts/build_fts_index.py"
```

The scheduler reads the config and runs each step:
- `regenerate_all`: Weekly full generation
- `revalidate_stale`: Daily — query `connections` for staleness (using `lib/controls/temporal.py`'s `needs_revalidation()`) and regenerate only those connections whose half-life has passed
- Index rebuild: Triggered after any ingest script

**Implementation:** `scripts/schedule.py` (~150 lines) with:
- `python3 scripts/schedule.py` — run all due pipeline steps
- `python3 scripts/schedule.py --revalidate-stale` — revalidate stale connections
- `python3 scripts/schedule.py --status` — show pipeline status and last-run times
- A simple `last_run.json` state file for tracking what ran when

### 1.2 Integrate with CI

**File:** `.github/workflows/ci.yml` — add a `schedule` event:

```yaml
on:
  schedule:
    - cron: '0 6 * * 0'  # Weekly: full regenerate
    - cron: '0 6 * * 1-6'  # Daily: revalidate stale
  workflow_dispatch:
    inputs:
      pipeline_step:
        description: 'Pipeline step to run'
        default: 'all'
```

This replaces the current manual-only workflow.

### 1.3 Staleness Dashboard

**New API endpoint:** `GET /api/v1/pipeline/status`

Returns:
```json
{
  "last_full_generation": "2026-07-12",
  "connections_total": 1770000,
  "connections_stale": 342000,
  "connections_critical": 87000,
  "generator_last_run": {
    "linguistic": "2026-07-12",
    "gematria": "2026-06-30",
    "intertextual": "2026-05-15"
  },
  "ingest_last_import": {
    "tsk": "2026-07-01",
    "lxx": "2025-11-20",
    "dss": "2026-03-15"
  }
}
```

**Lines:** ~200 (schedule.py) + ~30 (CI config) + ~80 (API endpoint) = **~310 lines**

---

## Phase 2: Generator Incremental Support

### 2.1 Generator Dependencies

Each generator currently exports `run(conn, book_ids=None)` with no metadata about what it depends on. Add a `depends_on` field to `GENERATOR_DEFS`:

```python
{
    "name": "Linguistic — Same Lemma",
    "module_path": ".linguistic",
    "layers": ["linguistic"],
    "automatic": True,
    "depends_on": ["ingest_strongs"],  # NEW
    "provides": ["same_lemma", "same_root", "same_morphology"],
    "run_time_seconds": 45,
}
```

**Dependency graph:**

```
ingest_strongs → linguistic (45s) → intertextual (120s) → ...  
ingest_gematria → gematria (30s) → symbolic (60s) → ...
ingest_tsk → structural (90s) → ...  
```

### 2.2 Change Detection

Add generation timestamps per source type in a `generator_meta` table:

```sql
CREATE TABLE generator_meta (
    generator_name TEXT PRIMARY KEY,
    last_run_at TEXT NOT NULL,
    source_hash TEXT,        -- hash of input data at last run
    connection_count INTEGER,
    duration_ms INTEGER
);
```

When deciding whether to run a generator:
1. Check `last_run_at` for staleness
2. Compare `source_hash` against current hash of input data
3. If neither stale nor changed, skip

### 2.3 Book-Scoped Generation

Many generators support `book_ids=None` (all books). But often only one book's data changed. Add `--books` support to the scheduler:

```bash
python3 scripts/schedule.py --books isa     # Only Isaiah-related generators
python3 scripts/schedule.py --layer sod     # Only sod generators
python3 scripts/schedule.py --changed-sources  # Auto-detect what changed
```

**Lines:** ~200 across `generators/__init__.py`, `db.py`, and `schedule.py`

---

## Phase 3: Fix Quality Pipeline Known Bugs

### 3.1 Fix `agreement_count = 0`

**File:** `lib/controls/calibration.py`, line ~460

The `rate_connection_row()` function has `agreement_count=0` hardcoded with the comment "Will be populated by Track D" — Track D was never implemented. This means multiple independent sources confirming the same connection don't get the confidence boost they should.

**Fix:** Implement Track D:
1. When a connection is created by generator X, check if generator Y also produces the same (source, target, layer) combination
2. If so, increment `agreement_count` on the connection record
3. The LR multiplier for agreement_count (3 sources = 3x, 4+ sources = 5x) now actually works

**Lines:** ~80

### 3.2 Fix `graph_centrality` Dead WHERE

**File:** `web/routes/graph.py`, line ~402

```python
# Current (broken):
where_clauses = []
# ... code builds where_clauses but never passes them to query:
" AND ".join(where_clauses)  # ← discarded, no effect
cursor.execute("""
    SELECT ... FROM connections ...
    GROUP BY source_verse
    ORDER BY cnt DESC LIMIT ?
""", [limit])
```

**Fix:** Pass the joined WHERE clause into the SQL query:

```python
where_sql = " AND ".join(where_clauses)
if where_sql:
    where_sql = "WHERE " + where_sql
cursor.execute(f"""
    SELECT ... FROM connections ...
    {where_sql}
    GROUP BY source_verse
    ORDER BY cnt DESC LIMIT ?
""", [limit])
```

**Lines:** ~10

### 3.3 Fix `list.pop(0)` → `collections.deque`

**File:** `web/routes/graph.py`, BFS implementation

```python
# Current O(n²):
queue = [...]
while queue:
    current = queue.pop(0)  # O(n) per pop
    
# Fix O(n):
from collections import deque
queue = deque([...])
while queue:
    current = queue.popleft()  # O(1) per pop
```

**Lines:** ~5

### 3.4 Fix Calibration LR Values

**File:** `lib/controls/calibration.py`

All likelihood ratios are currently guessed (1.2x–20x) with no empirical basis. Replace with data-driven values by:

1. Running each generator against a held-out gold standard (e.g., TSK cross-references as ground truth)
2. Computing actual precision/recall per generator
3. Converting to empirical LRs: `LR = sensitivity / (1 - specificity)`
4. Updating the LR tables

**Lines:** ~100 (new `scripts/calibrate_lrs.py`)

---

## Phase 4: Test Coverage

### 4.1 Generator Tests

**New file:** `tests/test_generators.py`

For each generator, test:
- It runs without errors (smoke test)
- It produces valid connection records (correct schema)
- It doesn't create duplicate (source, target, layer, type, subtype) rows
- It's idempotent (running twice produces same results)
- Handle empty input (no books specified, empty DB)

```python
def test_linguistic_generator():
    conn = get_test_db()
    count = linguistic.run(conn, book_ids=["gen"])
    assert count > 0
    rows = conn.execute("SELECT COUNT(*) FROM connections WHERE layer='linguistic'").fetchone()[0]
    assert rows == count
    # Idempotency: second run should produce no new rows
    count2 = linguistic.run(conn, book_ids=["gen"])
    assert count2 == 0
```

**Lines:** ~300 (one test module, ~6 tests per generator × 52 generators via parametrize)

### 4.2 Calibration Tests

**New file:** `tests/test_calibration.py`

- `rate_connection_row` produces valid star ratings (0-5)
- Agreement multiplier works when `agreement_count > 0`
- Temporal decay function produces correct half-lives
- Contradiction detection identifies known conflict pairs

**Lines:** ~150

### 4.3 Search Quality Regression Tests

**New file:** `tests/test_search_quality.py`

- Known queries return expected verses
- Hebrew cross-lingual search works
- Graph search finds entity-linked results
- Empty query returns appropriate fallback

**Lines:** ~100

### 4.4 Current Test Fixes

**File:** `tests/test_api.py`

Some tests accept 5xx as "OK" (e.g., `test_assessment_start`, `test_hebrew_fsrs_review`). These mask real failures and should be fixed to expect the correct status code or document the known issue.

---

## Phase 5: Graph Search Improvements

### 5.1 Replace Hardcoded Entity Frozensets with DB Queries

**File:** `lib/api/graph_search.py`

Current: 75 hardcoded entities in `KNOWN_PEOPLE`, `KNOWN_PLACES`, `KNOWN_CONCEPTS` frozensets.

Fix: Query `entity_links` table at module load time. Falls back to hardcoded sets if DB not available:

```python
def _load_entities(conn):
    if conn is None:
        return KNOWN_PEOPLE, KNOWN_PLACES, KNOWN_CONCEPTS  # fallback
    people = set()
    try:
        rows = conn.execute(
            "SELECT DISTINCT name FROM entity_links WHERE entity_type IN ('person', 'prophet', 'apostle')"
        ).fetchall()
        people = {r[0].lower() for r in rows}
    except Exception:
        pass
    return people or KNOWN_PEOPLE, ...
```

### 5.2 Enable Multi-Hop Graph Search

Current: `MAX_HOPS=2` defined but only 1-hop implemented.

Fix: Add a 2-hop expansion in `_find_hop_neighbors()`. At 2 hops, verses that share a connection through an intermediate entity appear:

```
Verse A —[same_lemma]→ Verse B —[geographic]→ Verse C
                                           ↑
                                    Verse A now reaches Verse C
                                    via 2-hop traversal
```

### 5.3 Add Entity Disambiguation

Entity extraction currently treats "John" as one entity. Add disambiguation by checking `verse_entities` for context:

```python
def _disambiguate(entity_name, context_verse):
    """Given 'John' in context of verse 'matt.3.1', return specific John entity ID."""
    rows = conn.execute("""
        SELECT entity_id FROM entity_docs
        WHERE doc_id = ? AND entity_name = ?
        ORDER BY confidence DESC LIMIT 1
    """, (context_verse, entity_name)).fetchone()
    return rows[0] if rows else entity_name
```

---

## Lines Summary

| Phase | What | Lines |
|-------|------|-------|
| **P1** | Scheduler + CI + dashboard | ~310 |
| **P2** | Incremental generation + deps | ~200 |
| **P3** | Quality bug fixes (4 bugs) | ~195 |
| **P4** | Tests: generators, calibration, search | ~550 |
| **P5** | Graph search improvements | ~180 |
| **Total** | | **~1,435 lines** |

---

## Priority Order

| Priority | What | Why |
|----------|------|------|
| 🔴 P3.1 | Fix `agreement_count` | Bug in critical quality path — star ratings wrong |
| 🔴 P1 | Add scheduler | Without this, everything is manual and stale |
| 🔴 P4 | Add generator tests | 52 untested modules = blind spot |
| 🟠 P3.2 | Fix graph_centrality WHERE | Book/layer filters don't work on centrality |
| 🟠 P3.3 | Fix deque | Minor perf bug in critical web endpoint |
| 🟠 P2 | Incremental generation | Saves time on regeneration |
| 🟡 P5 | Graph search improvements | Better search quality for users |
| 🟡 P3.4 | Calibrate LR values | More accurate star ratings |
