---
status: completed
kind: plan
area: hebrew-performance
author: james
created: 2026-09-16
---

# Project: Game performance — faster, fewer resources

Goal: halve backend p95 on Hebrew routes, halve frontend JS payload, cut idle CPU (ticker + canvas).

## Requirements
- [ ] R1: No behavior change — same FSRS intervals, same Ohr math, same unlocks
- [ ] R2: Backend p95 < 350ms on curriculum / review-queue / top-words+status (baseline: curriculum 0.69s/365KB)
- [ ] R3: Initial JS payload < 500KB gzipped (baseline: ~1.3MB across 3 chunks, cytoscape x2)
- [ ] R4: Idle tab CPU near-zero (ticker + canvas gated)
- [ ] R5: Every change measured before/after (ab + self-checks + build)

## Pre-resolved Decisions
- Current DB is tiny (25 progress rows) — costs are latent. Optimize by measurement, index first, no caching layer (no redis).
- SQLite: add indexes via one migration at startup, never per-request DDL.
- Frontend: `React.lazy` + `manualChunks` for cytoscape/markdown; no new deps except `react-virtuoso` OR collapse-levels fallback (decide in C2).
- Startup 500MB RAM cache: trim columns first (no architecture change); worker/mmap only if RSS still hurts.
- `d3` is unused — safe to delete after `npm why d3` confirms no transitive peer.

## Track A: Backend quick wins (hours, no risk) `[x]`
- Description: indexes + ensure-once + LIKE-map + speed-cache. Biggest ms-per-line in the repo.
- Scope: 2 files (hebrew.py, one migration), ~80 lines

### Phase A1: Indexes + ensure-once `[x]`
- Priority: high
- [x] Migration (startup, once): `idx_hebrew_progress_user_practiced(user_id,last_practiced)`, `idx_review_state_user_due(user_id,due)`, `idx_review_state_user_node(user_id,node_id)`, `idx_lessons_node(node_id)`
- [x] Move all `_ensure_*` DDL out of request path (run at startup/migration): review_state, progress_source, gamification x4-5, attempt_events, analytics
- [x] Replace self-HTTP `update_hebrew_progress → verb-drill` with direct function call
- Scope: ~40 lines
- Checkpoint: `EXPLAIN QUERY PLAN` shows index use on review-queue ORDER BY + state lookups; `ab -n 100` curriculum p95 down
- Fallback: keep per-request DDL (correct, just slow)
- Depends on: nothing

### Phase A2: Kill the LIKE scans + speed recompute `[x]`
- Priority: high
- [x] Build `hebrew_text -> node_id` map once (parse lesson `content_json.hebrew/glyph` at startup, refresh on seed); `resolve_hebrew_node` becomes dict lookup
- [x] `top-words?with_status=1`: 2 batched queries (`WHERE node_id IN`) instead of ~200 LIKE scans
- [x] Memoize `compute_learning_speed` per user_id with TTL; invalidate on progress/review write; single-SQL rollup
- Scope: ~60 lines
- Checkpoint: `ab -n 100 top-words?limit=50&with_status=1` p95 < 200ms; review POST p95 down
- Fallback: LIKE path stays as fallback when map misses
- Depends on: A1

## Track B: Backend structural (days, measured) `[x]`
- Description: curriculum N+1, review-queue pushdown, single-conn review writes, startup trim.
- Scope: 2 files, ~200 lines

### Phase B1: Curriculum + review-queue `[x]`
- Priority: high
- [x] Curriculum: one batched prereq query (`WHERE target_id IN` + group in Python) instead of 697 queries; move confusable reorder to build-time; paginate (`limit/offset/category`)
- [x] Review-queue: push `due<=now` into SQL, parse dates once, `set` for taken ids, slice to `limit` BEFORE interleave/compress
- Scope: ~120 lines
- Checkpoint: curriculum p95 < 350ms at 696 nodes; payload < 365KB via pagination
- Fallback: current queries (correct under small N)
- Depends on: A1

### Phase B2: Review write path + startup `[x]`
- Priority: medium
- [x] One connection/transaction per review; single `_check_badges` call; iterative FIRe with `visited` set; batch `seen_connections` insert
- [x] Startup cache: SELECT needed columns only; lazy-load `connections_json/gematria_json`; `SKIP_RAM_CACHE` for tests
- Scope: ~80 lines
- Checkpoint: review POST p95 down; `time uvicorn` startup + RSS down
- Fallback: current multi-conn path
- Depends on: A2

## Track C: Frontend payload (hours) `[x]`
- Description: cytoscape x2 + d3 + 5x markdown -> lazy chunks.
- Scope: vite.config + 6 components, ~40 lines

### Phase C1: Split the vendors `[x]`
- Priority: high
- [x] `manualChunks: {cytoscape, markdown}`; `lazy()` ConnectionGraph + KnowledgeGraphView (load on tab open)
- [x] Single `ScriptureMarkdown` wrapper in lib/scripture-markdown.jsx — all 6 consumers migrated, vendor imports live in one file; lazy markdown in LearnView/CardRenderer/VerbDrill
- [x] `npm uninstall d3` (after `npm why d3`)
- Scope: ~40 lines
- Checkpoint: initial JS < 500KB gzip (vite-bundle-visualizer before/after)
- Fallback: current eager bundle
- Depends on: nothing

## Track D: Frontend runtime (hours-days) `[x]`
- Description: ticker, lists, fetches, storage, audio.
- Scope: ~6 files, ~150 lines

### Phase D1: Ticker + canvas + storage `[x]`
- Priority: high
- [x] Tick 5s (ohr in ref, throttled display) (done as skip-empty-commit + hidden-tab pause — timing semantics preserved) OR skip commit when gain==0; split HudRow/ShopList/QuestList + `memo()`
- [x] GolemCanvas: `IntersectionObserver` + `visibilitychange` pause; cap 20 golems mobile
- [x] Debounce `saveIdleState` 15-30s (2s trailing on answers; purchases immediate) + `pagehide`; analytics buffer + 1x/10s batch
- Scope: ~80 lines
- Checkpoint: React Profiler idle commits down 5x; localStorage writes down 10x
- Fallback: 1s ticker (current)
- Depends on: nothing

### Phase D2: Lists + fetches + audio `[x]`
- Priority: medium
- [x] `useMemo(filtered/byLevel/nextLesson)` + `memo(LessonRow)`; virtualize 696-row list OR collapse levels (`<details>`)
- [x] Single `/hebrew/bootstrap` (curriculum+gamification+prefs+queue, one round trip) + LearnView wiring with legacy fallback (curriculum+gamification+prefs+queue); lazy top-500 only for word/root quizzes; `memo(MessageBubble)` + backoff recovery poll
- [x] Singleton Audio pool + URL map; `width/height + decoding=async` on imgs
- Scope: ~70 lines
- Checkpoint: LearnView render < 100ms; chat stream without full-list rerender
- Fallback: current lists/fetches
- Depends on: C1 (chunk split first so lazy wrappers land in right chunks)
