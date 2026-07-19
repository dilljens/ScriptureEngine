# UKI → ScriptureEngine Integration Plan

*How patterns from the Universal Knowledge Index can improve ScriptureEngine.*

---

## Overview

UKI (uki) was built as a universal knowledge indexer — it evolved from clew, which was originally forked from ScriptureEngine's search/knowledge-graph code. The two codebases share deep DNA: UKI's `generators/__init__.py` and `knowledge/card.py` explicitly cite ScriptureEngine as inspiration.

Now the innovations have reversed direction. UKI has developed capabilities that ScriptureEngine doesn't have: an automated generator pipeline, a generator registry with tier/cost metadata, write hooks for cascading generation, query-adaptive search alphas, BLIM confidence scoring, and per-entity materialized cards.

This plan covers what UKI patterns to adopt, how to adapt them to ScriptureEngine's existing architecture, and in what order.

---

## Pattern Inventory: What UKI Has That SE Could Use

| # | UKI Pattern | SE Equivalent | Gap | Effort | Impact |
|---|-------------|--------------|-----|--------|--------|
| 1 | **Generator registry** with tier/cost/automatic | GENERATOR_DEFS (exists, no tier/cost) | Missing metadata fields | Low | Unlocks pipeline + calibration |
| 2 | **Tiered pipeline** (lightweight/idle/periodic) | Manual script invocation | No scheduling, no tiers | Medium | Transforms generation UX |
| 3 | **Write hooks** → auto-fire generators | None | No cascade effect | Medium | One manual connection → N algorithmic suggestions |
| 4 | **DAT 3D alphas** (query-adaptive search fusion) | Static heuristic weights | No query adaptivity | Low | Better search for free |
| 5 | **BLIM confidence** for search results | `rate_connection()` (connection-only) | No search-result confidence | Medium | Self-improving search |
| 6 | **Cross-encoder reranker** with SEE | None | Top-N are BM25/vector ranked | Low | Better result ordering |
| 7 | **Entity cards** (per-entity materialized JSON) | `passage_guides` (per-verse only) | No entity cards for people/places | Low | New capability |
| 8 | **Access-count temporal decay** modulation | Per-method half-lives only | No usage boost | Low | Better retention |
| 9 | **`store` abstraction** for generator code | Raw SQL everywhere | Harder to test | High | Long-term maintainability |

---

## Phase 1: Generator Registry Enhancement (Low Effort)

### What

Add `tier`, `cost`, and `automatic` fields to the existing `GENERATOR_DEFS` in `generators/__init__.py`. Currently each def has `name`, `module_path`, `layers`, `automatic`, `requires`, `description`. Add:

```python
{
    "name": "Linguistic — Same Lemma",
    "module_path": ".linguistic",
    "layers": ["linguistic"],
    "automatic": True,
    "tier": "periodic",        # NEW: lightweight | idle | periodic
    "cost": "free",            # NEW: free | llm_call | external_api
    "precision": 0.78,         # NEW: empirical precision 0.0-1.0 (optional)
    "avg_run_time_s": 45,      # NEW: average runtime in seconds
    "requires": "gematria table (present)",
    "description": "Connects verses sharing rare Hebrew lemmas (Strong's numbers)",
}
```

### Tier Classification for All Generators

| Tier | Criteria | Example Generators |
|------|----------|-------------------|
| **lightweight** | < 1s, pure SQL, no external calls | `same_lemma`, `same_root`, `same_morphology`, `keyword_linking`, `chiasm_detected` |
| **idle** | 1-30s, moderate computation | `distribution`, `hapax_dislegomenon`, `formula_count`, `refrain`, `inclusio`, `concentration_index` |
| **periodic** | > 30s or external API calls | `intertextual` (book-pair scans), `gematria` (full canon), `sefaria_api`, `shem_hamephorash_scanner`, `geographic` |

### Cost Classification

| Cost | Criteria | Example Generators |
|------|----------|-------------------|
| **free** | Zero external cost | All algorithmic generators (~45) |
| **external_api** | Requires API call | `sefaria_api` |
| **llm_call** | Uses LLM for extraction | (future) agent-based connection discovery |

### What This Unlocks

- `generators/list_generators()` can now show tier and cost
- `calibration.py`'s `generator_precision` parameter gets populated (was always `None`)
- Pipeline scheduling becomes possible
- Telemetry: "which generators consume the most time?"

### Lines: ~50 (metadata edits across 45 GENERATOR_DEFS entries)

---

## Phase 2: DAT 3D Alphas for Search (Low Effort)

### What

Replace the static heuristic weights in `_merge_results()` (lines 1227-1249 of `web/server.py` and `lib/api/search.py`) with query-adaptive 3D alphas.

### Current Code (static):

```python
if entity_ratio > 0.3:
    alpha_vec, alpha_bm25, alpha_graph = 0.35, 0.40, 0.25
else:
    alpha_vec, alpha_bm25, alpha_graph = 0.40, 0.45, 0.15
```

### Target (adaptive):

```python
def get_alphas_3d(query: str, entity_ratio=0.0):
    alpha_vec, alpha_bm25, alpha_graph = 0.40, 0.45, 0.15
    q = query.strip()
    if len(q.split()) > 5:          # Long query → semantic
        alpha_vec += 0.1; alpha_bm25 -= 0.05
    if q.lower().startswith(("what", "how", "why")):  # Question → semantic
        alpha_vec += 0.1; alpha_bm25 -= 0.05
    if entity_ratio > 0.3:          # Entity mentions → graph
        alpha_graph += 0.1; alpha_bm25 -= 0.05
    if any(ord(c) > 0x05D0 for c in q):  # Hebrew → BM25
        alpha_bm25 += 0.2; alpha_vec -= 0.1
    total = alpha_vec + alpha_bm25 + alpha_graph
    return (alpha_vec/total, alpha_bm25/total, alpha_graph/total)
```

