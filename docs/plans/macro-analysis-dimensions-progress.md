# Progress: Macro-Analysis Remaining Dimensions (4–10)

## Session 2026-08-05 (implemented)

All seven unbuilt dimensions of `docs/plans/macro-analysis-plan.md` shipped as
passage-level generators. See `docs/plans/macro-analysis-dimensions.md`
(status: completed).

### What was built (all in `generators/passage/`, all registered in GENERATOR_DEFS)
| Dim | Module | Type | How it works |
|---|---|---|---|
| 4 | `interpretation_network.py` | `interpretation_chain` | Walks direct-quotation chains (A quotes B, B quotes C); aggregates endpoints into passages; emits cross-testament, same-network edges. Explicit-direct-quotation only; hub degree ≤ 150; 100 pairs/hub. |
| 5 | `typology.py` | `typology` | Lifts the existing curated `typology` table (28 verse-level pairs) into passage arcs + 4 narrative-level arcs (Exodus→salvation, wilderness→testing, temple→body, out-of-Egypt→Son). |
| 6 | `source_layers.py` | `shared_source` | Curated J/E/D/P + Deutero/Trito-Isaiah + Psalms-books + Deuteronomistic History + apocalyptic tags into `passage_source_tags`; connects same-source passages. |
| 7 | `multilingual_network.py` | `translation_divergence` | KJV/WEB/LSV divergence per verse (1 − word overlap); top-3 crux passages per book; connects cross-book crux passages. **Documented gap: no LXX/Vulgate/Peshitta text — this is translation-family divergence, not versional alignment.** |
| 8 | `social_setting.py` | `shared_setting` | 11 settings × 28 curated passages (`passage_social_tags`); connects same-setting cross-book passages. |
| 9 | `rhetorical.py` | `shared_rhetoric` | 17 curated form-critical tags (`passage_rhetoric_tags`); connects same-rhetoric passages. |
| 10 | `reception_history.py` | `shared_reception` | Verses with recorded interpretive disagreement (`interpretive_disagreements`, 33 verses incl. isa.1.2 with 98 signals) are reception nodes; connects cross-book tradition-engaged passages with scholar-provenance metadata. |

### Real-data output (copy of data/processed/scripture.db; all idempotent, run2 = 0)
| Generator | rows |
|---|---|
| interpretation_network | 47,200 |
| typology | 42 |
| source_layers | 5 |
| multilingual_network | 15,235 |
| social_setting | 24 |
| rhetorical | 6 |
| reception_history | 3 |

Total: passage_connections 7,151 → 102,887 (+95,736) across all ten new
generators (this plan's 7 + the 3 discovery generators).

### Design decisions worth recording
- **Dim 4 density control**: first version (all 3 intertextual types, any
  testament, verse-pair chains) produced 1.2M rows — a near-complete graph that
  would swamp the table. Restricted to explicit `direct_quotation` only,
  cross-testament chains, passage-level aggregation, deterministic sorted
  iteration, and per-hub caps. Result: 47k faithful, high-signal edges
  (e.g. ezek.1.24 ↔ rev.5.2 via rev.10.1 — Ezekiel vision quoted in
  Revelation).
- **Idempotency**: running caps break idempotency (run 2 processes pairs
  beyond run 1's cutoff). Fixed by making selection deterministic (sorted
  iteration, passage-level dedup) — no running caps.
- **Dim 7 honesty**: real MT↔LXX alignment is impossible without LXX text;
  the generator surfaces translation-family cruxes and documents the gap for a
  future LXX/Vulgate/Peshitta ingest rather than faking versional alignment.
- **Dim 10 conservatism**: only data already in the engine (interpretive
  disagreements + scholar provenance) — no new ingests, low confidence (0.45).

### Verification
- `python3 -m pytest tests/test_generators.py -q` → 29 passed (new "Passage —"
  generators auto-included via GENERATOR_DEFS).
- ruff clean on all new files; `sentrux check .` unchanged (3 pre-existing).
- Production DB untouched during verification (temp copy); live ingest part of
  rollup.

### Net file changes
- New: `_common.py`, `interpretation_network.py`, `typology.py`,
  `source_layers.py`, `multilingual_network.py`, `social_setting.py`,
  `rhetorical.py`, `reception_history.py` (+~900 lines)
- Modified: `generators/__init__.py` (+7 registrations),
  `generators/passage/__init__.py`, `docs/plans/macro-analysis-plan.md`
  (dims 4–10 marked done), plan doc (completed)
