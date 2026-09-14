---
status: completed
kind: plan
area: hebrew-games
author: james
created: 2026-09-10
---

# Project: Cookie-Clicker clone with Hebrew theme + learning currency

Goal: Clone Cookie Clicker's progression systems (mechanics only, original theme/art/code) with Ohr ✨ as time-money and Kavod 🌟 as learning-money earned only by correct Hebrew↔English/audio answers.

## Requirements
- [ ] R1: 12-tier Ohr generator ladder (1.15 growth) with tiered ×2 upgrades — Cookie pacing, Hebrew skin
- [ ] R2: Tap power + streak/crit combo system driven by recall accuracy, never reflex spam
- [ ] R3: Aliyah prestige (cube-root) + heavenly unlock chain, all gated by learning
- [ ] R4: Golden Prompt quiz-gated buffs (Frenzy ×7, Lucky, Dikduk Rush) — accuracy windows, never time punishment
- [x] R5: Retention: ripe Figs (20h), offline formula + cap, quests/dailies, achievements→Shemen milk
- [ ] R6: Every event in BOTH games logged locally with mode/game tags; exportable; balance queries documented
- [ ] R7: Backend batch endpoint for durable analytics (phase 2, after local proves useful)
- [ ] R8: No Cookie assets, names, text, or code — mechanics only (proprietary license)

