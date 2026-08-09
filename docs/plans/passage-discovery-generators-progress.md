# Progress: Passage Discovery Generators (Phase 2)

## Session 2026-08-05 (implemented)

All three Phase-2 discovery generators built, registered, and verified. See
`docs/plans/passage-discovery-generators.md` (status: completed).

### What was built
- `generators/passage/_common.py` — shared helpers (keyword scan, passage
  clustering, idempotent `passage_connections` upsert, single-verse passage
  promotion) so discovery generators stay thin.
- `generators/passage/narrative_parallel.py` — 7 narrative motifs
  (birth/annunciation, deliverance/crossing, covenant ratification,
  theophany, wilderness journey, judgment/restoration, calling/commission);
  connects same-motif passages across books (type `narrative_parallel`).
- `generators/passage/macro_chiasm.py` — book-level mirror detection: per-book
  chapter signatures (rare words, stoplist filtered), symmetric-pair overlap vs
  book baseline; emits labeled `macro_chiasm` edges only when the mirror signal
  clearly beats the book's own cross-pair average.
- `generators/passage/covenant_structure.py` — 8 curated covenant-form
  passages scored against 5 treaty-element keyword sets (preamble,
  stipulations, blessings, curses, witnesses); connects passages sharing ≥2
  elements (`covenant_structure`).
- All registered in `GENERATOR_DEFS` (generators/__init__.py, "Passage —"
  names so the parametrized test picks them up) and imported in
  `generators/passage/__init__.py` (with `__all__`).

### Real-data output (run on a copy of data/processed/scripture.db)
| Generator | rows | notes |
|---|---|---|
| narrative_parallel | 32,915 | idempotent (run2 = 0) |
| macro_chiasm | 299 | conservative — only clear mirror signals |
| covenant_structure | 7 | e.g. Sinai (exo.19.1-24.18) ↔ Sermon on the Mount (matt.5.1-7.29) |

### Fixes found during verification
- `covenant_structure` originally used `id BETWEEN start AND end` — lexically
  wrong for multi-digit chapters (deu.4.1 > deu.30.20 lexically → 0 rows).
  Rewrote `_passage_text` with book/chapter/verse arithmetic.
- `interpretation_network` (macro plan, but shares the upsert path) had a
  running cap that broke idempotency — resolved by passage-level aggregation
  + sorted iteration (see macro progress log).

### Verification
- `python3 -m pytest tests/test_generators.py -q` → 29 passed (parametrized
  list auto-includes the new "Passage —" generators; empty-fixture runs are
  graceful).
- ruff clean on all new files (pre-existing violations in older generators
  untouched).
- `sentrux check .` → same 3 pre-existing violations, no new.
- Production DB untouched during verification (temp copy only); live ingest is
  part of the rollup.

### Net file changes
- New: `generators/passage/_common.py`, `narrative_parallel.py`,
  `macro_chiasm.py`, `covenant_structure.py` (+~460 lines)
- Modified: `generators/__init__.py` (+3 registrations),
  `generators/passage/__init__.py` (+35), this log, plan doc (checkboxes →
  completed)
