# UKI → ScriptureEngine Integration Plan

*How patterns from the Universal Knowledge Index can improve ScriptureEngine.*

---

## Overview

UKI (uki) was built as a universal knowledge indexer — it evolved from clew, which was originally forked from ScriptureEngine's search/knowledge-graph code. The two codebases share deep DNA: UKI's `generators/__init__.py` and `knowledge/card.py` explicitly cite ScriptureEngine as inspiration.

Now the innovations have reversed direction. UKI has developed capabilities that ScriptureEngine doesn't have.

**Status: Partially implemented.** The 2026-07 version of this plan proposed 8 phases. Phases 2–4 have been implemented. This updated plan reflects what was done, what the deeper uki codebase audit revealed, and a revised priority order.

---

## ✅ Completed (from original plan)

### Phase 2: DAT 3D Alphas for Search — ✅ Done

Implemented in `web/server.py` `_get_dat_alphas()` (line 1437). Query-adaptive 3D weights:
- Long queries → favor vector
- Questions → favor vector
- Entity mentions → favor graph
- Hebrew/Greek → favor BM25
- Verse references → favor BM25 + graph

Also supports `entity_ratio` for fine-tuning graph weight.

### Phase 3: Cross-Encoder Reranker + SEE — ✅ Done

Implemented in `lib/api/reranker.py`. Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` with SEE (Similarity-based Early Exit):
- Pre-filters low-similarity docs via `all-MiniLM-L6-v2` bi-encoder (~3.5× speedup)
- Batched cross-encoder score for promising candidates
- Graceful degradation if `sentence-transformers` not installed

### Phase 4: BLIM Confidence for Search — ✅ Done

Implemented in `lib/api/search_confidence.py`. Full 2PL IRT model:
- Per-result calibrated confidence (0-100)
- `KnowledgeState` persistence to JSON for cross-session calibration
- Bayesian update from implicit feedback
- Shared DNA with `lib/assessment/models.py`

### Phase 5 (partial): Graph-Enhanced Search — ✅ Done

Implemented in `lib/api/graph_search.py`. Entity-aware traversal:
- Extracts entity candidates from query via `entity_links` table
- Finds matching entities via trigram FTS5
- Explores 2-hop neighborhood via connections
- Scores verses by graph proximity to query entities
- Each result carries explanation string

---

## 🔴 Phase 1: Generator Registry Enhancement

### What

Add `tier`, `cost`, and `precision` metadata fields to the existing `GENERATOR_DEFS` dicts in `generators/__init__.py`. Currently each def has `name`, `module_path`, `layers`, `automatic`, `requires`, `description`. Add:

```python
{
    "name": "Linguistic — Same Lemma",
    "module_path": ".linguistic",
    "layers": ["linguistic"],
    "automatic": True,
    "tier": "idle",               # NEW: lightweight | idle | periodic
    "cost": "free",               # NEW: free | llm_call | external_api
    "precision": 0.78,            # NEW: empirical precision 0.0-1.0 (optional)
    "avg_run_time_s": 45,         # NEW: average runtime in seconds
    "requires": "gematria table (present)",
    "description": "Connects verses sharing rare Hebrew lemmas (Strong's numbers)",
}
```

### Tier Classification

| Tier | Criteria | Example Generators |
|------|----------|-------------------|
| **lightweight** | < 1s, pure SQL | `same_lemma`, `same_root`, `same_morphology`, `keyword_linking`, `chiasm_detected`, `semuchin` |
| **idle** | 1-30s, moderate compute | `distribution`, `hapax_dislegomenon`, `formula_count`, `refrain`, `inclusio`, `parallelism` |
| **periodic** | > 30s or external API | `intertextual` (book-pair scans), `gematria` (full canon), `geographic`, `heiser_divine_council`, `beale_temple_creation`, `barker_angel_yhwh` |

### Cost Classification

| Cost | Criteria | Examples |
|------|----------|---------|
| **free** | Zero external cost | All algorithmic generators (~45) |
| **external_api** | Requires API call | `sefaria_api` (if added), agent-generated connections |
| **llm_call** | Uses LLM for extraction | (future) AI-assisted connection discovery |

### What This Unlocks

- `list_generators()` can filter by `tier` and `cost`
- Pipeline scheduler knows which generators to run when
- Telemetry: "which generators consume the most time?"
- Calibration: `generator_precision` parameter gets populated

### Pattern from uki

uki uses a `GeneratorDef` class with `register()`/`get_generators(tier=..., cost=...)` helpers:

```python
class GeneratorDef:
    def __init__(self, name: str, description: str, tier: str, cost: str,
                 automatic: bool = True, run_fn=None):
        self.tier = tier  # "lightweight" | "idle" | "periodic"
        self.cost = cost  # "free" | "llm_call"
