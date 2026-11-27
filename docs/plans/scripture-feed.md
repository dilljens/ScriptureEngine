---
status: active
kind: plan
area: feed
author: dillon
created: 2026-11-26
---

# Project: Scripture Feed (Devote-style verse feed on open-source ranking)

Goal: Ship a Devote-like swipeable scripture-verse feed ranked by an open-source, explainable algorithm adapted to ScriptureEngine's graph.

## Requirements
- [ ] R1: Infinite/swipeable feed of verse cards (English + Hebrew/Greek where available, audio, share, save)
- [ ] R2: Ranking uses a named open-source algorithm (Reddit Hot + Wilson score, HN gravity as documented alternative) — no black-box ranker
- [ ] R3: Every card explains "why this verse" (top scoring signals + connection reason)
- [ ] R4: Topic/mood filters + Daily verse pinned + canon-scope selector (canon-only default, opt-in outside-canon modes)
- [ ] R9: Subreddit-equivalents (`r/` communities): general scroll (all units, hot) + per-community scroll (same ranker, scoped). Reddit/X look: vote arrows, comment counts, sort tabs (hot/top/new/controversial/best), sidebar + community header
- [ ] R10: Posts + comments on verse-units and per community (reuse forum auth rule: author resolved server-side). No LLM needed for v1 categorization — derive communities from existing graph data
- [ ] R5: Feedback loop (like / save / skip / dwell) improves future ranking per-user, with cold-start defaults
- [ ] R6: Diversity + freshness (no repeat within N days, MMR de-dup of near-duplicate pericopes)
- [ ] R7: Performance: p95 feed page < 300ms on SQLite via precompute + query cache; works offline-ish via prefetch
- [ ] R8: Anti-gaming / pastoral guardrails: quality-calibrated connections only, tradition labels, no engagement-bait theology

## Pre-resolved Decisions
- Architecture: `lib/api/feed.py` (pure scoring) + `web/routes/feed.py` (HTTP) + `FeedView.jsx`/`FeedCard.jsx` (frontend). Scoring is a pure function `score(item, now)` so it is unit-testable without DB.
- Algorithm: Reddit "hot" (open-source, Apache-licensed `hot.py`: `log10(max(|ups-downs|,1)) + sign*y*t/45000`) for time-decayed engagement + Wilson score lower bound (open, standard statistics) for quality confidence + HN gravity `score/(age_hours+2)^1.8` as fallback/exploration comparator. All three are public, citable, reimplementable in stdlib `math`.
- Signals mapped to votes: `ups` = saves+likes+long-dwells+shares, `downs` = skips/hides; `n` for Wilson = total ratings; base quality prior from graph: `log(1+connections)`, quality-star weight, entity richness, truth/consensus agreement. Time base = first-published/lectionary date, not row creation, so ancient verses don't all decay to zero.
- Personalization: explicit topic/book affinity (Laplace-smoothed) × implicit embedding-free keyword overlap — NO new ML dep, no transformer at request time. Keeps stdlib-only scoring.
- Diversity: Maximal Marginal Relevance (MMR, open published algorithm, Carbonell & Goldstein 1998) with λ=0.7 to penalize same-book / same-entity / same-pericope runs.
- Tools: no new deps. Python stdlib `math`, existing SQLite FTS5 + `lib/api/query_cache.py`, existing `verse.py`/`graph.py` lookups. Frontend reuses `VerseBlock.jsx`, `VerseAudioPlayer.jsx`, `DailyVerse.jsx` patterns.
- Canon scope: default `canon` = ot/nt/bom/dc/pgp (Devote-safe). Outside-canon works come from existing `works` table (apoc, dss, pseu/pseudepigrapha, expanded, josephus, philo, hellenistic_jewish, ane_texts, targums, mishnah, nag_hammadi, ugaritic_texts, etc.) and are strictly opt-in via `canon_mode` + `works=` allowlist. Every outside-canon card carries `work`, `canon_status` badge and tradition label.
- Error handling: feed endpoint never 500s on empty signals — falls back to deterministic daily-seed shuffle of lectionary/top-centrality verses; logs `feed_fallback` structured event.
- Testing: `pytest` unit tests for hot/wilson/gravity math (golden values from Reddit/HN reference), integration test for `/api/v1/feed`, Playwright smoke for swipe/next/save.
- Rollout: read-only GET first, feedback POST behind existing auth/session token; precompute job via `scripts/` + `schedule.yaml` tier, not a migration.

