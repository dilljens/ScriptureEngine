---
status: completed
kind: plan
area: connections
author: dillon
created: 2026-08-05
---

# Project: Macro-Analysis Remaining Dimensions (4–10)

Goal: Implement the seven unbuilt dimensions of `docs/plans/macro-analysis-plan.md`
(dims 1–3 shipped: passage density, genre via `generators/passage/genre_tagger.py`,
thematic via `generators/passage/theme_tracer.py`). Each dimension adds
passage-level or book-level connection capability on top of the existing
`passage_connections` table + `generators/passage/` pattern.

## Requirements
- [x] R4: **Inner-biblical interpretation network** — quotation/allusion chains
      with transitive closure (dim 4)
- [x] R5: **Narrative analogy / typology** — OT type → NT antitype narrative
      arcs (dim 5)
- [x] R6: **Source/critical layers** — passages grouped by scholarly source
      attribution (dim 6)
- [x] R7: **Multilingual textual network** — MT ↔ LXX ↔ Vulgate ↔ Peshitta
      passage alignment (dim 7)
- [x] R8: **Social setting / Sitz im Leben** — passages by social context (dim 8)
- [x] R9: **Rhetorical analysis** — passages by rhetorical structure (dim 9)
- [x] R10: **Reception history** — passages linked through interpretive
      tradition (dim 10)

## Pre-resolved Decisions
- **Generator contract**: each dimension = one module in
  `generators/passage/<name>.py` with `run(conn, book_ids=None)` returning a
  count, registered in `GENERATOR_DEFS` in `generators/__init__.py`
  (`module_path: ".passage.<name>"`, `layer: "passage"`) — mirroring
  `theme_tracer.py` / `genre_tagger.py` exactly. Tests ride the existing
  parametrized `test_passage_generators_run` in `tests/test_generators.py`.
- **All outputs write `passage_connections`** rows (source_ref, target_ref,
  type_name, layer, confidence) — no new tables except where a dimension needs
  its own tag source.
- **Dependencies**: dims 5 and 9 build on theme/genre data; dim 7 needs a
  per-verse version-alignment table (`verse_alignments` — check `versions`
  data first; may be derivable from the existing MT/LXX text columns);
  dims 6, 8, 10 need curated tag data — seed from existing scholar tables
  (`lib/api/sources.py`, `sources` provenance on connections) and
  `consensus`/`disagreements` tables rather than new external sources.
- **Quality bar**: confidence < 0.5 for heuristic dims (typology, social
  setting); human-curated tag sets get higher confidence. No LLM calls.

## Track A: Interpretation Network (dim 4) `[x]`
- Description: transitive closure over the existing `intertextual` layer
  quotation/allusion edges → passage-level chains (e.g. Isa 7:14 → Matt 1:23
  → reception chains).
- 📏 Scope: 2 files, ~180 lines

### Phase A1: Closure generator `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] `generators/passage/interpretation_network.py`: walk
      `connections` WHERE layer='intertextual' AND type IN
      ('direct_quotation','allusion','echo') with BFS/closure up to depth 3;
      emit passage_connections rows for same-theme chain endpoints
- [x] Register in GENERATOR_DEFS; dedupe against existing rows (source_hash /
      idempotent upsert)
- [x] Tests: small fixture chain → expected closure edges
- 📏 Scope: `generators/passage/interpretation_network.py` ~130,
      `tests/test_generators.py` +40
- ✅ Checkpoint: `python3 scripts/generate_connections.py --name "Inner-biblical Interpretation Network"` (or the schedule.py equivalent) runs clean; `sentrux check .` unchanged
- ⚙ Fallback: if closure is too noisy, restrict to 'direct_quotation' + 'allusion' only, drop 'echo'

## Track B: Narrative Typology (dim 5) `[x]`
- Description: OT narrative arcs as types → NT antitypes (Exodus→salvation,
  Adam→Christ, temple→body). Builds on theme_tracer's 16 themes.
- 📏 Scope: 2 files, ~170 lines

### Phase B1: Type/antitype generator `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] Curated type→antitype pair list (seed: Adam/Christ, Exodus/redemption,
      Tabernacle/Incarnation, Passover/Last Supper, Israel/vine, Moses/Christ)
      as a module constant or small table
- [x] `generators/passage/typology.py`: for each pair, find OT passage(s)
      (via theme/entity overlap) and NT antitype passage(s); connect with
      type_name='typology', layer='passage'
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `generators/passage/typology.py` ~130, tests +40
- ✅ Checkpoint: run produces ≥5 typology passage rows for the seed pairs;
      spot-check Adam→Christ arc exists
- ⚙ Fallback: restrict to theme_tracer's canonical theme clusters for both
      endpoints (higher precision, fewer arcs)

## Track C: Source/Critical Layers (dim 6) `[x]`
- Description: connect passages that share scholarly source attribution
  (J/E/D/P, Isaiah deutero/trito, Davidic psalms, Pauline corpus etc.).
- 📏 Scope: 3 files, ~150 lines