### Lines: ~40

---

## Phase 3: Cross-Encoder Reranker + SEE (Low Effort)

### What

Add optional cross-encoder reranking to the search pipeline, after RRF fusion and before returning results. Port from UKI's `wrappers/reranker.py`.

### Implementation

```python
# lib/search/reranker.py
from sentence_transformers import CrossEncoder, SentenceTransformer

_HAS_RERANKER = False
try:
    _RERANKER = CrossEncoder("BAAI/bge-reranker-v2-m3")
    _SEE = SentenceTransformer("all-MiniLM-L6-v2")
    _HAS_RERANKER = True
except ImportError:
    pass

def rerank(query, results, top_k=20, see_threshold=0.3):
    if not _HAS_RERANKER or not results:
        return results
    # SEE early-exit + cross-encoder scoring (port from UKI)
```

### Lines: ~80

---

## Phase 4: BLIM Confidence for Search Results (Medium Effort)

### What

Add per-result confidence scoring using a 2PL IRT model. The BLIM model is already in `lib/assessment/models.py` — apply it to search results.

### Implementation

```python
# In lib/api/search.py
def score_search_result(query, result):
    """Wrap a search result with BLIM-calibrated confidence 0-100."""
    ability = _query_ability(query)
    blim = BLIM(difficulty=0, discrimination=1.0, guess=0.15, slip=0.10)
    confidence = blim.p_relevant(ability)
    result["confidence_score"] = round(confidence * 100)
    return result
```

### What's Needed

- `score_search_result()` wrapper (~30 lines)
- Feedback endpoint `POST /api/v1/search/feedback` (~50 lines)
- KnowledgeState persistence in SQLite (~30 lines)

### Lines: ~110

---

## Phase 5: Write Hooks — Auto-Fire Lightweight Generators (Medium Effort)

### What

After a connection is added, automatically fire lightweight generators that can discover additional connections from the new data.

### Trigger Points

| Trigger | Location | Effect |
|---------|----------|--------|
| New connection added | `generators/__init__.py` `run_generator()` | Fire lightweight generators for the source/target verse |
| New entity added | `lib/api/entities.py` or direct DB | Fire lightweight generators for the entity |
| Manual connection approved | `staging_connections` → `connections` | Fire lightweight generators from the approved pair |

### Generator Cascade

```
User adds: gen.1.1 ↔ exod.12.2 (direct_quotation)
  ↓ Fire lightweight generators:
  ├── same_lemma: find other verses sharing rare lemmas
  ├── keyword_linking: find shared rare keywords
  └── shared_verse_overlap: check other generators
  ↓ New connections discovered → fire again (dedup prevents loops)
```

### Lines: ~100

---

## Phase 6: Tiered Pipeline Scheduler (Medium Effort)

### What

Replace the manual generator workflow with a schedule.yaml-driven pipeline.

### Scheduler

```python
# scripts/schedule.py
"""
Usage:
  python3 scripts/schedule.py                   # Run all due steps
  python3 scripts/schedule.py --status          # Show pipeline status
  python3 scripts/schedule.py --revalidate-stale  # Stale connections only
"""
```

```yaml
# schedule.yaml
pipeline:
  - name: regenerate_all
    interval_days: 7
    generators: ["all"]
    tier: "periodic"
  - name: revalidate_stale
    interval_days: 1
    generators: ["temporal.revalidate"]
    tier: "idle"
```

### Lines: ~170

---

## Phase 7: Entity Cards (Low Effort)

### What

Add entity cards for people, places, concepts — like passage_guides but for entities.

```python
# lib/api/entity_cards.py
def get_entity_card(conn, entity_id):
    info = conn.execute("SELECT * FROM entity_links WHERE entity_id=?", (entity_id,)).fetchone()
    verses = conn.execute("SELECT verse_id FROM verse_entities WHERE entity_id=? LIMIT 50", (entity_id,)).fetchall()
    # Build card with info, verses, passage connections, co-occurring entities
    return card
```

### Lines: ~80

---

## Phase 8: Temporal Decay Enhancement (Low Effort)

### What

Merge UKI's access-count-modulated decay with SE's per-method half-lives.

### Enhanced formula:

```python
effective_years = years * (1 / (1 + access_count * damping))
confidence * 0.5 ** (effective_years / half_life)
```

### Lines: ~30

---

## Integration Summary

| Phase | What | Lines | Priority |
|-------|------|-------|----------|
| **P1** | Generator registry tier/cost metadata | ~50 | 🔴 Phase 1 |
| **P2** | DAT 3D alphas for search | ~40 | 🔴 Phase 1 |
| **P6** | Tiered pipeline scheduler | ~170 | 🔴 Phase 1 |
| **P3** | Cross-encoder reranker + SEE | ~80 | 🟠 Phase 2 |
| **P4** | BLIM confidence for search | ~110 | 🟠 Phase 2 |
| **P5** | Write hooks → lightweight generators | ~100 | 🟠 Phase 2 |
| **P7** | Entity cards | ~80 | 🟡 Phase 3 |
| **P8** | Temporal decay enhancement | ~30 | 🟡 Phase 3 |
| | **Total** | **~660 lines** | |

### Two highest-impact immediate changes:

1. **DAT 3D alphas** (~40 lines) — zero new infrastructure, pure math, immediately improves every search query. Can be done in one afternoon.

2. **Pipeline scheduler** (~170 lines) — transforms the manual generation workflow into automated, scheduled runs with staleness monitoring. Builds on the existing `connection-automation-quality-plan.md`.