## Out-of-scope (anti-scope)
- NOT a social graph (no follows, no comments, no DMs)
- NOT LLM-generated devotionals at request time (reflection prompts come from curated template bank + verse metadata; LLM devotionals are a later track)
- NOT push notifications / streak emails in v1 (streak counter only, local + memorize.db)
- NOT retraining embeddings or changing connection quality calibration

## Open Questions → Assumed Answers (confirm in review)
- Q: Which "Devote" exactly? → A: assumed Devote = daily-verse-card + devotional + streaks + share-image app (Bible.YouVersion-adjacent). Plan clones: card, topic/mood chips, reflection prompt, share, save, streak. If different app, swap card fields, ranking unchanged.
- Q: Per-user accounts? → A: assumed existing session-token/auth (`currentSessionToken`, memorize.db) is enough; anonymous gets deterministic device-seed feed.
- Q: Canon scope? → A: default OT/NT/BoM/D&C/PGP (Devote-safe). Outside-canon is opt-in — see Canon-scope options below. No auto-mixing of DSS/Apocrypha/Pseudepigrapha/Nag Hammadi into the default feed.

## Canon-scope options (outside-canon verses)
Pick one default + ship the others as settings. Recommended: Option 2 as default UX with Option 5 per-work toggles.

- **Option 1 — Canon-only (default):** `canon_mode=canon`. Only ot/nt/bom/dc/pgp. Safest Devote parity, no badges needed.
- **Option 2 — Blended with cap (recommended opt-in):** `canon_mode=blend&outside_ratio=0.2`. Max ~1 in 5 cards from outside canon, MMR-spread, each card badged (e.g. `Apocrypha · 1 Enoch`, `DSS · 1QS`). Respects `works=` allowlist. Best discovery without overwhelming canon readers.
- **Option 3 — Deuterocanon-only expansion:** `canon_mode=deutero`. Canon + apoc only. For Catholic/Orthodox-leaning users; no DSS/Pseudepigrapha/scholar texts.
- **Option 4 — Scholar lane (separate section):** canon feed stays pure; a second `Beyond the canon` horizontal lane/section shows dss/targums/josephus/philo/nag_hammadi/ane_texts as context cards (visually distinct, "context — not canon" copy). Zero ranking contamination.
- **Option 5 — Per-work toggles (settings, persisted per user_key):** checklist of all 19 `works` rows; `works=apoc,dss,pseu,expanded` etc. Stored in settings; anonymous = device_seed + localStorage. Finest control, slightly more UI.
- **Option 6 — Topic-gated cameo:** outside-canon appears only when topic/mood matches (e.g. prophecy → 1 Enoch, wisdom → Sirach/Wisdom, temple → DSS Community Rule). Conservative, high-relevance.
- Guardrails for all outside modes: `canon_status` badge required, tradition/scholar attribution (`get_sources_for_verse`), low-quality `suggested`-only fragments excluded from top-10, daily-verse pinned card stays canon unless user explicitly opts véhiculum.

## Track A: Ranking engine (open-source algorithm port) ` [ ]`
- Description: Pure-function port of Reddit Hot + Wilson + HN gravity, mapped to scripture signals, with golden tests.
- 📏 Scope: ~3 files, ~400-600 lines (new `lib/api/feed.py`, tests, script)

### Phase A1: Signal inventory + scoring spec `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] Inventory signals available per verse: connections count by layer/quality, entity count, gematria presence, word count, versions, TSK count, consensus/tradition count
- [ ] Define `ups/downs/n` mapping + quality prior formula + time-base rule (publish/lectionary date) + decay constants (45000s hot, 1.8 gravity)
- [ ] Write worked examples (e.g. john.3.16 vs isa.53.5 vs obscure genealogy verse) showing expected order
- [ ] Cite sources in code comments: reddit `hot.py`, Wilson (1927), HN `arc` ranking, MMR paper
- 📏 Scope: ~1 file spec (~150 lines in findings)
- ✅ Checkpoint: `findings` section reviewed; 3 worked examples hand-computed and agreed
- ⚙ Fallback: if signal inventory blocked, use connections_count-only prior and document gap
- Depends on: nothing

