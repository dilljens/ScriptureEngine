# Plan: Truth Alignment System v2 ✅

Goal: Upgrade the calibration/confidence system from linear weighted sum to Bayesian ensemble, add inter-source agreement scoring, contradiction detection, temporal decay, disputed tier, and confidence propagation.

Status: **All tracks complete** ✅

## Files Changed (net: +610 lines)

| File | Lines | What |
|------|-------|------|
| `lib/controls/calibration.py` | 348 | Bayesian ensemble rewrite + source tiering + structured confirmation |
| `lib/controls/contradiction.py` | 196 | Contradiction matrix + detection + scan + resolution |
| `lib/controls/temporal.py` | 148 | Half-life decay + staleness + revalidation flags |
| `lib/controls/agreement.py` | 87 | Multi-source agreement scoring |
| `lib/controls/propagation.py` | 147 | Layer compatibility + path confidence |
| `lib/db.py` | +8 | Disagreements table schema |
| `scripts/migrate_truth_alignment.py` | 62 | DB migration |
| `scripts/calibration_audit.py` | 103 | Weekly audit report |

## Summary of Changes

### Track A: Bayesian Confidence Ensemble ✅
**Before:** Linear weighted sum: `discovery×0.40 + type×0.30 + confidence×0.15 + bonus×0.10 + confirm×0.05`
**After:** `posterior_odds = prior_odds × product(LR₁, LR₂, ..., LRₙ)`
- Each signal has a likelihood ratio (Bayes factor) from research-grade evidence weights
- Strong signal (text quotation: LR=20×) single-handedly produces high confidence
- Multiple weak signals (algorithm + p-value + agreement) naturally stack
- Added `explain_rating()` showing which signals drove score up/down
- Backward compatible — same function signature, same output shape

### Track B: Contradiction Detection ✅
- Created `disagreements` table (via migration)
- Defined `CONTRADICTION_MATRIX` with 30+ type-pair conflict scores (0.0-1.0)
- Added layer-level incompatibility matrix
- `scan_all_contradictions()` batch processor — tags conflicting connections as `disputed`
- `resolve_disagreement()` + `get_unresolved_disagreements()` for workflow

### Track C: Temporal Decay ✅
- Half-life per discovery method: algorithm=2yr, LLM=1.5yr, human=5yr, text=never
- `apply_temporal_decay()` with exponential decay model
- `get_staleness()` → `fresh/aging/stale/critical`
- `needs_revalidation()` → flags connections for revalidation
- DB migration adds `last_validated` + `revalidation_due` columns

### Track D: Inter-Source Agreement ✅
- `count_independent_sources()` — distinct discovered_by per verse-pair+type
- `agreement_multiplier()` — 1→1.0×, 2→1.5×, 3→2.5×, 4+→3.0×
- Integrated into Bayesian ensemble as `agreement_count` LR parameter

### Track E: Confidence Propagation ✅
- `LAYER_COMPATIBILITY` matrix: linguistic→sod=0.8, geographic→chronological=0.3
- `path_confidence()`: product × length_penalty(1/√n) × layer_compatibility
- `propagate_to_reachable()` for graph traversal integration

### Track F: API + Audit ✅
- `explain_rating()` — human-readable rating explanation
- `scripts/calibration_audit.py` — weekly report: type dist, tier dist, method skew, staleness, contradictions
- Dispute tracking via `disagreements` table

## Acceptance Criteria Check
- [x] `rate_connection()` uses Bayesian ensemble — verified: text→0.99, algorithm→0.403, algorithm+agreement→0.628
- [x] Contradiction scan completes without errors
- [x] Temporal decay: algorithm 2020→0.104, text 2020→1.0
- [x] Inter-source agreement: 3 sources = 2.5× multiplier
- [x] Propagation: 2 hops = 0.317, 1 hop = 0.95
- [x] Audit script produces valid report
- [x] All existing imports/tests work (backward compatible)
