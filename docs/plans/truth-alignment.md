# Truth Alignment System — Research & Recommendations

Research date: 2026-07-13
Sources: Academic papers on KG confidence calibration, provenance systems (TrustGraph, Wikipedia), existing `lib/controls/` code audit.

## Current State — What's Already Strong

| Component | What It Does |
|-----------|-------------|
| `lib/controls/null_text.py` | Monte Carlo p-values, Bonferroni/FDR correction, effect sizes |
| `lib/controls/preregistration.py` | Prevents p-hacking — declare method before seeing data |
| `lib/controls/calibration.py` | Multi-signal weighted scoring (discovery×type×confidence×bonuses) |
| `lib/controls/stats.py` | Statistical verification framework |
| `lib/connections/types.py` | 12 types with layer, subtype, strength, confidence, quality_level |
| `lib/connections/pardes.py` | PaRDeS mapping — what *kind* of truth each connection represents |
| `lib/api/sources.py` | Scholar attribution and provenance tracking |
| `lib/api/disagreements.py` | Interpretive disagreement tracking |

## Recommendations (Priority Order)

### 🔴 High Priority

1. **Inter-source agreement scoring** — When 3 independent sources find the same connection, boost confidence 20%. Count distinct `discovered_by` values for the same verse-pair+type.

2. **Contradiction detection** — Flag when two connections between the same verse pair contradict (e.g., "direct quotation" vs "echo"). Use a `CONTRADICTION_MATRIX` mapping type pairs to conflict scores.

3. **Temporal decay + revalidation** — Algorithmic discoveries decay faster (2yr half-life) than human scholarship (5yr). Mark stale connections for revalidation.

4. **Bayesian ensemble confidence** — Replace linear weighted sum with likelihood ratio product:
   - `P(real|signals) / P(chance|signals) = prior_odds × product(LR_i)`
   - Naturally handles: multiple weak signals stacking, one strong signal being sufficient, contradictory signals producing <0.5

### 🟡 Medium Priority

5. **Disputed quality tier** — Add `disputed` tier alongside verified/strong/probable. Connect disagreements system to calibration so conflicting connections get auto-tagged.

6. **Confidence propagation through graph** — A→B→C path confidence via product with layer compatibility matrix. From CA-GCN literature.

7. **Empirical shrinkage for rare types** — Pull low-N connection types toward layer average to prevent over-interpretation of rare patterns.

8. **Structured user feedback** — Different weights for clicks (0.05) vs reasoning (0.15) vs scholar citations (0.30).

### 🟢 Lower Priority

9. **Source tiering (S0-S5)** — Formalize discovery_method into reliability tiers: S0=text, S5=unverified.

10. **Calibration audit script** — Weekly health check: type distribution, method skew, staleness, contradictions.

11. **Speculative→Rejected lifecycle** — Full connection status lifecycle with audit trail. Never delete — just archive.

12. **PROV-O provenance metadata** — Self-documenting creation chain per connection (extraction method, timestamp, calibration version, revalidation history).

## Key Insight

The single highest-ROI change is Bayesian ensemble (#4) combined with inter-source agreement (#1). This replaces the current weighted sum with a probability-theoretic foundation and naturally handles multi-source confirmation.