### Phase A2: Implement `lib/api/feed.py` pure functions `[ ]`
- [ ] `hot_score(ups, downs, epoch_sec)` — byte-identical to Reddit open-source formula
- [ ] `wilson_lower_bound(pos, n, z=1.96)` — stdlib math only
- [ ] `hn_score(points, age_hours, gravity=1.8)` — comparator
- [ ] `base_quality(verse_meta)` — log-centrality + star-weight + entity richness + consensus
- [ ] `rank_score(...)` — combines hot/wilson/quality/affinity/recency + MMR penalty; deterministic with seed
- [ ] Golden unit tests with Reddit/HN reference values (e.g. known hot ordering, Wilson edge cases n=0, unanimous)
- 📏 Scope: ~2 files, ~350 lines + ~200 test lines
- ✅ Checkpoint: `pytest tests/test_feed_ranking.py -q` green + `ruff check lib/api/feed.py`
- ⚙ Fallback: if Wilson over-conservative on low-n, back off to Laplace-smoothed mean and flag in findings
- Depends on: A1

### Phase A3: Personalization + diversity + precompute `[ ]`
- [ ] Affinity vector: topic/book/entity Laplace smoothing from `feed_interactions` (likes/saves/dwells/skips)
- [ ] MMR pass: penalize same-book/entity/pericope within window (λ=0.7, window=20)
- [ ] Freshness: exclude seen verse_ids within N=14 days per user/device; deterministic daily seed for anon
- [ ] Precompute script `scripts/build_feed_index.py` + `schedule.yaml` tier (daily lightweight) writing `feed_scores` cache table or query-cache entries
- [ ] Cold-start: lectionary + top-centrality + topic-balanced shuffle when no history
- 📏 Scope: ~2 files, ~250 lines
- ✅ Checkpoint: `python3 scripts/build_feed_index.py --limit 500` succeeds; spot-check diversity (no 3 same-book in a row in top 20)
- ⚙ Fallback: precompute optional in v1 — endpoint can compute top-K on the fly from materialized `passage_guides` + cache
- Depends on: A2

## Track B: Verse-card content pipeline (Devote-style cards) `[ ]`
- Description: Curated FeedUnit cards (1–3 verses that form one thought) — text, reflection prompt, topic tags, why-this-unit, share text. Single verses only when the thought is complete; passages when the idea flows across verses.
- 📏 Scope: ~4 files, ~450-650 lines

### Phase B1: Card schema + topic/mood taxonomy `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [ ] Define `FeedUnit` schema: unit_id, verses[1..3] (each: verse_id, reference, text_en/he/gr, transliteration, audio_url), span_ref (e.g. `john.1.1-3`), topics[], mood[], reflection_prompt, why_this_unit[], connections_preview (3), share_text, **work, canon_status (`canon`/`apocrypha`/`dss`/`pseudepigrapha`/`expanded`/`scholar`), tradition_label, unit_reason (`complete_thought`/`parallelism`/`chiasm`/`chain`/`argument`/`narrative**)
- [ ] Single-vs-span rule: default 1 verse; expand to 2–3 only when coherence gain clears threshold (see Phase B3). Never merge across chapters or works (canon + outside-canon never mix in one card).
- [ ] Topic/mood taxonomy (12 topics × 8 moods) mapped to existing entities + keywords + books. **No LLM over 70k verses for v1 — derive from 87k `verse_entities` rows + 559 entities + 88 `symbols` + 41 `thematic_clusters` (366 members) + `passage_genres` + TG/GS/BD footnote categories. LLM only as offline backfill for names/descriptions, human-reviewed, cached.**
- [ ] Reflection prompt bank: ~5 templates × topic (curated, pastoral, non-denominational-plus-tradition-label), no LLM at request time
- [ ] "Why this verse" renderer: top-2 signals in plain language ("Loved by 200 savers · Deeply connected (42 cross-refs) · Matches your interest in Isaiah")
- 📏 Scope: ~2 files, ~200 lines + prompt bank JSON (~100 lines)
- ✅ Checkpoint: schema JSON example for 3 verses (one OT, one NT, one BoM) validates
- ⚙ Fallback: if taxonomy mapping stalls, ship with 6 topics only and document remainder as follow-up
- Depends on: nothing (reads A1 signal list when ready, but not blocked)

