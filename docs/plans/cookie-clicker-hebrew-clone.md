---
status: active
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
- [ ] R5: Retention: ripe Figs (24h), offline formula + cap, quests/dailies, achievements→Shemen milk
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

## Track A: Ohr core (generators + upgrades) `[ ]`
- Description: 12-tier ladder, 1.15 costs, tiered upgrades, tap power. Extends current 22-letter shop.
- 📏 Scope: ~2 files (lib/idle-game.js, HebrewIdleBar.jsx), ~200 lines

### Phase A1: Tier ladder + cost table `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [ ] 12 tiers mapped to Hebrew-learning producers (Etzba→Sofer→Yeshiva…) with base costs/rates
- [ ] Keep 1.15 exponent; synergy pairs forcing balanced buying
- [ ] Self-check assertions for ladder math
- 📏 Scope: ~1 file, ~80 lines
- ✅ Checkpoint: `node frontend/src/lib/idle-game.js` all ok
- ⚙ Fallback: keep 22-letter shop, reskin rates only
- Depends on: nothing

### Phase A2: Tiered ×2 upgrades + tap power `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [ ] Own-1/5/25/50/100 ×2 upgrades per tier; tap = 1 + % of per-sec
- [ ] Claim buttons in shop UI
- 📏 Scope: ~2 files, ~120 lines
- ✅ Checkpoint: build green + buy/claim logged
- ⚙ Fallback: global ×2 milestones instead of per-tier
- Depends on: A1

## Track B: Kavod prestige + Golden Prompts `[ ]`
- Description: Aliyah cube-root prestige, heavenly chain, quiz-gated buffs. Extends current roots/frenzy.
- 📏 Scope: ~2 files, ~200 lines

### Phase B1: Aliyah prestige + unlock chain `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [ ] `level = floor((lifetime/1e12)^(1/3))`, +1% each; ordered unlock chain (Legacy→…→key)
- [ ] First-ascend target surfaced in UI (~365 levels)
- 📏 Scope: ~1 file, ~100 lines
- ✅ Checkpoint: self-check prestige math + UI shows progress
- ⚙ Fallback: keep sqrt-roots prestige, add % chain only
- Depends on: nothing

### Phase B2: Golden Prompt buffs `[ ]`
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [ ] Prompt spawns every 60–180s; claim = audio quiz in 20s window → Frenzy ×7 77s / Lucky / Dikduk Rush
- [ ] Wrong = fizzle (nothing), never drain
- 📏 Scope: ~2 files, ~150 lines
- ✅ Checkpoint: prompt appears, quiz-gated, buff applies + logged
- ⚙ Fallback: keep manual Frenzy/Time-Warp buttons only
- Depends on: B1

## Track C: Retention (Figs, offline, quests, milk) `[ ]`
- Description: 24h Figs, offline cap upgrades, daily quests, achievement milk. Mostly extends existing.
- 📏 Scope: ~2 files, ~150 lines

### Phase C1: Figs + offline ladder `[ ]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [ ] Fig ripens 20h, harvest = tap + quiz; building levels 1–10
- [ ] Offline 5% → 100%+ via upgrades, cap 24h → 5d8h
- 📏 Scope: ~2 files, ~100 lines
- ✅ Checkpoint: fig lifecycle + offline claim logged with rate/cap
- ⚙ Fallback: keep 12h/24h offline, skip figs
- Depends on: nothing

### Phase C2: Achievements→Shemen + dailies `[ ]`
- 🏷 Priority: low
- 🔁 Max turns: 8
- [ ] Each achievement +4% Shemen; Talmidim multipliers read Shemen
- [ ] Daily lesson-streak reward requiring 10 correct
- 📏 Scope: ~2 files, ~80 lines
- ✅ Checkpoint: milk % moves CpS; daily grants once/day
- ⚙ Fallback: static achievement list, no milk
- Depends on: C1

## Track D: Analytics for both games `[ ]`
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

### Phase D2: Balance queries doc `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 5
- [ ] `docs/balancing-analytics.md`: event schema + console/node queries per tuning question + thresholds
- 📏 Scope: ~1 file
- ✅ Checkpoint: queries run against exported log
- Depends on: D1

### Phase D3: Backend batch endpoint `[ ]`
- 🏷 Priority: low
- 🔁 Max turns: 10
- [ ] `POST /api/v1/hebrew/analytics` + `hebrew_analytics_events` table; batch upload on export/interval
- 📏 Scope: ~2 files (web/routes/hebrew.py, schema)
- ✅ Checkpoint: 200 OK + rows queryable
- ⚙ Fallback: stay local-only
- Depends on: D2

## Track F: Depth + agency (no audio) `[ ]`
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
- Vineyard (Garden), Midrash (Grimoire), Sanhedrin (Pantheon), Shuk (Market) — NOT this plan. Listed so clones don't fork structure early: keep `systems/` seams in lib files.