### Phase C1: Source tag table + generator `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] `passage_source_tags` table (ref, source_label, confidence) seeded with
      the consensus critical attributions (book/chapter level)
- [x] `generators/passage/source_layers.py`: connect passages sharing a
      source_label (same layer='passage', type_name='shared_source')
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `lib/db.py` +10, `generators/passage/source_layers.py` ~100,
      seed script ~40
- ✅ Checkpoint: seed table populated; generator emits rows; no DSS/odd
      attributions (consistency-check skill passes)
- ⚙ Fallback: if curated attribution is contested for a book, exclude that
      book from the seed (document why)

## Track D: Multilingual Textual Network (dim 7) `[x]`
- Description: align MT ↔ LXX ↔ Vulgate ↔ Peshitta passage pairs and connect
  passages with interesting translation divergence/agreement.
- 📏 Scope: 3 files, ~220 lines

### Phase D1: Alignment table `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 14
- [x] Audit existing text storage (`lib/db.py` versions columns /
      `web/routes/versions.py` / `scripture_versions` tool) — determine what
      version texts are already present and at what granularity
- [x] `verse_alignments` table (verse_ref, version, aligned_verse_ref) built
      from chapter/verse offsets; populate for books with MT+LXX coverage
- 📏 Scope: `lib/db.py` +12, builder script ~80
- ✅ Checkpoint: alignment rows cover a sampled book (e.g. Psalm 1–10)
      correctly
- ⚙ Fallback: if only KJV/WEB are present for most books (no real LXX text),
      downgrade to "translation-family alignment" (KJV↔WEB↔LSV agreement) and
      document the gap for a future LXX ingest

### Phase D2: Divergence generator `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [x] `generators/passage/multilingual_network.py`: connect passages whose
      aligned verses show notable divergence (e.g. differing verse counts,
      textual differences flagged in data) OR high agreement; register it
- 📏 Scope: `generators/passage/multilingual_network.py` ~100
- ✅ Checkpoint: generator runs; rows exist for both agreement and divergence
- ⚙ Fallback: emit only agreement edges if divergence signal is unreliable

## Track E: Social Setting (dim 8) `[x]`
- Description: passages by Sitz im Leben (cultic, prophetic court, wisdom
  school, diaspora, exile, synagogue).
- 📏 Scope: 3 files, ~150 lines

### Phase E1: Setting tags + generator `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 10
- [x] `passage_social_tags` table (ref, setting, confidence) seeded from
      consensus scholarship (book-level defaults, chapter overrides where
      clear)
- [x] `generators/passage/social_setting.py`: connect passages sharing a
      setting (type_name='shared_setting'), low confidence 0.4–0.6
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `lib/db.py` +10, seed ~40, generator ~90
- ✅ Checkpoint: generator emits rows per setting; validator passes
- ⚙ Fallback: ship as tag-only (no connections) if setting edges are noisy —
      the tag table still powers search/filter

## Track F: Rhetorical Analysis (dim 9) `[x]`
- Description: passages by rhetorical structure (legal case, lament,
  judgment oracle, hymn, wisdom instruction).
- 📏 Scope: 2 files, ~130 lines

### Phase F1: Rhetorical-type generator `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 10
- [x] Curated rhetoric tags per passage (reuse genre_tagger output as the
      base, add rhetoric layer on top: e.g. Isa 1–5 judgment oracle, Psalms
      of lament)
- [x] `generators/passage/rhetorical.py`: connect same-rhetoric passages
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `generators/passage/rhetorical.py` ~90, seed data ~40
- ✅ Checkpoint: run produces rows; sample matches scholarly expectation
- ⚙ Fallback: fold rhetoric into genre_tagger's labels instead of a new
  generator if it becomes redundant

## Track G: Reception History (dim 10) `[x]`
- Description: passages linked through interpretive tradition (which
  commentators/traditions engaged a passage, and how traditions chain).
- 📏 Scope: 2 files, ~160 lines

### Phase G1: Reception chain generator `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 12
- [x] Reuse `consensus` (ecumenical engagement) + `sources` (scholar
      attribution) + `disagreements` tables to find passages engaged by the
      same tradition/scholar network; connect same-tradition passages
      (type_name='shared_reception', layer='passage')
- [x] `generators/passage/reception_history.py`; register it
- 📏 Scope: `generators/passage/reception_history.py` ~120, tests +40
- ✅ Checkpoint: generator emits rows for at least the well-documented
      traditions (e.g. temple microcosm, divine council — see
      `scripture_truth_topic`)
- ⚙ Fallback: restrict to `consensus`-confirmed engagements only; mark
      speculative chains with confidence < 0.5

## Track H: Rollup `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 5
- [x] Update `docs/plans/macro-analysis-plan.md` table: dims 4–10 → done as
      they land
- [x] Progress log `docs/plans/macro-analysis-dimensions-progress.md`
- ✅ Checkpoint: all tracks checked; parent table accurate
- ⚙ Fallback: none

## Out of Scope
- New external corpora (reception history stays within existing
  consensus/sources data — no new ingests)
- LLM-assisted tagging (curated constants only)
- Changing the `passage_connections` schema (only additive tag tables)
