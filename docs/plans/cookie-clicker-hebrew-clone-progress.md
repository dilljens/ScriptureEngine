# Progress: Cookie-Clicker Hebrew clone

## Session 2026-09-10 (plan created; prior prototype sessions)
- Current track: Track D (Phase D1 in progress — wiring analytics now)
- [x] Typing-reset bugfixes (App.jsx guard, CardQueue reset-key, Quiz 1s timer, PassageReader key)
- [x] Idle research (Cookie/AdCap/Realm/NGU/Melvor/Idle Slayer/Revolution formulas)
- [x] Open-source research (Incremancer = zombie favorite, ideas-only license)
- [x] Design doc `docs/aleph-to-revelation.md` (balance, loop, adaptive, mobile, lineage)
- [x] Prototype: idle-game.js + HebrewIdleBar + ModePicker + Kavod/Frenzy/Warp
- [x] Popularity verdict: Cookie Clicker #1 + full copy blueprint (research report in chat)
- [x] Plan + findings files written (this file = progress)
- [x] Track D Phase D1: analytics lib (`lib/analytics.js`, 5 asserts) + wiring (answers, purchases, prestige, quests, boosts, milestones, offline, feedback, mode/game switches, session_start) + 📊 export button
- [x] Track D Phase D2: `docs/balancing-analytics.md` (schema + 7 queries + tuning table)
- [ ] Track D Phase D3: backend batch endpoint (deferred)
- [x] Theme locked: **EMET — Golem Maker** (Incremancer horde × Cookie ladder, Hebrew-native prestige)
- [x] `docs/DESIGN.md` — game-design constitution (MDA/flow/SDT/Koster/juice/idle-math/learning integrity)
- [x] `GolemCanvas.jsx` — visible agent layer (canvas 2D, rAF, caps, reduced-motion)
- [x] Bugfix: prestigeTick propsRef omission (spurious mount flash + never firing) — critic-found
- [x] Migration: stale game id normalized to emet (`loadGameId`) + analytics default fixed
- [x] Test: `__tests__/hebrewGames.test.js` (6 tests) — 122/122 total green
- [ ] Tracks A/B/C: not started (await playtest signals from D)

## Session 2026-09-11 — local instance bring-up (playtest)
- [x] Fixed DB drift: `works.position` missing in production DB (code+ingest expect it) → additive migration
- [x] Recovered empty `data/memorize.db` (0 bytes, wiped Sep 6): ran `build_hebrew_graph.py` (102 nodes) → `align_hebrew_vocabulary.py` → `seed_hebrew_all.sh` (696 nodes, 531 word lessons, 28 consonants, 5634+ practice items)
- [x] NEW server-side telemetry: `POST /api/v1/hebrew/analytics` appends to `logs/hebrew-analytics.jsonl` (never fails the request)
- [x] Frontend auto-flush: `analytics.flushLog()` every 8s + `sendBeacon` on pagehide; `startAutoFlush()` mounted in HebrewLearnView
- [x] Running: api :8002, web :5176, both 200
- Note: quiz `/hebrew/quiz` returns 0 for a fresh user (draws from studied material) — use per-lesson quiz `/hebrew/lesson/{id}/quiz`, which returns 5. `audio_url` still absent on quiz questions (backend task pending).

