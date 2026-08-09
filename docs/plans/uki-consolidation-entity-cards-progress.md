# Progress Log — UKI-Inspired Graph Ops: Entity Cards, Consolidation, Access Decay

Plan: `docs/plans/uki-consolidation-entity-cards.md` — **status: completed** (2026-08-06)

Session log for Tracks A–D. All checkpoints pass; no production DB was written
(all runs used temp-DB fixtures; the smoke run used a copy of `data/test/test.db`).

## What was built

### Track A — Materialized Entity Cards
- `lib/db.py`: `entity_cards` table (`CREATE TABLE IF NOT EXISTS`, live-DB safe).
- `scripts/build_materialized_views.py`: new `build_entity_cards()` step — one JSON
  card per `entity_links` row (metadata + aliases, all verses, intra-set
  connections, top co-occurring entities via the existing
  `entity_cooccurrence` table, gematria where the entity is a Hebrew surface,
  with a niqqud-tolerant consonant fallback).
- `lib/api/materialized.py::entity_card(conn=None, entity=None)` — registry-contract
  signature (mirrors `entity_deep(conn, entity)`), graceful "run
  build_materialized_views.py" error on a missing view.
- `lib/api/__init__.py`: registered `scripture_entity_card` (layer graph).
- `web/routes/graph.py`: `GET /api/v1/entities/{entity_id}` → `{"ok": true, "data": card}`,
  404 for unknown entity / unbuilt view. Uses `lib.db.get_db()` (honors the test-DB
  override, unlike the router's hardcoded `get_conn()`).
- OpenAPI snapshot regenerated (`tests/__snapshots__/openapi.json`, 172 → 173 paths).

### Track B — Consolidation Pipeline
- `lib/controls/consolidation.py` (new): 5 stages orchestrated by `consolidate(conn, dry_run=True)`:
  1. **Inspect** — trigram Jaccard merge candidates over `entity_links` name/alias
     surfaces (same entity_type, sim ≥ 0.9), read-only contradiction scan
     (direction-normalized, tolerates missing `deprecated`/`quality_level`
     columns), stale via `needs_revalidation()`.
  2. **Resolve** — explicit sources (`text/script/tsk/human/bible_dictionary`)
     beat algorithmic; higher calibrated `rate_connection_row` quality wins.
     Idempotent via a `metadata.consolidation.resolved` marker on the loser.
  3. **Merge** — coalesce duplicate `entity_links`: merge aliases, re-point
     `verse_entities` (+ materialized `entity_cooccurrence`, tolerating a
     missing table), drop stale `entity_cards`, delete the duplicate row.
  4. **Generalize** — audit-only frequent `(layer, type)` rules; no auto-write.
  5. **Forget** — archive `confidence < 0.1 AND created > 180d` to
     `archived_connections` (never hard-delete).
- `scripts/consolidate.py` (new): `--dry-run` (default, report only) / `--apply`
  (idempotent — re-running reports 0 new actions), `--json`, `--db`.
- `lib/db.py`: `archived_connections` table + guarded migrations for
  `connections.access_count` and `entity_links.aliases` (`PRAGMA table_info` check).

### Track C — Access-Modulated Temporal Decay
- `lib/controls/temporal.py`: `access_count` (default 0) on
  `apply_temporal_decay` / `get_staleness` / `needs_revalidation`;
  `effective_years = years / (1 + access_count * 0.2)` via `_effective_years`;
  `ACCESS_DAMPING = 0.2` documented; half-life table untouched. access_count=0 →
  byte-identical output (unit-tested).
- `lib/api/connections.py`: best-effort, batched `UPDATE connections SET
  access_count = access_count + 1` on `get_connections` / `get_intertext`
  read paths; skips when the column is unavailable; rowcount-gated commit.
- `lib/db.py`: guarded `ALTER TABLE connections ADD COLUMN access_count`.

### Track D — Docs & Rollup
- `docs/plans/uki-integration-plan.md` priority table: P4/P5/P7 → ✅ Done,
  total remaining 820 → 490 lines.
- This progress log.

## Verification results

| Checkpoint | Result |
|---|---|
| `python3 -m pytest tests/test_consolidation.py -q` | **12 passed** |
| `python3 -m pytest tests/ -k "temporal or entity" -q` | **21 passed** |
| `python3 -m pytest tests/test_entity_cards.py -q` | **10 passed** |
| `python3 -m pytest tests/ -q` (full suite) | **314 passed, 1 skipped** (273s) |
| Builder + card smoke (temp DB) | `build_entity_cooccurrence` + `build_entity_cards` → `scripture_entity_card` returns populated card for `person.abraham` (3 verses, 1 intra-set connection) |
| `tools/connections.py '{"tool":"scripture_entity_card","entity":"person.abraham"}'` | populated card (temp DB) |
| `scripts/consolidate.py --apply` ×2 (temp DB) | 1st run: 1 merged + 1 archived; 2nd run: **0 new actions**; `PRAGMA integrity_check` = ok |
| Migration idempotency | `init_db()` twice on a pre-existing DB → `access_count`/`aliases` present, no error |
| OpenAPI snapshot | regenerated, `/api/v1/entities/{entity_id}` present |
| `sentrux check .` | same 3 pre-existing violations (`max_cycles`, `max_cc`, `no_god_files`) — **no new** |

## Deviations from the plan

1. **No prod write for the A1 checkpoint.** The plan checkpoint ran the builder on
   the prod DB; the task rule forbids writing `data/processed/*.db`. The builder +
   tool smoke ran against a copy of the test DB instead (read-only on prod
   never happened).
2. **`reconnect_all` does not exist** in the codebase (`revalidate_connection_row`
   is internal to `lib/controls/temporal.py` and is exercised by the temporal
   tests). Nothing to verify beyond `revalidate_connection_row` keeping its shape.
3. **C2 throttle changed.** The plan's fallback throttle (`access_count % 10`)
   is unusable: a counter that only advances on writes can never reach the
   modulo trigger, so it deadlocks at the first write. Used the plan's primary
   instruction instead — a single batched `access_count = access_count + 1`
   UPDATE per request, kept off the hot verse-lookup path, commit gated by
   rowcount.
4. **`entity_card` signature** follows the tool registry contract
   (`(conn, entity)`), matching `entity_deep`; the plan's `entity_card(entity_id)`
   shorthand is satisfied by the optional-conn form.
5. **Merge candidates use pure-Python trigram Jaccard** over name/alias
   surfaces rather than an FTS5 trigram virtual table on `entity_links` (none
   exists); same stdlib-only intent, higher threshold (0.9) for precision.

## Net line delta

- Modified: **+445 / −17** (lib/api/*.py, lib/controls/temporal.py, lib/db.py,
  scripts/build_materialized_views.py, web/routes/graph.py, OpenAPI snapshot,
  parent plan doc)
- New: **+1131** (`lib/controls/consolidation.py` 546, `scripts/consolidate.py` 83,
  `tests/test_consolidation.py` 220, `tests/test_entity_cards.py` 200,
  `tests/test_temporal.py` 82)
- Total: **~+1559** production/test lines (plus this doc and the plan doc).

## Files touched

| File | Change |
|---|---|
| `lib/db.py` | +`entity_cards`, `archived_connections` tables; +`access_count`, `aliases` guarded migrations |
| `lib/controls/consolidation.py` | NEW — 5-stage pipeline |
| `scripts/consolidate.py` | NEW — CLI (`--dry-run` / `--apply`) |
| `lib/controls/temporal.py` | +`access_count` on decay/staleness/revalidation |
| `lib/api/materialized.py` | +`entity_card` |
| `lib/api/connections.py` | +`_bump_access_counts` read instrumentation |
| `lib/api/__init__.py` | +`scripture_entity_card` tool |
| `scripts/build_materialized_views.py` | +`build_entity_cards` |
| `web/routes/graph.py` | +`GET /api/v1/entities/{entity_id}` |
| `tests/test_consolidation.py` | NEW |
| `tests/test_entity_cards.py` | NEW |
| `tests/test_temporal.py` | NEW |
| `tests/__snapshots__/openapi.json` | regenerated |
| `docs/plans/uki-integration-plan.md` | P4/P5/P7 → done |

Not committed (per task instructions). No production DB was written.