### Phase B2: Card builder on top of existing verse APIs `[ ]`
- [ ] `build_card(conn, verse_id, user_ctx)` reusing `lookup_verse` + `graph_reachable(1-hop, 3)` + `get_sources_for_verse` — no N+1 (batch via `lookup_verses`)
- [ ] Audio: reuse read-along/schmueloff URL logic from `DailyVerse.jsx` (`/api/v1/read-along/{id}`)
- [ ] Share text + share-image payload (verse + reference + deep link), save/bookmark write path
- [ ] Tests: card builder returns all required fields for verses with and without Hebrew/Greek
- 📏 Scope: ~2 files, ~250 lines + tests
- ✅ Checkpoint: `pytest tests/test_feed_cards.py -q` green; manual `tools/verse.py` parity for 5 verses
- ⚙ Fallback: if audio missing, card omits audio button (same as DailyVerse fallback to TTS client-side)
- Depends on: B1, A2 (for why-this-verse signals; stub with placeholder until A2 lands)

### Phase B3: Thought-unit sizing (1 vs 2–3 verses) `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] Rank anchors with Track A, then decide span per anchor: score candidate windows {1}, {1-2}, {1-3} in same chapter/same work only; pick smallest span whose coherence gain clears threshold, cap 3 (4 only to complete a chiasm/parallelism already open)
- [ ] Coherence signals (all already in DB, stdlib math only): word overlap Jaccard/cosine on English tokens; shared-entity overlap via `verse_entities`/`entity_cooccurrence`; connection density via `connections` 1-hop + `passage_connections` span overlap; membership in `patterns` (`staircase_chain`), intra-verse `parallel_synonymous/antithetic/synthetic` pairs, `known_chiasms` spans; genre prior from `passage_genres` (genealogy/lists → collapse to 1 representative + `read chapter` link; prayer/proverb/beatitude → 1; narrative/argument/discourse → allow 2–3)
- [ ] Boundary algorithm: open-source TextTiling (Hearst 1997, public algorithm — token-sequence gap + depth-score cut) lite-port over the ±2 verse window; hard stops at chapter boundary, work boundary, genre change (e.g. genealogy → narrative), and speaker/discourse shift (heuristic: colon/quote + entity change)
- [ ] `unit_reason` + `why_grouped` line required on every span (e.g. `parallelism: v2 restates v1` / `chain: staircase repetition of 'righteousness'` / `argument: v3 completes the `if…then` in v1–2`); single-verse cards get `complete_thought`
- [ ] Tests: golden spans (john.1.1-3 stays together as prologue; ps.23.1 stands alone; isa.1.7-9 chain groups; a genealogy chapter collapses to 1 + link); assert no cross-chapter/work spans, max length honored
- 📏 Scope: ~2 files, ~200 lines (`lib/api/feed_units.py` + tests)
- ✅ Checkpoint: `pytest tests/test_feed_units.py -q` green; spot-check 20 anchors — zero broken thoughts, zero cross-chapter spans
- ⚙ Fallback: if TextTiling port stalls, ship rule-only version (parallelism/chiasm/chain + genre caps) and add lexical cohesion as fast-follow
- Depends on: A2, B1

## Track C: Feed API + Frontend UI `[ ]`
- Description: `GET /api/v1/feed`, `POST /api/v1/feed/interact`, `FeedView` swipeable UI reusing VerseBlock.
- 📏 Scope: ~5 files, ~600-800 lines