## Session 2026-09-11 — UX + performance pass
- [x] **Perf root cause**: `/api/v1/info` did two full GROUP BYs over 1.35M `connections` rows → **11.4s cold**, and App.jsx polled it **every 30s** (re-rendering the whole tree each time). Fixes: (a) RAM `INFO_CACHE` (static per process) → **0.007s**; (b) added missing `idx_connections_quality` (3.98s → 0.25s); (c) frontend poll 30s→60s + skip setState when payload unchanged.
- [x] Fixed `no such table: hebrew_confusability` (caught-but-noisy 200 traceback in review-queue) → ran `seed_hebrew_confusability.py data/memorize.db` (28 pairs).
- [x] UX: locked study nodes now say **why** ("🔒 Requires Kaf (כ) (0%)") — API already sent `prerequisites`; UI ignored it.
- [x] UX: golem shop **auto-opens** when you own nothing + first-run CTA + pulsing Letters button; canvas empty-state now says how ("inscribe a letter below 👇").
- Perf baseline (warm, after fixes): info 0.012s · books 0.044s · gamification 0.024s · review-queue 0.11s · curriculum 0.69s/365KB · search 2.5s cold → 0.04s cached.
- Remaining known perf: curriculum payload 365KB; search cold ~2.5s; dev mode is unminified (use `npm run build && npm run preview` to judge real speed).

## Session 2026-09-11 — game onboarding + viewer
- [x] **Buy-letter dead end (user-reported)**: new players started at **0 Ohr** while the cheapest letter costs 10 → every button disabled, unclickable, no feedback. Fixed: `STARTING_OHR = 50` on fresh state + rescue in `loadIdleState` for saves with no golems and <10 Ohr + prestige reseeds 50. Unaffordable letters are now clickable and flash "Need N more ✨".
- [x] **Games mode focus**: was rendering the full curriculum dashboard under the game. Now an early-return focused game screen (mode picker + game + earn-loop card); full browse is behind "📚 Browse all lessons" with a "← Back to the game" button (progressive disclosure).
- [x] Ran in axe-viewer: backend :5172 + vite :5173; `viewr_open_tab(plugin="browser", url=http://localhost:5176/)` — browser tab "EMET (local)" live in ScriptureEngine project. `start.sh` needed `chmod +x`.
- Tests: idle-game self-checks now 41 ok.

## Session 2026-09-11 — Track F: depth + agency (no audio, per user)
- [x] **F1 Letter ×2 upgrades** — thresholds 10/25/50/100 owned, cost `baseCost × {10,60,400,3000}`, one-time, gated. `letterMultiplier` folds into `perSecond`; new `statePerSecond(state, mastery)` composes owned/mastery/tracks/words/roots/letterUpgrades/perm so no call site can silently drop a modifier.
- [x] **F2 Kavod permanents** — 6 one-time upgrades bought only with 🌟 (tap ×2, +5% crit, frenzy +30s, offline +25%, +25% global, prestige seed letter), applied via `permEffect`.
- [x] **F3 Golems with purpose** — motes are now *carried* from golem to the bank (top-right) with easing + arc, bank ripples on delivery, golems surge/glow on a correct answer and dim on a wrong one. Frame-rate-independent `dt` (was hard-coded 1/60).
- [x] **Critic-found wiring bugs fixed**: `offlineEarnings` call site dropped `s.perm` (the 60-🌟 "Faithful Watch" upgrade did nothing) and the HUD tap readout dropped `state.perm` (reported half the real tap). Both fixed + regression asserts added.
- Tests: idle-game self-checks now **58 ok**; vitest **122/122**; build green.
- Deferred nits (critic): impure setState updaters call `rollTap`/`saveIdleState` inside the reducer (dormant — `onEarn` not passed); shop handlers use render-closure state (two batched clicks could clobber).