```

SE's dict approach works fine — the class is a style preference. The metadata fields are what matter.

### Lines: ~50 (metadata edits across 45+ GENERATOR_DEFS entries)

---

## 🔴 Phase 2: Tiered Pipeline Scheduler

### What

Replace the manual generator workflow (`python3 scripts/generate_connections.py --name "X"`) with a schedule-driven pipeline. Builds on the existing `generator_meta` table (already tracks `last_run_at`, `source_hash`, `connection_count`, `duration_ms`).

### Scheduler Script

```python
# scripts/schedule.py
"""
Usage:
  python3 scripts/schedule.py                # Run all due steps
  python3 scripts/schedule.py --status        # Show pipeline status
  python3 scripts/schedule.py --revalidate-stale  # Stale connections only
  python3 scripts/schedule.py --tier periodic      # Run only periodic tier
"""
```

### Schedule Config

```yaml
# schedule.yaml
pipeline:
  - name: reconnect_all
    interval_hours: 168        # Weekly — every 7 days
    tier: "periodic"
    generators: ["all"]
    description: "Full regeneration of all algorithmic connections"

  - name: revalidate_stale
    interval_hours: 24         # Daily
    tier: "idle"
    generators: ["temporal.revalidate"]
    description: "Revalidate stale/low-confidence connections"

  - name: lightweight_pass
    interval_hours: 1          # Hourly
    tier: "lightweight"
    generators: ["auto"]
    description: "Run all lightweight generators for recently added data"
```

### Key Design Decisions

- **Schedule file is declarative YAML** (not cron) for readability and audit
- **Generator picks up where it left off** — `generator_meta.last_run_at` drives staleness
- **Source hash change detection** — existing `_compute_source_hash()` already supports this
- **Respects tier classification** from Phase 1

### Lines: ~170

---

## 🔴 Phase 3: Write Hooks — Auto-Fire Lightweight Generators

### What

After a connection is added, automatically fire lightweight generators that can discover additional connections from the new data. This creates a **cascade effect** — one manually-approved connection can yield many algorithmic suggestions.

### Pattern from uki

uki's `KnowledgeStore.put_entity()` calls `_run_lightweight_generators()` synchronously on every entity write. The pattern is:

```python
def add_connection(conn, source, target, layer, type_name, **kwargs):
    # 1. Insert connection (existing code)
    conn.execute("INSERT INTO connections ...", ...)
    
    # 2. Fire lightweight generators (NEW)
    deferred = _fire_lightweight_hooks(conn, source, target)
    
    return {"connection_id": cid, "new_suggestions": deferred}
