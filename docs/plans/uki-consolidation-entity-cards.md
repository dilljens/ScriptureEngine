---
status: completed
kind: plan
area: graph
author: dillon
created: 2026-08-05
---

# Project: UKI-Inspired Graph Ops — Entity Cards, Consolidation, Access Decay

Goal: Close the three remaining phases of `docs/plans/uki-integration-plan.md`
(P4 materialized entity cards, P5 consolidation pipeline, P7 access-count
modulated temporal decay). Parent plan: `uki-integration-plan.md` (its Phases
1–3 + 6 are already shipped via `29a0fc7`).

## Requirements
- [x] R1: **Entity cards** — a materialized per-entity JSON card (metadata,
      aliases, all verses, connections among those verses, co-occurring
      entities, gematria where applicable), exposed as a tool + `GET
      /api/v1/entities/{id}`.
- [x] R2: **Consolidation pipeline** — a periodic script that inspects,
      resolves contradictions, merges duplicate entities, generalizes patterns,
      and archives stale/low-confidence connections — idempotent, dry-run
      first.
- [x] R3: **Access-modulated decay** — connection confidence decay slowed by
      reads (queries/study guides), accelerated for neglected edges; wired into
      the existing `lib/controls/temporal.py` half-life model without breaking
      `apply_temporal_decay`'s callers.

## Pre-resolved Decisions
- **Entity cards reuse the existing materialization pattern**: extend
  `scripts/build_materialized_views.py` (which already builds
  `similar_verses` + `entity_cooccurrence` views consumed by
  `lib/api/materialized.py`) with an `entity_cards` table — do NOT write a
  fresh ad-hoc builder. The card assembles data already returned by
  `lib/api/graph.py::entity_deep` + `entity_cooccurrence` — the materialized
  view just pre-packages it.
- **Consolidation reuses existing controls** — contradiction scan:
  `lib/controls/contradiction.py::scan_all_contradictions`; stale detection:
  `lib/controls/temporal.py::needs_revalidation`; merge candidates: trigram
  similarity over `entity_links.name`/`aliases` (the FTS5 trigram pattern
  already used by `lib/api/graph_search.py`). New module
  `lib/controls/consolidation.py` orchestrates the 5 stages.
- **Decay is backward compatible**: add an `access_count` parameter with
  default 0 to `apply_temporal_decay`/`get_staleness`; the formula
  `effective_years = years / (1 + access_count * damping)`; default `damping`
  ~0.2. Track reads via a light `UPDATE connections SET access_count =
  access_count + 1` on the read paths in `lib/api/connections.py` (best-effort,
  throttled — not on hot verse lookups). Migration: `ALTER TABLE connections
  ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0` via the existing
  migration pattern in `lib/db.py`.
- **No new dependencies** — all stdlib/sqlite.

## Track A: Materialized Entity Cards `[x]`
- Description: entity card view + API + tool. Parent-plan P4.
- 📏 Scope: ~4 files, ~250 lines

### Phase A1: Materialized view + builder `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] Add `entity_cards` table schema (id, entity_id UNIQUE, card_json,
      built_at) in `lib/db.py` (CREATE TABLE IF NOT EXISTS — live-DB safe)
- [x] Extend `scripts/build_materialized_views.py` to populate it: entity
      metadata from `entity_links`, verses from `verse_entities`, intra-set
      connections, top co-occurring entities, gematria where the entity is a
      Hebrew surface
- [x] `lib/api/materialized.py::entity_card(entity_id)` returning the JSON
      with the same graceful "run build_materialized_views.py" error as
      `similar_verses`
- 📏 Scope: `lib/db.py` +8, `scripts/build_materialized_views.py` +120,
      `lib/api/materialized.py` +35
- ✅ Checkpoint: `python3 scripts/build_materialized_views.py` then
      `python3 tools/connections.py '{"tool":"scripture_entity_card","entity":"person.abraham"}'`
      returns a populated card
- ⚙ Fallback: if the full intra-set connection query is slow, materialize
      only metadata+verses+cooccurrence and compute connections at request
      time (still one query, joins on verse_entities)

### Phase A2: Tool + HTTP endpoint `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 8
- [x] Register `scripture_entity_card` in `lib/api/__init__.py` TOOL_DEFS
      (layer `graph`, mirrors `scripture_entity_deep` signature)
- [x] `GET /api/v1/entities/{entity_id}` in `web/routes/` (or extend
      existing graph router) returning `{"ok": true, "data": card}`
- [x] Tests: `tests/test_generators.py`-style — card exists for a known
      entity, 404-style error for unknown