### Phase C1: Feed API routes `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] `GET /api/v1/feed?topic=&mood=&work=&limit=20&cursor=` → ranked **units (1–3 verses)** + `next_cursor` + `debug_scores?`` (scores only with flag, never by default). Add `canon_mode=canon|blend|deutero|all` + `works=` allowlist (validated against `works` table) + `outside_ratio` (default 0.2, max 0.5). Reject unknown works with 400 + valid list; unknown combo falls back to `canon` + log.
- [ ] `POST /api/v1/feed/interact` {verse_id, action: like/save/skip/share/dwell_ms, device_seed} → append to `feed_interactions`, update affinity incrementally
- [ ] `GET /api/v1/feed/daily` → deterministic verse-of-day pinned card (compat with existing `/api/v1/verse-of-day`)
- [ ] SQLite tables: `feed_interactions(user_key, verse_id, action, dwell_ms, created_at)` + `feed_scores_cache` (or reuse query_cache); migration script idempotent
- [ ] Rate-limit interact (e.g. 120/min/device) + validate verse_id format; never 500 on bad cursor (reset to head + log)
- 📏 Scope: ~3 files, ~350 lines
- ✅ Checkpoint: `curl /api/v1/feed?limit=5` returns 5 cards <300ms p95 locally; `pytest tests/test_feed_api.py -q` green
- ⚙ Fallback: if migration blocked, store interactions in existing `memorize.db` key-value/conversation table and document
- Depends on: A2, B2

### Phase C2: Frontend FeedView (Devote-like) `[ ]`
- [x] `ScrollView.jsx` shipped as stub singleton tab replacing Learn's slot (bottom nav `Scroll 📜`, `openScrollTab`, command `scroll` + legacy `learn` alias; Learn demoted to More menu, old `learn` tabs still render). Stub reads `GET /api/v1/feed` when live, falls back to verse-of-day card.
- [ ] Ranked units, vote wiring to Hot/Wilson, canon-scope selector + per-work settings sheet, prefetch + offline cache
- [ ] `FeedCard.jsx`: verse text, ref deep-link (`scripture-navigate`), Hebrew/Greek toggle, transliteration, audio play, why-this-verse expander, reflection prompt, like/save/share/skip buttons, streak counter
- [ ] Reuse `VerseBlock`, `VerseAudioPlayer`, `RatingButtons` styles; dark mode + mobile bottom nav safe; `prefers-reduced-motion` respected
- [ ] Prefetch next 5, cache in `frontend/src/cache.js`; offline-tolerant (stale cards render with badge)
- [ ] Playwright smoke: open feed, next, save, filter by topic, reload persists position
- 📏 Scope: ~3 files, ~400 lines
- ✅ Checkpoint: `npm run build` (frontend) green + Playwright feed spec passes
- ⚙ Fallback: if swipe gestures stall, ship button/tap Next-prev only and add swipe as fast-follow
- Depends on: C1

### Phase C3: Streaks, share, quality gates `[ ]`
- [ ] Streak counter (days visited feed, Amulet-style break — no streak anxiety copy) stored per user_key
- [ ] Share: Web Share API + clipboard + PNG/text export reusing `study_export_html` pattern
- [ ] Guardrails: hide low-quality (`suggested`-only + no consensus) from top-10 unless affinity override; tradition badge on disagreements; pastoral copy review. Outside-canon: badge + source line mandatory, scholar-lane cards visually distinct, daily verse stays canon by default.
- [ ] Docs: `docs/feed-algorithm.md` (formula, constants, worked example, license attributions) + wiki stub
- 📏 Scope: ~2 files, ~150 lines + docs
- ✅ Checkpoint: `sentrux check .` (or `ruff` + `pytest`) clean; docs page renders in wiki
- ⚙ Fallback: streaks localStorage-only in v1 if backend counter slips
- Depends on: C2

## Track D: Communities (subreddit-equivalents) + posts/comments `[ ]`
- Description: Reddit/X-shaped layer — `r/` communities derived from existing clusters/entities, general + per-community feeds, verse-anchored threads. Reuses `forum_topics`/`forum_posts`; vote arrows wire directly into Hot/Wilson inputs.
- 📏 Scope: ~5 files, ~500-700 lines

