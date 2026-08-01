# Progress: Biblical Hebrew learning content overhaul

## Session 2026-08-01 (lexicon frequencies)

- Rebuilt lexicon frequency fields from exact OT lemma aggregates
  (scripts/rebuild_lexicon_frequencies.py): 8,632 canonical Strong's bases,
  25,732 lexicon rows updated so prefixed raw forms and H rows share the true
  base count (e.g. H3605 כל = 5,413 tokens; H3068 יהוה = 6,521).
- Made vocabulary selection and alignment identity-stable: get_top_words now
  selects one citation form per Hebrew surface (non-prefixed rows only) ordered
  by true frequency; align matches existing lessons by unpointed surface first,
  then (language, Strong's base), so ranking changes never renumber node IDs.
- /api/v1/vocabulary now returns lemma + language and excludes prefixed raw rows.
- Result: 478/500 existing lessons re-aligned, 500 alignment rows, validator
  passes, align idempotent; 22 top-frequency words (שבת, קהל, רעב, …) surfaced
  by the corrected ranking have no lesson yet (seeding gap, out of scope here).
- Verification: 36 Hebrew backend tests pass; ruff + diff clean.

## Session 2026-08-01 (final follow-ups)

- Repaired five legacy vocabulary lessons corrupted by the old numeric-key lexicon
  (vocab_אבדה_276, vocab_יואב_251, vocab_מקים_89, vocab_מלכו_187, vocab_אביו_24):
  descriptions now cite the authoritative Strong's entry and roots are corrected
  (e.g. אָבַד root אבד, אָב root אב). Script: scripts/repair_vocabulary_metadata.py,
  wired into seed_hebrew_all.sh after alignment; idempotent.
- review-queue now returns a `language` field so Aramaic due cards stay labeled.
- Generalized Hebrew DB test isolation: any test whose node id or class name
  contains "hebrew" gets an isolated memorize.db copy.
- Verification: 131 backend tests pass (chat/graph streaming tests are pre-existing
  slow real-LLM tests and were deselected); 94 frontend unit tests + production
  build pass; live DB hebrew-table hash unchanged across all test runs; critic PASS.

## Session 2026-08-01 (continuation)

- Replaced substring vocabulary examples with exact OSHB OT token/lemma alignment
  for all 500 generated lessons (495 Hebrew + 5 Aramaic), with token-position
  cloze, provenance, source version, and attestations.
- Corrected the five Aramaic lexemes: citation forms (דִּי, מֶלֶךְ, אֱלָהּ, הָוָא,
  דֵּן), glosses, descriptions, transliterations, and regenerated practice with
  no stale "Daniel"/"clay" answers.
- Stored cloze/recall/typing answers as unpointed consonant skeletons (the UI has
  no niqqud entry); choice questions keep pointed options, preserving shin/sin and
  dagesh distinctions.
- Replaced the reconstructed "FSRS" with a persisted adaptive scheduler:
  `hebrew_review_state` table, POST review route, atomic BEGIN IMMEDIATE handling
  (8 concurrent reviews → reps=8, no lost updates), unknown-node rejection.
- Added nine advanced reading units: I-Yod/Waw, I-Aleph, III-Aleph, doubly weak
  verbs, weqatal discourse, poetic parallelism, legal and prophetic formulae, and
  the Biblical Aramaic boundary — all with learner-visible attestations.
- Isolated all Hebrew API tests from the live database via `MEMORIZE_DB_PATH`
  support and a per-class copied template; live DB fingerprint unchanged by tests.
- Frontend review action now reads the persisted due queue (falls back to unlocked
  nodes); Aramaic language label flows through curriculum API and card factory.
- Verification: 33 backend tests + 4 frontend grading tests pass; validator passes
  on the live DB; independent critic PASS.

## Session 2026-07-31

- Audited all 671 existing lessons, 4,622 practice items, progression routes,
  frontend learning surfaces, seeders, and related tests.
- Researched permissibly usable Hebrew Bible corpora, morphology, grammar,
  Unicode/RTL requirements, and evidence-based learning methods.
- Corrected foundational linguistic errors and added six Masoretic reading units.
- Repaired objective lesson grading, diagnostic placement, quiz timing/results,
  keyboard input, review cards, vocabulary/audio responses, and verse reading.
- Standardized prerequisite edges as prerequisite → dependent.
- Added an idempotent repair/validation pipeline; the cleaned live DB now has
  677 nodes, 677 lessons, and validated practice with no DSS references,
  contradictory answers, duplicate options, dangling edges, or reversed base edges.
- Added server-issued, single-use, atomically claimed diagnostic batches; answers
  are graded server-side and only tested nodes receive placement credit.
- Verification: 5 focused Python tests passed; 93 frontend unit tests passed;
  frontend build passed; two complete temp-DB seed runs produced identical
  logical rows, lesson versions, and timestamps; independent critic PASS.

## Remaining phases

- Seed the ~22 newly-surfaced high-frequency vocabulary words that the corrected
  ranking now includes (שבת, קהל, רעב, עור, קצה, עמוד, …); keep identity keyed by
  surface, not rank index.
- Reingest pinned OSHB XML to restore maqqef and exact separators.
- Isolate the memorize interleaved route (memorize.py) and add authenticated
  user ownership to review endpoints; the current `default` user remains shared.
- Add a review-queue `language` assertion to tests.