## Pre-resolved Decisions
- Clone target: Cookie Clicker (verified #1 composite: 67.8k Steam peak, 93k reviews, genre synonym). See findings.
- Theme: Biblical Hebrew study; Ohr/Kavod split already prototyped (Ohr idle, Kavod learning-only).
- Stack: existing React+Vite frontend, no new deps; localStorage trial → backend tables later.
- Rule: Ohr = wait, Kavod = know. No Ohr purchase grants Kavod; Kavod never purchasable or idle-farmable.
- Punishment ban: wrong answers reset streak only — never drain bank, never Clot/Ruin.
- Mobile-first: ≥44px targets, stacked HUD, no reflex windows under 20s.

## Track A: Ohr core (generators + upgrades) `[x]`
- Description: letter-generator synergies + tiered upgrades, tap power. Extends current 22-letter shop.
- 📏 Scope: ~2 files (lib/idle-game.js, HebrewIdleBar.jsx), ~80 lines remaining

### Phase A1: Letter synergy (breadth beats spam) `[x]`
- 🏷 Priority: high
- [x] `synergyMultiplier(owned, mastery, i)`: +2% per other letter owned, +4% per other letter mastered (curriculum bar 0.8), capped +100%
- [x] Folded into `perSecond` — flows through `statePerSecond`/`tapValue` automatically
- [x] Self-check assertions (8) for lone-letter, breadth, mastery, cap, symmetry, perSecond wiring
- 📏 Scope: 1 file, ~50 lines (was ~80)
- ✅ Checkpoint: `node frontend/src/lib/idle-game.js` → 65 ok / 0 fail; `vite build` green
- ⚙ Fallback: keep 22-letter shop, reskin rates only
- **Decision:** the plan's "12-tier producer ladder (Etzba→Sofer→Yeshiva)" is superseded by
  `DESIGN.md` ("Letters are the generators", 22 of them). The missing piece DESIGN.md
  explicitly names — *"leaders must shift over time … synergy so studying a new letter
  beats spamming a maxed one"* — is what this phase now delivers. A2's per-tier ×2
  upgrades were already shipped by F1, so A2's only remaining item is surface-in-UI.
- Depends on: nothing

### Phase A2: Surface upgrades + synergy in the shop `[x]`
- 🏷 Priority: medium
- [x] Own-10/25/50/100 ×2 upgrades per letter + tap = 1 + 5% of per-sec *(shipped in F1)*
- [x] Live breadth bonus in the HUD (`⚡ +X%`) + per-letter `synergy ×N.NN` in each shop tile's tooltip + a footer explainer
- 📏 Scope: 1 file, ~30 lines
- ✅ Checkpoint: build green; HUD shows a synergy % that moves when a new letter is bought
- ⚙ Fallback: leave synergy implicit (self-checks still guard the math)
- Depends on: A1

## Track B: Aliyah sparks + Golden Prompts `[x]`
- Description: Aliyah cube-root sparks, heavenly chain, quiz-gated buffs. Extends current roots/frenzy.
- 📏 Scope: ~2 files, ~200 lines

### Phase B1: Aliyah sparks + heavenly chain `[x]`
- 🏷 Priority: high
- [x] `sparksEarned = floor(cbrt(lifetime / BASE))`; each UNSPENT spark = +1% Ohr
- [x] Ordered heavenly chain (Legacy → Primordial Light → Chochmah → Shabbat Rest → Long Breath → Key of David), each gated on the previous; buying spends sparks so bonus and permanence compete
- [x] First-spark target surfaced in the HUD/next-goals grid
- 📏 Scope: ~1 file, ~90 lines (lib) + HUD
- ✅ Checkpoint: 20+ self-checks for cube-root, chain gating, spend-reduces-bonus, effect plumbing; build green
- ⚙ Fallback: keep sqrt-roots prestige, add % chain only
- **Tuning note:** `ALIYAH_BASE = 1e12` (the plan's value), confirmed by headless sim (`scripts/balance-sim.mjs`): first spark ~2.8h / full chain ~13h of *optimal bot* play → days for a real learner. An earlier `1e8` was tried and **rejected** — first spark at 40m and the whole chain done in 1.8h (trivial). Deliberately NOT a wipe (roots already supply the reset loop; DESIGN.md bans punishing resets).
- Depends on: nothing

### Phase B2: Golden Prompt buffs `[x]`
- 🏷 Priority: medium
- [x] Prompt spawns every 60–180s; claim = answer the next question correctly inside a 20s window
- [x] Rewards: Ruach Gale ×7 Ohr / 77s · Dew of Light (2h production) · Dikduk Rush ×3 tap / 60s
- [x] Wrong or late = fizzle (nothing), never drain; expired prompts auto-clear; no prompt spawns at zero production
- [x] Rewards use the buffed effective rate (same as Time Warp), not the raw rate
- 📏 Scope: ~2 files, ~120 lines
- ✅ Checkpoint: self-checks for spawn cadence, window enforcement, wrong/expired fizzle, buff stacking (max not product), reward plumbing; build green
- ⚙ Fallback: keep manual Frenzy/Time-Warp buttons only
- **Deviation:** plan said "audio quiz" in the window; reusing any graded answer (the existing answer bus) is equivalent and needs no new quiz surface. Answering IS the claim.
- Depends on: B1

## Track C: Retention (Figs, daily, achievements) `[x]`
- Description: 20h Figs, daily lesson, achievement Shemen. Extends existing offline/quests.
- 📏 Scope: ~2 files, ~150 lines

### Phase C1: Figs `[x]`
- 🏷 Priority: medium
- [x] Fig ripens over 20h; harvest grants 4h of production × (1 + level bonus), levels the grove 1–10 (+10% Ohr per level), replants
- [x] Fig level feeds `statePerSecond`; fig bonus shown in the Grove panel
- 📏 Scope: ~1 file, ~50 lines + HUD
- ✅ Checkpoint: self-checks for ripening boundary, harvest math, level cap, replant; build green
- ⚙ Fallback: keep 12h/24h offline, skip figs
- **Deviation (offline ladder):** the shipped offline formula already has the cap (12h→24h at 10 roots) and efficiency (50%→100% via Chochmah). The plan's "5% → 100%+ / cap → 5d8h" would NERF shipped behavior and contradicts DESIGN.md "offline = gift, rest is supported, never punished" — intentionally not adopted. Only the Fig timer was missing.
- **Deviation (harvest):** plan said "tap + quiz"; code harvests on one deliberate tap. Losing a 20h timer to a misclick would punish (DESIGN.md ban). The timer IS the retention hook.
- Depends on: nothing

### Phase C2: Achievements→Shemen + daily lesson `[x]`
- 🏷 Priority: low
- [x] 10 achievements, each +4% Ohr ("Shemen"), derived from state (can't be lost); folded into `statePerSecond`
- [x] Daily lesson: 10 correct answers → claim 1h of production, once per day; resets on day rollover
- 📏 Scope: ~1 file, ~60 lines + HUD
- ✅ Checkpoint: self-checks for achievement predicates, Shemen composition, daily rollover/once-only; build green
- ⚙ Fallback: static achievement list, no milk
- **Deviation:** plan's "Talmidim multipliers read Shemen" is moot — there is no building ladder (letters are the generators), so Shemen is a global multiplier.
- Depends on: C1

## Track D: Analytics for both games `[x]`
- Description: local event log + export + balance queries now; backend batch later.
- 📏 Scope: ~3 files (lib/analytics.js, IdleBar wiring, docs/balancing-analytics.md), ~200 lines

### Phase D1: Local event log + wiring `[x]`
- 🏷 Priority: high
- [x] `lib/analytics.js`: ring buffer (2000), session id, mode/game tags, export JSON
- [x] Wire: answers, purchases, prestige, quests, boosts, offline, feedback, mode switches
- [x] Export button in game HUD
- 📏 Scope: ~3 files
- ✅ Checkpoint: play 2 min → export shows session events
- Depends on: nothing

### Phase D2: Balance queries doc `[x]`
- 🏷 Priority: high
- [x] `docs/balancing-analytics.md`: event schema + console/node queries per tuning question + thresholds (shipped earlier; plan checkbox was stale)
- 📏 Scope: ~1 file
- ✅ Checkpoint: queries run against exported log
- Depends on: D1

### Phase D3: Backend batch endpoint `[x]`
- 🏷 Priority: low
- [x] `POST /api/v1/hebrew/analytics` dual-writes JSONL (never-fail fallback) + `hebrew_analytics_events` table in memorize.db (queryable, indexed)
- [x] Malformed payloads cannot 500 the endpoint (`_safe_epoch`); connection closed in `finally`; DDL idempotent per batch
- 📏 Scope: ~1 file (web/routes/hebrew.py)
- ✅ Checkpoint: function-level test with malformed `t` → `{ok, stored_db}` and `t=0` row, no exception; endpoint live was stale (server runs without --reload) pending restart
- ⚙ Fallback: stay local-only
- Depends on: D2

## Track F: Depth + agency (no audio) `[x]`
- Description: the game currently has 4 formulas and a shop. Add the two things
  that make it a game: meaningful upgrade choices, and golems that visibly work.
- 📏 Scope: ~3 files, ~350 lines

### Phase F1: Letter upgrades (×2 tiers) `[x]`
- 🏷 Priority: high
- [x] ×2 upgrade at 10/25/50/100 owned per letter; cost = baseCost × {10,60,400,3000}
- [x] `letterMultiplier` folds into perSecond; `statePerSecond` composes state
- [x] UI: upgrades surface when a letter hits the threshold (progressive disclosure)
- 📏 Scope: ~2 files, ~140 lines
- ✅ Checkpoint: self-check (×2 math, cost, buy-once) + build green
- Depends on: nothing

### Phase F2: Kavod permanents (learning buys permanent power) `[x]`
- 🏷 Priority: high
- [x] 6 one-time upgrades bought with 🌟 only: tap ×2, +5% crit, frenzy +30s,
      offline +25%, +25% global, +1 starting letter tier
- [x] Applied through `permEffect` into perSecond/tapValue/critChance/offline/buff
- 📏 Scope: ~2 files, ~90 lines
- ✅ Checkpoint: each effect changes its formula; buy-once guarded
- Depends on: nothing

### Phase F3: Golems with purpose `[x]`
- 🏷 Priority: high
- [x] Motes physically travel to the Ohr bank and pop the counter (not just drift up)
- [x] Golems flinch/excite on correct answers; horde dims on a wrong answer
- [x] Carry animation + bank pulse; no audio
- 📏 Scope: ~2 files, ~120 lines
- ✅ Checkpoint: visual states react to `answerPulse` prop; build green
- Depends on: nothing

## Track E: Minigames (future) `[ ]`
- ~~Vineyard (Garden)~~ `[x]` shipped 2026-09-14: 3 parallel 4h vines, 15min harvests, vineyard level 1-10 (+5%/lvl to 1.5x), Vinedresser achievement → Shemen. Sim: first harvest 4h bot, level 10 ~16h bot, no early-milestone distortion.
- Midrash (Grimoire), Sanhedrin (Pantheon), Shuk (Market) — still future. Listed so clones don't fork structure early: keep `systems/` seams in lib files.

## Engagement pass (post-plan, 2026-09-14) `[x]`
- Prophet's Choice: 12% of golden spawns offer pick-1-of-3 blessings (gale/dew/rush + Manna Kavod + Early Harvest timer cut). Same 20s window, same fizzle rules.
- Exile runs: optional prestige vow locking study to Aleph + 2 random letters until the next root, for double Kavod. Return achievement → Shemen. Sim prices the variant honestly (bot exiling half its prestiges runs ~2x slower to full heavenly — a real challenge tradeoff, not a tax on normal play).
- Streak reframe: best-streak is the hero number; once-a-day grace halves (not resets) a 10+ streak on a wrong answer. Nothing earned is ever lost.
