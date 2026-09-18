---
status: completed
kind: plan
area: hebrew-scale
author: james
created: 2026-09-16
---

# Project: Scale to 500+ words/roots + grammar tracks + tap feedback

Goal: 500 words/roots learnable in Anki-style tiers with Cookie-Clicker depth, grammar as 3 tracks, and visible tap feedback.

## Requirements
- [x] R1: Word Tiles pages through all 500 words in 10 decks of 50 (due-first order)
- [x] R2: Word/root nodes spread across levels 4–7 by frequency tier (no L4 blob)
- [x] R3: Tap feedback — every tap (correct/wrong) is visible where the numbers live
- [x] R4: Grammar reorganized into 3 tracks x levels (display + income), no content rewrite
- [x] R5: No balance break — 1.15 law, x2 tiers, Shemen (milk), cube-root prestige untouched

## Pre-resolved Decisions
- Milk equivalent already exists: Shemen +4%/achievement (`SHEMEN_PER_ACHIEVEMENT`, wired into `statePerSecond`). No Honey system needed.
- Mastery = interval (Anki 26.08.1 verified locally): mature = 21+ days (`WORD_MATURE_INTERVAL_DAYS`, both ends).
- Tiers derived from top500 rank: 0-49 L4, 50-149 L5, 150-299 L6, 300+ L7. Seeder writes it; migration fixes existing DBs.
- Tap economy rule preserved: Ohr = wait, Kavod = know. Feedback is visual only, never free taps.
- Roots prestige stays sqrt for now; cbrt retune is a balance decision for later (needs sim).

## Track A: Tap visual feedback `[x]`
- Description: make every tap visible at the HUD numbers (Cookie Big-Cookie squish equivalent)
- Scope: 1 file (HebrewIdleBar.jsx), ~20 lines

### Phase A1: Counter pop + answer ring `[x]`
- Priority: high
- [x] Ohr counter re-pops on every tap (`key={state.taps}` + `idle-pop`)
- [x] Kavod counter pops on earn
- [x] HUD panel ring flashes green (correct) / red (wrong), keyed by `answerPulse`
- [x] "Study to tap" hint when `taps === 0`
- Scope: 1 file, ~20 lines
- Checkpoint: `vite build` green; manual: answer quiz -> counter pops, ring flashes
- Fallback: floaters only (current behavior)
- Depends on: nothing

## Track B: Word/root tiers + deck pager `[x]`
- Description: 500 words pageable in 10 decks; nodes leveled by tier
- Scope: ~4 files, ~120 lines

### Phase B1: Deck pager on Word Tiles `[x]`
- Priority: high
- [x] `offset` state, Deck N/10 header, prev/next (uses existing `top-words?limit&offset&with_status`)
- [x] Due-first sort within deck (overdue by `due_in_days` first, mastered last)
- [x] Sync `masteredWords` across deck pages (union, not replace)
- Scope: 1 file, ~40 lines
- Checkpoint: `vite build` green; page through 3 decks, mastered persist
- Fallback: single 50-word page (current)
- Depends on: nothing

### Phase B2: Tier levels in seeder + migration `[x]`
- Priority: high
- [x] `wordTier(rank)` helper (idle-game.js + seeder): 0-49 L4, 50-149 L5, 150-299 L6, 300+ L7
- [x] `seed_hebrew_vocabulary.py`: level from tier instead of constant 4
- [x] `scripts/migrate_word_tiers.py`: re-level existing `vocab_*` nodes by rank suffix
- [x] Run migration on local dev DB, verify counts per level
- Scope: 3 files, ~80 lines
- Checkpoint: `sqlite3 data/memorize.db "SELECT level,COUNT(*) FROM hebrew_nodes WHERE category='word' GROUP BY level"` shows spread; seeder rerun idempotent
- Fallback: keep L4 blob, tiers display-only
- Depends on: nothing

### Phase B3: Staged translation gates `[x]`
- Priority: medium
- [x] Mastery gates instead of known-count (no extra fetch): decks 3+/6+ need 10/40 mastered, roots screen needs 25 — `wordDeckUnlocked`, `WORD_DECK_GATES`, `ROOTS_TILES_GATE`
- [x] Roots Tiles screen reusing WordTilesView (`kind="roots"`) — example-based known status, self-graded reps, mature=3 net knows
- [x] word<->root synergy: words +5%/mature-root, roots +0.1%/mature-word (`WORD_ROOT_SYNERGY`, `ROOT_WORD_SYNERGY`, `matureRootCount`)
- Scope: ~3 files, ~100 lines
- Checkpoint: `node` self-checks + build green
- Fallback: single 100-gate (current)
- Depends on: B1

## Track C: Grammar tracks `[x]`
- Description: 48 existing nodes into 3 tracks x levels; tracks pay income
- Scope: ~3 files, ~120 lines

### Phase C1: Track grid (display + income) `[x]`
- Priority: medium
- [x] `track`/`track_level` DERIVED from category+level (no migration needed) — `grammarTrack`, `GRAMMAR_TRACKS`
- [x] Tracks filter tab: 3 rows x 5 tiers, click-through to lessons, empty cells = backlog
- [x] +5%/complete tier (cap +50%), threaded through statePerSecond/letterRate + 📜 HUD chip
- [x] Empty cells render as backlog cells in the grid itself
- Scope: ~3 files, ~120 lines
- Checkpoint: build green; grid renders; income math in self-checks
- Fallback: flat categories (current)
- Depends on: nothing

## Track D: Minigames (shipped under garden-onescreen plan) `[x]`
- Out of scope here by design; built as docs/plans/hebrew-garden-onescreen.md Tracks A–J: Root Garden → Golden Dreidel combos → Watchmen → Shuk market (+ feasts, scribe autobuy). Do not start here.