```

### Trigger Points

| Trigger | Location | Effect |
|---------|----------|--------|
| New connection added | `lib/db.py` `add_connection()` | Fire lightweight generators for source/target verses |
| New entity created | `scripts/*` or direct DB | Fire scope_linker for the entity |
| Manual connection approved | `staging_connections` → `connections` | Fire lightweight generators from approved pair |

### Generator Cascade

```
User adds: gen.1.1 ↔ exod.12.2 (direct_quotation)
  ↓ Fire lightweight generators:
  ├── same_lemma: find other verses sharing rare lemmas
  ├── keyword_linking: find shared rare keywords
  ├── semuchin: adjacent verse check
  └── shared_verse_overlap: find overlapping verse references
  ↓ New connections discovered → staged for review
```

### Key Design Decisions

- **Lightweight only** (< 1s, SQL-only) — never block for idle/periodic work
- **Results go to staging** — not directly to production connections
- **Dedup via source hash** — prevents infinite loops
- **Opt-in per generator** — only generators marked `automatic=True` and `tier="lightweight"` fire in hooks

### Lines: ~100

---

## 🟠 Phase 4: Entity Cards (Materialized Entity Views)

### What

Add materialized JSON cards for people, places, concepts — like `passage_guides` but for entities. SE already has `entity_links` and `verse_entities` tables with 559+ entities. An entity card would combine:
- Entity metadata (type, aliases, description)
- All verses mentioning the entity
- Connections between those verses
- Co-occurring entities
- Gematria/patterns when applicable

### Pattern from uki

uki's `get_entity_card(entity_id)` builds a JSON card on-the-fly with entity metadata, relations grouped by predicate, tags, and access count. Designed as a hook point for future materialization.

### Implementation

```python
# lib/api/entity_cards.py
def get_entity_card(conn, entity_id):
    info = conn.execute(
        "SELECT * FROM entity_links WHERE id=?", (entity_id,)
    ).fetchone()
    verses = conn.execute(
        "SELECT verse_id FROM verse_entities WHERE entity_id=? LIMIT 100",
        (entity_id,)
    ).fetchall()
    connections = conn.execute("""
        SELECT c.* FROM connections c
        JOIN verse_entities ve1 ON ve1.verse_id = c.source_verse AND ve1.entity_id = ?
        JOIN verse_entities ve2 ON ve2.verse_id = c.target_verse AND ve2.entity_id = ?
        LIMIT 50
    """, (entity_id, entity_id)).fetchall()
    cooccurring = conn.execute("""
        SELECT e2.id, e2.name, COUNT(*) as count
        FROM verse_entities ve1
        JOIN verse_entities ve2 ON ve2.verse_id = ve1.verse_id AND ve2.entity_id != ?
        JOIN entity_links e2 ON e2.id = ve2.entity_id
        WHERE ve1.entity_id = ?
        GROUP BY e2.id ORDER BY count DESC LIMIT 20
    """, (entity_id, entity_id)).fetchall()
    return build_card(info, verses, connections, cooccurring)
```

### HTTP API

```
GET /api/v1/entities/{entity_id}              # Entity card
GET /api/v1/entities/{entity_id}/connections   # Entity connections
GET /api/v1/entities/search?q=Abraham          # Entity search
```

### Lines: ~150 (card builder + 3 API endpoints + materialized cache)

---

## 🟠 Phase 5: Consolidation Pipeline

### What

A periodic maintenance pipeline that improves data quality over time. SE has 1,356,667 connections and ~560 entities — some are bound to be redundant, stale, or contradictory.

### Pattern from uki

uki's 5-stage consolidation pipeline runs as a periodic generator:

```python
def consolidate(conn):
    """5-stage consolidation."""
    # Stage 1: Inspect — find merge candidates, contradictions, stale data
    candidates = find_merge_candidates(conn)
    contradictions = find_contradictions(conn)
    stale = find_stale_connections(conn)
    
    # Stage 2: Resolve conflicts — heuristic (or LLM-assisted)
    for pair in contradictions:
        resolve_contradiction(conn, pair)  # lower-confidence loses
    
    # Stage 3: Merge entities — coalesce duplicates
    for candidate in candidates:
        merge_entities(conn, candidate.keep, candidate.discard)
    
    # Stage 4: Generalize patterns — detect frequent connection triples
    patterns = detect_frequent_patterns(conn)
    
    # Stage 5: Forget stale — archive low-confidence, old connections
    forget_stale(conn, stale)
```

### SE-Specific Adaptations

| Stage | SE Adaptation | Why |
|-------|--------------|-----|
| Inspect | Find entity_links with high name similarity (trigram), connections with zero confidence, generators not run in 30 days | SE has `generator_meta` — can detect generators that haven't produced new connections |
| Resolve | Explicit connections have authority over algorithmic; higher confidence wins | SE's `rate_connection()` already scores quality |
| Merge | Entity_links with same name/alias but different IDs | `entity_links` has `aliases` column — pure SQL merge |
| Generalize | "Every connection of type `direct_quotation` has layer `intertextual`" — surfaces schema-level knowledge | Not yet needed at SE's scale, but growth will benefit |
| Forget | Remove connections with `confidence < 0.1` and `last_verified > 180 days` | Keep the graph lean; 1.3M connections can accumulate noise |

### Lines: ~200

---

## 🟠 Phase 6: Conversation → Entity Pipeline

### What

SE's conversation system already stores messages, extracts verse refs, and detects connections. The next step is promoting high-value conversation discoveries to permanent graph entities.

### Pattern from uki

uki's `session_promote` generator scores QA pairs by `feedback × novelty × re-mentions` and promotes high-scoring results to permanent `SessionFact` entities.

### Implementation

```python
# generators/conversation_promote.py
def run(conn, book_ids=None):
    """Promote high-value conversation discoveries to permanent connections."""
    # 1. Find connections detected in conversations
    rows = conn.execute("""
        SELECT sc.*, COUNT(*) as mention_count
        FROM staging_connections sc
        JOIN staging_connection_versions scv ON scv.connection_pending_id = sc.id
        WHERE sc.source = 'conversation'
        GROUP BY sc.source_verse, sc.target_verse
        HAVING mention_count >= 3  # Re-mentioned = higher confidence
    """).fetchall()
    
    # 2. Score by  novelty × re-mentions × confidence
    for row in rows:
        score = min(1.0, row.mention_count / 10) * row.confidence
        if score > 0.5:
            promote_to_connection(conn, row)
    
    return count
```

### What This Unlocks

- **Study insight memory** — connections discovered during chat survive the session
- **Crowdsourced connections** — if multiple users/re-reads notice the same link, it auto-promotes
- **Self-improving graph** — the graph gets richer with use

### Lines: ~120

---

## 🟡 Phase 7: Temporal Decay Enhancement

### What

Merge UKI's access-count-modulated decay with SE's per-method half-lives for connection confidence.

### SE Current State

Connection confidence decays by fixed half-lives per layer. No access-count modulation.

### Enhanced Formula (from uki)

```python
effective_years = years * (1 / (1 + access_count * damping))
confidence * 0.5 ** (effective_years / half_life)
```

Accessing a connection (via queries, study guides, etc.) slows its decay. Neglected connections decay faster.

### Lines: ~30

---

## 🟡 Phase 8: 3-Phase FTS5 Fallback (Typo-Tolerant Search)

### What

SE already has trigram FTS5 with AND → OR → LIKE fallback (Phase 1 in the original trigram work). This phase adds the missing third fallback layer that uki uses.

### SE Current State

`_trigram_search()` does:
1. AND — all trigrams must match (best precision)
2. OR — any trigram matches (typo-tolerant)

### What's Missing

3. **LIKE** — SQL substring match (last resort for very short queries or corrupted FTS5)

This already exists in `_keyword_search()` as fallback. Considered done.

---

## Priority Summary

| Phase | What | Lines | Priority |
|-------|------|-------|----------|
| **P1** | Generator tier/cost metadata | ~50 | 🔴 Now |
| **P2** | Tiered pipeline scheduler | ~170 | 🔴 Now |
| **P3** | Write hooks → lightweight cascade | ~100 | 🔴 Now |
| **P4** | Entity cards (materialized per-entity) | ~150 | 🟠 Next |
| **P5** | Consolidation pipeline (dedup + merge) | ~200 | 🟠 Next |
| **P6** | Conversation → entity promotion | ~120 | 🟠 Next |
| **P7** | Temporal decay enhancement | ~30 | 🟡 Future |
| | **Total remaining** | **~820 lines** | |

### Two Highest-Impact Immediate Changes

1. **Generator tier/cost metadata** (~50 lines) — pure metadata change, unblocks everything below. Can be done in one sitting.

2. **Write hooks** (~100 lines) — transforms the generator UX from "run a script" to "add a connection, get suggestions back." Builds on existing `staging_connections` table so results go to review, not production.

### Already Done vs. Remaining

```
Original plan: 8 phases, ~660 lines
Completed:     Phases 2-4 (DAT alphas, reranker, BLIM confidence, graph search)
Remaining:     Phases 1, 5, 6, 7, 8 + new patterns (consolidation, conversation→entity)
New total:     ~820 lines of remaining work
```

---

## Architecture Note: No Major Refactors Needed

None of these phases require:
- New database migrations (all use existing tables)
- New dependencies (all use existing imports)
- Architecture changes (all sit within existing patterns)
- The `store` abstraction from the original plan is deferred — SE's raw-SQL approach works fine for its domain-specific needs
