---
status: active
kind: plan
area: hebrew-games
author: james
created: 2026-09-16
---

# Project: Root Garden minigame + one-screen iPhone layout

Goal: first minigame (Root Garden) live in a tabbed single-screen game HUD that needs no page scroll on iPhone.

## Requirements
- [ ] R1: Garden: 6 plots, plant readable roots for Ohr, 2h growth (3 stages), harvest = 30min production + 5 Kavod + 1 root rep
- [ ] R2: Cross-breed: adjacent different mature roots → 25% mutation on harvest → +15 Kavod + rep for the neighbor root (feeds B3 +5% word synergy)
- [ ] R3: No punishment mechanics (wither/rot banned — matches game rules); costs only Ohr, never Kavod
- [ ] R4: iPhone: HUD + tabs + active panel fit one screen, no page scroll (tab content may mini-scroll internally on SE-size screens)
- [ ] R5: Desktop keeps full power — tabs for everyone (no forked logic), golems collapsible

## Pre-resolved Decisions
- Garden state in idle-game.js (`state.garden.plots`), pure functions + self-checks, same pattern as figs/vineyard.
- Plant picker = roots readable from owned letters (letter-level readability, not example-based — simpler, documented).
- Tabs replace showShop/showQuests/showUpgrades toggles (deletion): Letters | Garden | Boosts | Quests | Upgrades. HUD keeps counters + prestige/exile/rest.
- GardenPanel.jsx new file (~200 lines); IdleBar restructure is moves, not rewrites.

## Track A: Garden economy `[x]`
- Phase A1: idle-game functions + self-checks `[x]` — 16 asserts, 266 total pass
- Phase A2: GardenPanel + IdleBar Garden tab wiring `[x]`

## Track B: One-screen layout `[x]`
- Phase B1: tab bar + section moves + golem collapse `[x]` — 5 tabs replace 3 toggles (net code deleted); badges on tabs; e2e updated for tab nav
- Phase B2: compact mobile CSS (tab bar, grid density, HUD squeeze) `[x]` — max-h-100dvh shell, flex-1 scrolling tab panels, mobile golem cap already in

## Track C: Sanhedrin sages (2nd minigame) `[x]`
- SAGES catalog (6 gifts+prices), SANHEDRIN_SEATS ×1.0/0.6/0.3, 4h swap cooldowns, one-seat-per-sage
- sageEffects choke point wired into production/costs/taps/Kavod/offline/Shemen; 10 new self-checks (276 total)
- SagesPanel + Sages tab (unlock: 10 letters or 1 root)

## Track D: Bottom tab bar `[x]`
- Tab bar relocated to panel bottom (thumb-first, safe-area padded, icon-over-label)
- Middle always-visible block (vow/legend/goals/offline/onboarding) moved above tab content; golden/prophet dialogs are fixed overlays ( untouched)
- DOM order verified: HUD → golems → banners → 6 tab panels → bottom bar → toasts
## Track E: Golden Dreidel combos `[x]`
- Shofar Blast 4th prompt (workshop-scaled ×(1+golems/20), 60s, weight 1); buffs multiply across kinds (Frenzy × Gale × Shofar)
- Dew bank rule (min 2h, floor 15min, 15% of bank between); Get Lucky (buffed visits 2× faster); Prophet shofar blessing
- HUD combo readout (📯 mult + COMBO count); 8 new self-checks, old max-not-product/bank tests updated honestly

## Track F: Shuk market (3rd minigame) `[x]`
- 5 goods in production-seconds, deterministic 47+11min cycles, 2% spread, buy 1/10 + sell-all
- Learn on credit: +1h now, −25% 4h, 24h cooldown; debt flows through the combo multiplier
- ShukPanel + 🧺 tab (7-tab bottom bar, compact labels); 12 new self-checks (296 total)
- Verify: esbuild clean, 13 backend tests pass, vite build green

## Track G: Watchmen rename `[x]`
- Sages → Watchmen (Is. 62:6): WATCHMEN/WATCH_SEATS/watchEffects/seatWatchman, WatchmenPanel, 👁️ Watch tab; six proper-name figures kept; sanhedrin→watchmen state key with one-release fallback

## Track G2: Major Prophets watchmen `[x]`
- Catalog rewritten: Isaiah 📖, Jeremiah 🕊️, Ezekiel ⚖️, Moses 🔥, Daniel 🦁, Elijah ⚡ (4 majors + 2 greatest, per user pick); same balanced numbers, Hebrew names shown, Is. 62:6 epigraph
- Verify: 296 self-checks, esbuild clean, vite build green

## Track H: Per-root FSRS (top-100) `[x]`
- seed_hebrew_roots --top-roots gap-fills 96 generated lessons from top500 (113 root nodes total, L4-6, idempotent)
- hebrew_node_map indexes lesson `root` field; shared _attach_srs_status helper; top-roots?with_status=1 resolves root_ ids by PK (no LIKE)
- Roots Tiles grades noded roots through real FSRS (Know=Good/Skip=Again) with FSRS tile visuals; reps kept for synergy flow
- Verify: 296 self-checks, 21 backend tests, top-roots status resolves, vite build green

## Track I: Hebrew feasts seasonal layer `[x]`
- FEASTS table (8 moedim with meaning/scriptures/vocab), Intl Hebrew-calendar detection verified vs real 2026 dates, 13 new self-checks (309 total)
- Effects: mercy windows (Passover/YK 60s), Shavuot grammar ×2, Trumpets/Hanukkah/Shemini spawn quickening, Sukkot garden ×2, Purim +5 🌟/claim
- HUD feast chip (live/countdown) + info modal; Enoch 364-day tie-in documented for the Luminaries follow-up
- Fixed en route: purim edit ate the answer-path `hours` guard (restored)
- Verify: 309 self-checks, 54 backend tests, esbuild clean, vite build green

## Track J: Scribe autobuy (spending automated, learning never) `[x]`
- Double gate: first forged root globally + mastery 0.8+ per letter ("a letter you've taught inscribes itself"); 50 Kavod ×1.6 each — automation bought with knowledge
- One-unit drip per tick (never drains the saving bank); global ON/OFF; exile-aware; quill hire buttons on mastered tiles + 📜 badges
- 11 new self-checks (319 total); e2e buy-button order preserved
- Verify: 319 self-checks, esbuild clean, vite build green
- FEASTS table (8 moedim with meaning/scriptures/vocab), Intl Hebrew-calendar detection verified vs real 2026 dates, 13 new self-checks (309 total)
- Effects: mercy windows (Passover/YK 60s), Shavuot grammar ×2, Trumpets/Hanukkah/Shemini spawn quickening, Sukkot garden ×2, Purim +5 🌟/claim
- HUD feast chip (live/countdown) + info modal; Enoch 364-day tie-in documented for the Luminaries follow-up
- Fixed en route: purim edit ate the answer-path `hours` guard (restored)
- Verify: 309 self-checks, 54 backend tests, esbuild clean, vite build green
