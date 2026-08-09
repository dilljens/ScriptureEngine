---
status: completed
kind: plan
area: connections
author: dillon
created: 2026-08-05
---

# Project: Passage Discovery Generators (Phase 2)

Goal: Build the three Phase-2 discovery generators that
`docs/plans/passage-level-connections.md` planned but never shipped:
`narrative_parallel.py`, `macro_chiasm.py`, `covenant_structure.py`. Phase 1
(schema + density/book_coherence/chiastic_promoter + API + MCP) is done.

## Requirements
- [x] R1: **Narrative parallel detector** — passage-level connections between
      structurally parallel narratives across books (e.g. Exodus 14 / crossing
      motifs, annunciation sequences)
- [x] R2: **Macro-chiasm detector** — book-level chiastic structure detection
      (e.g. Genesis 1–11, Isaiah) promoted to passage-level connections with
      labeled parallel sections
- [x] R3: **Covenant structure matcher** — matches covenant/treaty-structured
      passages (Sinai, Deuteronomy, Joshua 24) across the canon
- [x] R4: All three registered in `GENERATOR_DEFS` and covered by the existing
      parametrized generator tests

## Pre-resolved Decisions
- **Contract**: each generator is a module in `generators/passage/<name>.py`
  exposing `run(conn, book_ids=None) -> int` (rows created), registered in
  `generators/__init__.py` with `module_path: ".passage.<name>"`, `layer:
  "passage"`, `tier`/`cost` metadata — byte-for-byte the
  `theme_tracer.py`/`genre_tagger.py` pattern (they are the templates to copy).
- **Idempotency**: every generator upserts into `passage_connections` keyed on
  (source_ref, target_ref, type_name); re-runs are no-ops. Use the same
  INSERT OR IGNORE / conflict-target pattern as `theme_tracer.py`.
- **Quality**: confidence 0.4–0.6 for structural heuristics unless a strong
  signal (explicit quotation-level parallelism) exists; `discovery_method` =
  'algorithm'; all outputs visible in the passage API
  (`lib/api/passage.py::get_passage_connections` picks them up automatically —
  no API change needed).
- **Testing**: add each generator name to the parametrized
  `test_passage_generators_run` list in `tests/test_generators.py` (it
  iterates GENERATOR_DEFS for layer 'passage') + targeted assertion tests on a
  small temp DB.

## Track A: Narrative Parallel `[x]`
- Description: structural narrative parallelism across books.
- 📏 Scope: 2 files, ~160 lines

### Phase A1: Generator `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] Curate seed motif→narrative-arc map (birth/annunciation, deliverance,
      covenant ratification, theophany, journey/wilderness, judgment+restoration)
      as module constants
- [x] `generators/passage/narrative_parallel.py`: for each motif, find OT+NT
      narrative passages via theme_tracer-style entity/keyword overlap; connect
      passage pairs with type_name='narrative_parallel'
- [x] Register in GENERATOR_DEFS (copy theme_tracer's dict, swap fields)
- 📏 Scope: `generators/passage/narrative_parallel.py` ~130, `generators/__init__.py` +12
- ✅ Checkpoint: run emits rows for ≥4 motifs; Exodus 14 crossing ↔ Isa 43
      (or similar) pair present; re-run emits 0 new rows
- ⚙ Fallback: restrict motif matching to named-entity overlap (people/places)
      if keyword overlap is too broad — precision over recall

### Phase A2: Tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Add to `test_passage_generators_run`; one targeted test on a 3-book
      fixture asserting a known narrative_parallel edge
- 📏 Scope: `tests/test_generators.py` +35
- ✅ Checkpoint: `python3 -m pytest tests/test_generators.py -q` green
- ⚙ Fallback: none

## Track B: Macro-Chiasm `[x]`
- Description: book-level chiasm → labeled passage connections.
- 📏 Scope: 2 files, ~150 lines

### Phase B1: Generator `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] `generators/passage/macro_chiasm.py`: scan book structure for mirrored
      sections (reuse `lib/sod`/`scripts/chiasm_scan.py` logic at book level —
      section→section keyword-overlap mirroring, A B C C′ B′ A′ shape); emit
      passage_connections rows for each mirrored pair with type_name='macro_chiasm'
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `generators/passage/macro_chiasm.py` ~120, `generators/__init__.py` +12
- ✅ Checkpoint: known chiastic books (Genesis 1–11, Exodus 1–15, Isaiah
      1–12) produce mirrored-section rows; random non-chiastic book produces
      few/none
- ⚙ Fallback: promote only exact section-count matches (A1↔A2 sections with
      ≥3 shared rare lemmas) to keep false positives low

### Phase B2: Tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Add to `test_passage_generators_run`; targeted test on a small
      hand-built mirror fixture
- 📏 Scope: `tests/test_generators.py` +30
- ✅ Checkpoint: pytest green
- ⚙ Fallback: none

## Track C: Covenant Structure Matcher `[x]`
- Description: treaty/covenant-form passages matched across the canon.
- 📏 Scope: 2 files, ~150 lines

### Phase C1: Generator `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] Curate covenant-form sections (Sinai Exod 19–24, Deut 4–30, Josh 24,
      Neh 9, Jer 31 new-covenant, Matt 5–7 covenant-renewal framing) as seed
      passage ranges
- [x] `generators/passage/covenant_structure.py`: connect seed passages whose
      internal structure matches (preamble/stipulations/blessings-curses
      keyword sets); type_name='covenant_structure'
- [x] Register in GENERATOR_DEFS
- 📏 Scope: `generators/passage/covenant_structure.py` ~110, `generators/__init__.py` +12
- ✅ Checkpoint: Sinai ↔ Deuteronomy ↔ Joshua 24 edges present; Jeremiah 31 ↔
      Matthew covenant-renewal edge present
- ⚙ Fallback: pure curated-pair generation (no auto-discovery) if the
      structure-keyword match is unreliable — the seed list alone still adds
      value

### Phase C2: Tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Add to `test_passage_generators_run`; targeted fixture test
- 📏 Scope: `tests/test_generators.py` +30
- ✅ Checkpoint: pytest green
- ⚙ Fallback: none

## Track D: Rollup `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 5
- [x] Run all three on a temp DB + production DB (idempotent)
- [x] Update `docs/plans/passage-level-connections.md` Phase 2 checkboxes
- [x] Progress log `docs/plans/passage-discovery-generators-progress.md`
- ✅ Checkpoint: `sentrux check .` unchanged; connection counts positive;
      OpenAPI snapshot unaffected (no API changes)
- ⚙ Fallback: none

## Out of Scope
- Frontend work (Phase 3 of the parent plan — separate plan if wanted)
- New tables (all three write existing `passage_connections`)
- LLM-assisted detection (algorithmic only)