### Phase D1: Community taxonomy from existing data (no LLM) `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [ ] Seed `r/` list from what exists: 41 `thematic_clusters` (creation_word, abrahamic_faith, temple_presence, suffering_servant, …) + 5 `forum_topics` (temple-symbolism, isaiah-studies, gematria-patterns, bom-isaiah, covenant-theology) + top entities/symbols by `verse_entities` count. Cap v1 at ~20 communities; each has slug (`r/covenant`), title, 1-line description from cluster text, and deterministic membership rule (cluster members + entity-bridge verses + symbol occurrences + book prefix) + work-scope default
- [ ] Each community = saved feed filter (topics/moods/entities/books/works allowlist + canon_mode default). General scroll `r/all` = unscoped hot feed. Registry lives in `data/feed_communities.json` + validator test; no new categorization pipeline
- [ ] Backfill rule: LLM MAY propose names/descriptions for sparse clusters offline, batched, cached in registry, human-approved in PR — never auto-applied, never at request time
- 📏 Scope: ~2 files, ~200 lines
- ✅ Checkpoint: registry validates (every community resolves >=50 verses; overlaps >30% documented as parent/child)
- ⚙ Fallback: thin community (e.g. `r/gratitude`) ships as entity+keyword rule marked `provisional` in UI
- Depends on: B1, A2

### Phase D2: Posts + comments on units and communities `[ ]`
- [ ] Extend existing `forum_topics`/`forum_posts` (keep server-side author rule from `web/routes/forum.py`): add `feed_posts(id, community_slug, unit_id NULL, title, body, author_key, verse_refs[], created_at)` + `feed_comments(id, post_id, unit_id, parent_id NULL, body, author_key, created_at)`. Nested comments via existing `parent_id` pattern
- [ ] Voting reuses `feed_interactions` (ups/downs feed Hot + Wilson directly — vote arrows ARE the ranker input). Sort tabs map 1:1: hot → `hot_score`, top → `wilson_lower_bound`, new → recency, controversial → high-total ~50/50 split, best → Wilson + quality prior
- [ ] Moderation v1 (no ML): rate limits (reuse C1 pattern), length caps, verse-ref validation, one vote per user_key+item (last-write-wins), tradition-label nudge on doctrinal claims, report/hide → human queue table
- 📏 Scope: ~3 files, ~350 lines + migration
- ✅ Checkpoint: `pytest tests/test_feed_community.py -q` green (vote-once enforced, sorts differ on fixture, invalid refs rejected)
- ⚙ Fallback: if nesting stalls, ship flat comments + `reply_to` quote line; nest as fast-follow
- Depends on: D1, C1

### Phase D3: Reddit/X UI shape `[ ]`
- [ ] Layout: left sidebar (`r/all` + community list + canon-scope selector), center feed (vote arrows | unit card | comment/share/save), sort tabs (hot/top/new/controversial/best), right rail (community header, rules, related verses via `graph_reachable`, top contributors). X touches: compact mode, quote-share, `j/k` next/prev + `a/z` vote (reuse hotkey pattern). **Scroll lives in the tab strip as the ex-Learn slot (desktop + mobile); communities render as `r/` header + sidebar inside Scroll, not as separate top-level tabs**
- [ ] Thread view: unit card pinned on top, threaded comments below, `reply` prefills `parent_id`, deep links `/r/{slug}/comments/{post_id}`
- [ ] Playwright: switch community, change sort, vote, comment, reload persists
- 📏 Scope: ~3 files, ~300 lines
- ✅ Checkpoint: frontend build green + community/comment smoke passes
- ⚙ Fallback: if sidebar/rails stall, ship sort tabs + community chips only; rails as fast-follow
- Depends on: D2

## Acceptance
- [ ] Feed returns 20 ranked, diversified, non-repeating **thought-units (1–3 verses, same chapter/work, each with unit_reason + why-grouped line)**
- [ ] Ranking math matches Reddit Hot / Wilson / HN reference values in unit tests
- [ ] Devote parity checklist: card, topics/moods, reflection, audio, share, save, streak, daily verse — all present
- [ ] p95 < 300ms locally, no 500s on bad input, fallback feed on cold start
- [ ] Docs + attributions shipped (Reddit/Apache, Wilson/public-domain statistics, HN, MMR citation)
