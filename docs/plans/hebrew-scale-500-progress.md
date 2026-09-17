# Progress: Scale to 500+ words/roots + grammar tracks + tap feedback

## Session 2026-09-16
- Current track: A (Phase A1) then B (Phase B1, B2)
- [x] Plan created: docs/plans/hebrew-scale-500.md (4 tracks, 6 phases)
- [x] Track A Phase A1: tap feedback — HUD ring flash (green/red), Ohr+Kavod counter pops, study-to-tap hint (HebrewIdleBar.jsx +~25)
- [x] Track B Phase B1: deck pager — 10 decks of 50, due-first sort, mastered union across pages (WordTilesView.jsx +~80)
- [x] Track B Phase B2: tier levels — wordTier() + self-checks (idle-game.js +~25), seeder writes tier level, migrate_word_tiers.py applied: L4:68 L5:98 L6:147 L7:218 (18 rank-less stay L4)
- Tests: 236/236 idle-game self-checks ok; 25 backend hebrew tests pass; vite build green
- DB backup before migration: /tmp/memorize-backup-tiers.db
- Remaining: B3 staged gates + roots tiles + synergy; C grammar tracks; D minigames (future)

## Session 2026-09-16 (perf)
- Perf profiles done (2 subagents): frontend top costs = cytoscape x2 (~60% payload), dead d3 + 5x markdown, 1s IdleBar re-render + 60fps canvas, 696-row unmemoized list, 1000-row fetch waterfall, localStorage write amplification, chat per-token rerenders, Audio-per-event
- Backend top costs = 500MB startup cache, curriculum N+1 (0.69s/365KB), compute_learning_speed 3-4 scans/req, top-words LIKE scans x200, review-queue Python O(n^2), zero secondary indexes, review write fan-out, per-request DDL + self-HTTP
- Plan created: docs/plans/hebrew-performance.md (4 tracks: A backend quick wins, B structural, C payload, D runtime)
## Session 2026-09-16 (perf A1)
- [x] Track A Phase A1 done: ensure_hebrew_schema_once() (short-circuits on sqlite_master index check), 4 hot indexes created, 13 request sites consolidated, _ensure_gamification_table delegates (kills 6x conn cycle/review), verb-drill self-HTTP replaced with direct builder call, lifespan hook
- Fix during verify: read_hebrew_prefs + _placement_apply_results take conn param (tmp-DB tests) — threaded through
- Measured: curriculum 0.69s -> 0.363s, review-queue 0.039s, top-words+status 0.284s/50 (LIKE scans remain -> A2); EXPLAIN shows index seeks, no temp B-trees
- Tests: 46 passed (incl. anki_parity tmp-DB tests)
- Net: web/routes/hebrew.py +~120/-60, web/server.py +7

## Session 2026-09-16 (perf rest: A2 B1 B2 C1 D1 D2)
- [x] A2: hebrew_node_map (cached till lesson count changes, LIKE fallback), top-words 2 batched queries (280ms -> 6ms), compute_learning_speed 60s memo
- [x] B1: curriculum 1 batched prereq query (697 -> 3 queries; 363ms -> 145ms), conn reuse for confusability, review-queue due<=now SQL pushdown, _interleave_due_items O(n^2)->O(n) (taken-set + presort, same order), warnings reverse-index
- [x] B2: fire_process visited+depth6+weight floor, FIRe credit SELECT IN + executemany, exactly-1 _check_badges/review (check_badges flag), SKIP_RAM_CACHE alias (SCRIPTURE_WORKERS=0 existed)
- [x] C1: manualChunks cytoscape (443KB) + markdown (338KB) lazy, ConnectionGraph lazy/Suspense, d3 uninstalled; wrapper refactor deferred (chunks dedup already)
- [x] D1: ticker skips empty commits + hidden-tab pause, canvas IO/visibility pause + mobile 22-golem cap, saveSoon 2s trailing + pagehide flush, analytics 10s write batch (fixed reentrancy bug, self-checks pass)
- [x] D2: LessonRow memo + filtered/byLevel useMemo, top-500 lazy (>=5 letters or roots), audio-pool singleton (IdleBar wired), chat recovery backoff 3s->60s; deferred: bootstrap endpoint, chat virtualization, rewiring all audio sites
- Final: 236 idle self-checks + 5 analytics self-checks ok; 54 backend tests pass; vite build green
- Measured (direct): top-words+status 6ms, curriculum 145ms (baseline doc 690ms), review-queue 13ms

## Session 2026-09-16 (leftovers: perf deferred + scale B3/C)
- [x] Markdown wrapper: ScriptureMarkdown in lib/scripture-markdown.jsx, 6 consumers migrated, vendor imports in exactly one file; DailyVerse dead imports removed
- [x] Bootstrap: GET /api/v1/hebrew/bootstrap (curriculum+gamification+prefs+queue, 0.2s single trip) + LearnView wiring with legacy fallback
- [x] Chat: 30-message history window + show-earlier button (indices absolute, all actions safe), recovery backoff kept
- [x] Audio: AnkiReview/CardRenderer/HebrewPassageReader-words/PassageReader-fallback on pool cache; WordPopup + verse-slice paths keep elements (pause/seek semantics) — documented
- [x] Scale B3: deck gates (3+→10, 6+→40 mastered), Roots Tiles (kind=roots, example-based status, Know/Skip reps, 25-mastered gate), word↔root synergy live
- [x] Scale C: derived tracks (no migration), Tracks tab 3×5 grid with click-through + backlog cells, +5%/tier (cap 50%) threaded + 📜 chip
- Deviations: gates use mastered (not known 200/350 — no extra 500-row fetch); roots mature by reps (only 17/500 have FSRS nodes)
- Verify: 251 idle + 5 analytics self-checks ok; 54 backend tests pass; vite build green
- Fixed en route: analytics node-path O(n²) hang (buffer-until-read), LessonRow extraction revert+redo
- Still future (Track D): minigames (Root Garden first) — explicitly not started
- Context: Anki 26.08.1 verified (/usr/bin/anki); Shemen=milk already shipped; prior work: WordTilesView + top-words with_status + word->letter bonus (net backend +69, idle-game +90, WordTilesView +230)
- Tests baseline: 21 backend hebrew tests pass; vite build green