- 📏 Scope: `lib/api/__init__.py` +1 tool, `web/routes/` +15, tests +30
- ✅ Checkpoint: `python3 -m pytest tests/ -k entity -q` passes; OpenAPI
      snapshot regenerated (`scripts/` regen script used by prior plans)
- ⚙ Fallback: keep HTTP endpoint off until the view builds in CI; tool works
      off the live DB

## Track B: Consolidation Pipeline `[x]`
- Description: 5-stage periodic maintenance. Parent-plan P5.
- 📏 Scope: ~4 files, ~220 lines

### Phase B1: `lib/controls/consolidation.py` + dry-run `scripts/consolidate.py` `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [x] Stage 1 Inspect: merge candidates via trigram name/alias similarity on
      `entity_links`; contradictions via `scan_all_contradictions()`; stale via
      `needs_revalidation()`
- [x] Stage 2 Resolve: explicit connections beat algorithmic; higher
      confidence wins (reuse `rate_connection`/calibration)
- [x] Stage 3 Merge: coalesce duplicate `entity_links` rows (merge aliases,
      re-point `verse_entities`, keep canonical)
- [x] Stage 4 Generalize: record frequent (layer, type) → layer rules (audit
      only, no auto-write)
- [x] Stage 5 Forget: archive `confidence < 0.1` AND stale > 180d — to an
      `archived_connections` table, NOT hard delete
- [x] CLI: `python3 scripts/consolidate.py --dry-run` (report only, no
      writes) / `--apply`; idempotent (re-running --apply is a no-op on
      already-consolidated data)
- [x] Migration for `archived_connections` + `entity_links` merge support
- 📏 Scope: `lib/controls/consolidation.py` ~150, `scripts/consolidate.py`
      ~40, `lib/db.py` +15
- ✅ Checkpoint: dry-run on a temp DB produces a sane report; --apply on temp
      DB leaves `PRAGMA integrity_check` clean; second --apply run reports 0
      new actions
- ⚙ Fallback: if trigram similarity on 560 entities is noisy, require exact
      alias-list overlap before proposing a merge (precision over recall)

### Phase B2: Verification + tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [x] Unit tests: merge candidate detection, contradiction resolution,
      forget/stale boundary, idempotency
- 📏 Scope: `tests/test_consolidation.py` ~120
- ✅ Checkpoint: `python3 -m pytest tests/test_consolidation.py -q`; live DB
      untouched by tests (temp-DB fixture pattern)
- ⚙ Fallback: none — test-only phase

## Track C: Access-Modulated Temporal Decay `[x]`
- Description: reads slow decay, neglect accelerates it. Parent-plan P7.
- 📏 Scope: ~3 files, ~90 lines

### Phase C1: Decay API extension `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [x] `lib/controls/temporal.py`: `access_count` param on
      `apply_temporal_decay` + `get_staleness`; `effective_years = years /
      (1 + access_count * 0.2)`; document damping constant; keep half-life
      table unchanged
- [x] Back-compat: existing callers (calibration, propagation) pass nothing →
      access_count defaults 0 → identical output; add a unit test asserting
      decayed confidence is unchanged when access_count=0
- 📏 Scope: `lib/controls/temporal.py` ~40, tests ~30
- ✅ Checkpoint: `python3 -m pytest tests/ -k temporal -q`; existing
      truth-alignment tests still green
- ⚙ Fallback: none — pure function change

### Phase C2: Read-path instrumentation + migration `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [x] `ALTER TABLE connections ADD COLUMN access_count ... DEFAULT 0`
      (idempotent migration in `lib/db.py`)
- [x] Best-effort increment on connection-read paths in
      `lib/api/connections.py` (bounded: batch per request, skip when
      `SELECT access_count` is unavailable)
- [x] Verify `revalidate_connection_row` + `reconnect_all` flows still work
- 📏 Scope: `lib/db.py` +8, `lib/api/connections.py` +15
- ✅ Checkpoint: `python3 -m pytest tests/ -q` (full suite, temp-DB);
      `sentrux check .` shows no new violations
- ⚙ Fallback: if hot-path cost is measurable, throttle to `access_count % 10
      == 0` per connection or drop instrumentation (decay API stays useful
      standalone)

## Track D: Docs & Rollup `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 5
- [x] Update `docs/plans/uki-integration-plan.md` priority table: P4/P5/P7 →
      done (once their tracks pass)
- [x] Progress log `docs/plans/uki-consolidation-entity-cards-progress.md`
- ✅ Checkpoint: all tracks checked; parent plan table accurate
- ⚙ Fallback: none

## Out of Scope
- Conversation→entity promotion (already shipped as
  `scripture_conversation_promote_connection`)
- Entity cards for study guides/audit tooling beyond the API+tool
- Any schema change to `connections` beyond the additive `access_count` column