## Session 2026-09-13 — Track A1: letter synergy (breadth beats spam)
- [x] Resolved a plan/design conflict before coding: plan A1 said "12-tier producer ladder (Etzba→Sofer→Yeshiva)", but `DESIGN.md` locks "Letters are the generators" (22 letters) and F1 already shipped A2's per-tier ×2 upgrades. User chose the DESIGN.md-consistent reading.
- [x] `synergyMultiplier(owned, mastery, i)` in `idle-game.js`: +2% per *other* letter owned, +4% per other letter *mastered* (bar 0.8 = curriculum's own), capped at +100%. Folded into `perSecond` (so `statePerSecond`/`tapValue` inherit it).
- [x] 8 new self-check asserts: lone-letter = ×1, breadth lifts, mastery > ownership, threshold match, cap, symmetry, perSecond wiring.
- Tests: idle-game self-checks **65 ok / 0 fail** (was 58); `vite build` green (1m02s, 403 modules).
- ⚠️ `vitest` hangs at startup at `RUN v4.1.10` on Node **v26.8.1** — zero tests run, on any file, independent of this change. Unit suite could not be executed; pre-existing environment breakage, not a regression.
- Follow-up (A2 done in the next session): synergy surfaced in the HUD.

## Session 2026-09-13 — A2 + Tracks B, C, D (remaining plan phases)
- [x] **A2** — HUD says `⚡ +X%` (breadth), each shop tile's tooltip shows its own live `synergy ×N.NN`; a footer explains it. Workshop number via new `workshopSynergy`.
- [x] **B1 Aliyah sparks + heavenly chain** — `sparksEarned = floor(cbrt(lifetime/1e8))` (plan's 1e12 deviated: unreachable at our scale). Unspent sparks = +1% Ohr; ordered 6-upgrade chain bought with sparks, each gated on the previous, so bonus vs permanence is a real trade. Effects reuse `permEffect` (no dropped-modifier class of bug). Spark progress card in the goal grid.
- [x] **B2 Golden Prompts** — spawn every 60–180s (only when production > 0), claimed by the next graded answer inside a 20s window; Gale ×7/77s · Dew 2h · Rush ×3 tap/60s. Wrong/late fizzles; expired prompts auto-clear. Rewards use the *buffed* rate, matching Time Warp.
- [x] **C1 Figs** — 20h timer, harvest grants 4h production × (1+level·0.1), levels grove 1–10, replants. Offline ladder intentionally NOT nerfed to 5% (contradicts DESIGN.md "offline = gift"; shipped 50%→100% already implements the ladder). Harvest is a deliberate tap, not quiz-gated (misclick would punish).
- [x] **C2 Achievements→Shemen + daily** — 10 state-derived achievements, +4% Ohr each; daily lesson = 10 correct → 1h production, once/day, resets on rollover.
- [x] **D3** — `/api/v1/hebrew/analytics` now also writes the indexed `hebrew_analytics_events` table (JSONL kept as never-fail fallback). Malformed `t` can no longer 500 it (`_safe_epoch`); connection closed in `finally`.
- [x] **Critic pass → 5 real bugs found & fixed:** (1) the fig mount effect's value-commit clobbered the functional offline `pendingOffline` update → offline Ohr shown but not credited; merged to a single commit. (2) endpoint 500 on malformed `t` / leaked connection. (3) Dew/fig/daily omitted buffs (Dew could grant 0) → all use the buffed rate now. (4) expired prompts blocked future spawns → auto-clear. (5) `words100` achievement was unreachable (`state.words` is never written) → replaced with reachable `own22`.
- Tests: idle-game self-checks **123 ok / 0 fail**; `vite build` green (1m16s, 403 modules, 0 warnings); full-app esbuild bundle green; `py_compile` + function-level endpoint test with malformed payloads green.
- Note: the running backend on :8002 has no `--reload`, so the D3 change needs a restart before it's live.
- Known remaining: pre-existing impure `setState` updaters (offline/claimOffline/boost/quest/feedback/mute) still do side effects in the reducer — StrictMode can double-run them. Follow-up migration to the `commit` pattern.
- `state.words` is still never assigned, so the `globalMultiplier` word term (+2%/word) is dormant — pre-existing, not touched.




- Blockers: vitest unusable on Node v26.8.1 (startup hang, 0 tests run)
- Decisions made: mechanics-only clone; Ohr=wait/Kavod=know; punishment ban; local-first analytics; A1 = letter synergy (12-tier ladder superseded by DESIGN.md); Aliyah BASE 1e8 not 1e12 (reachability); offline not nerfed; figs not quiz-gated
- Tests: idle-game.js self-checks green (123); vite build green (1m16s); vitest blocked by environment hang
