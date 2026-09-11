# Aleph to Revelation — incremental Hebrew game (trial)

No PaRDeS. Letters are fast. Roots / grammar / words are the game.

> **Theme (current): EMET — Golem Maker.** You are a *Baal Shem* animating clay
> servants by inscribing Hebrew letters. Each letter you buy becomes a visible
> golem that roams the workshop and mines ✨ Ohr. Mastered letters burn with the
> emet flame (golden). Prestige = erasing the א of **אמת** (truth) so it reads
> **מת** (death) — the golem returns to clay and rises stronger. This is the
> Incremancer fantasy (autonomous servant horde you can watch) fused with the
> Cookie Clicker scaffold (exponential ladder, prestige, buffs), in a theme that
> is Hebrew-native rather than a skin. Design law: `docs/DESIGN.md`.

## The mashup, precisely

| Layer | Incremancer (zombie) | Cookie Clicker | Emet |
|---|---|---|---|
| Producers | zombies you spawn, wander and kill | abstract generators tick | **golems** you inscribe — visible, roaming, each stamped with its letter |
| Payoff | kills are visible sprites | number goes up | Ohr motes drift off working golems |
| Unlock | energy → zombie | Ohr → building | Kavod/answers → letter → golem |
| Prestige | conquer next town | cube-root heavenly chips | erase א: clay → reformed stronger |
| Input | click to spawn | click cookie | **recall Hebrew** (H↔E + audio) |

The fusion rule: Incremancer supplies *visible agency* (why it feels alive),
Cookie supplies *long-arc depth* (why you return for weeks), Hebrew supplies
*the input* (why it matters). See `DESIGN.md` for the anti-Cookie-clone clauses.


## The fantasy

Letters mine **Ohr (light)**. Roots forge it into meaning. Words keep it forever.
Forgetting is the enemy — reviews are fuel, not homework.

## Layers (3 only)

| Layer | Name | Idle-game parent | What it is |
|---|---|---|---|
| 0 | Otiyot (Letters) | Revolution Idle circles / Cookie buildings | 22 generators, one per letter. Cheap, fast, mastery-gated |
| 1 | Shorashim (Roots) | AdCap Angels + Realm Gems (sqrt prestige) | First prestige: 3 mastered letters → 1 root. +10% global each, permanent |
| 2 | Milim + Pesukim (Words + Verses) | Idle Slayer souls + chest hunt | Mastered words = souls (+2% each). Verses = bosses/chests |

Grammar is not a layer — it's the **promotion track** (Revolution Promotion):
Dikduk Gain / Reading Speed / Niqqud Power / Chochmah Power. Spend roots to level tracks.

## Balance (stolen, tuned)

### Generators — Cookie 1.15 law
```
cost_next(i) = base_cost(i) * 1.15 ^ owned(i)
base_cost(i) = floor(10 * 4.2^(i/3))      # Aleph 10 … Tav ~230k
rate(i)      = 0.2 * 1.35^i per generator  # Aleph 0.2/s … Tav ~80/s
per_sec      = Σ rate(i) * owned(i) * (0.5 + mastery(i)) * global_mult
```
- `mastery(i)` comes straight from `curriculum[].mastery` (0..1). Unstudied letter still produces at 0.5x — never zero, never punishing.
- Unlock rule reuses curriculum `unlocked` (prereq mastery ≥ 0.8). Zero new gating.
- Growth 1.15 = Cookie Clicker standard. Production linear, cost exponential → walls appear on schedule, prestige pressure is real.

### Tapping — Cookie click + Slayer crit
```
tap = 1 + 0.05 * per_sec
streak_bonus = min(streak, 100) * 0.01   # +1% per streak, cap +100%
crit: 2% chance x7  (Cookie Frenzy lite, no stacking in trial)
tap_total = tap * (1 + streak_bonus) * (crit ? 7 : 1)
```
Every correct quiz/review answer = 1 tap. Wrong answer = streak resets, no Ohr lost (never punish learning).

### Roots prestige — AdCap sqrt
```
roots_earned = floor(3 * sqrt(lifetime_ohr / 1e6))
global_mult  = (1 + roots * 0.10) * (1 + words * 0.02) * promotion_mult
```
- First root at ~111k lifetime Ohr (~30–45 min at early rates). Feels fast if you know letters, still earned if you don't.
- Each root +10% everything (Realm Royal Exchange shape). Each mastered word +2% (AdCap Angels shape).
- Prestige resets Ohr + generator counts, keeps roots/words/tracks. Classic.
- Rule of thumb shown in UI: "Prestige when roots would at least double" (Idle Slayer 10–20% rule, generalized).

### Grammar promotion — Revolution table verbatim
4 tracks, exp costs double (1, 3, 7, 15, 31 …), mult requirements (1k, 4.3k, 13k, 37k …).
Spend 1 root per level. Effects:
- Dikduk Gain: +15% tap value / level
- Reading Speed: +10% per_sec / level
- Niqqud Power: +2% crit chance / level (cap +10%)
- Chochmah Power: +25% offline earnings / level

### Offline — Melvor + NGU split
```
earnings = per_sec_at_disconnect * min(elapsed, cap) * efficiency
cap = 12h (→ 24h after 10 roots)   efficiency = 0.5 (→ 1.0 via Chochmah)
```
Gear rule stolen from NGU: reviews only count online (active), generators always count offline (idle). No exploit, no guilt.

### Pacing targets (industry medians)
- First generator < 30s (Aleph costs 10, one tap ≈ 1–2)
- 5–10 purchases in first 10 min
- First automation (auto-review: FSRS due auto-collected at 50%) at 10–15 min
- First root prestige 30–90 min (fast path: tester who knows letters; slow path: real learner)
- Session: 3–8 min idle check + 5 min active review = the Slayer loop

## Learning integrity (non-negotiable)

A generator/word/root counts as **mastered** only when all three pass:
1. **H→E**: `What does '{hebrew}' mean?` (recognition)
2. **E→H**: `What is Hebrew for '{gloss}'?` / `Type the Hebrew word` (recall + production)
3. **Audio**: hear `{hebrew}` → choose or type (hearing mode)

This maps exactly onto existing FSRS `card_mode`s: `forward | reverse | hearing | drill`.
Quiz generation must interleave 40% H→E / 40% E→H / 20% audio. No direction may exceed 60% in any 10-question window (anti-gaming rule).

Audio chain (already built, just wire it):
`GET /hebrew/audio/{word}` → anki match → verse slice → alignment → `letters/{w}.wav` → `words/{w}.wav` (Kokoro TTS) → node fallback.
Every generator click plays its letter audio. Every card shows 🔊. Every prestige plays the root word. Browser `speechSynthesis (he-IL)` is the fallback, never the primary.

## Learning is the money (two-currency economy)

Most idle games sell speed for cash. Here there is no cash — **learning buys
speed**. Two currencies, strictly separated:

- **✨ Ohr** (time currency): flows from generators every second, buys more
  generators, spent on roots prestige. Waiting earns it. Patient, passive.
- **🌟 Kavod** (learning currency): earned ONLY by correct answers —
  1 base, +1 per 5 streak, +3 on crit. Cannot be idled, farmed, or bought.
  It purchases everything idle games put behind paywalls:
  - **🌬️ Ruach Frenzy** (20 🌟): x3 Ohr/sec for 60s. No stacking, no waste —
    refused while active. A focused 5-minute study session earns 1–2 frenzies.
  - **⏳ Time Warp** (30 → 90 → 270… 🌟): instantly grants 1h of production.
    The idle-game time-skip, priced in studying instead of dollars.

The whale is the diligent student. Anti-pay-to-win by construction: there is
literally nothing to pay.

## Mode choice: Classic vs Games (multi-game registry)

Hebrew learning offers both paths — the player chooses, never the app:
- **📖 Classic Study** (default): the curriculum dashboard exactly as before.
  Zero change for existing learners. Graded answers still feed the adaptive
  loop only when a game HUD is mounted; otherwise the events go unheard.
- **🎮 Games**: a shelf of games + the active game's HUD.
  Registry lives in `frontend/src/components/HebrewModePicker.jsx`
  (`HEBREW_GAMES`): to ship a game, append
  `{id, name, icon, tagline, available: true, Component}` — LearnView renders
  `getGame(activeGameId).Component` with `{curriculum}`. Locked entries render
  as 🔒-soon teasers (Desert Wanderer runner, Verb Slasher) so the roadmap is
  visible. Choice persists in localStorage (`hebrew-learn-mode`, `hebrew-game-id`).

## The gameplay loop (second-to-day)

Every timescale always has an answer to "what next?":
- **Seconds** — answer a review/quiz question → tap Ohr pops with a floater,
  crits splash ⚡x7, streaks climb toward the next milestone burst (5/10/25/50/100).
- **Minutes** — spend on letter generators (x1/x10/Max bulk, Cookie-standard),
  watch the next-generator + next-root progress bars fill, claim quests
  (8 short goals: first lamp → first root, all with Ohr rewards).
- **Tens of minutes** — forge a root (+10% forever), prestige, rebuild faster.
- **Days** — come back to a tap-to-claim offline haul (never silent), new
  quests, grammar promotion tracks. Offline cap 12h → 24h after 10 roots.

Studying IS the clicker: there is no separate "tap" button to grind —
the only way to tap is to answer correctly, in either direction, with audio.
Streaks reward focus; wrong answers only reset streak, never destroy Ohr.

## Trial scope (this week)

1. `lib/idle-game.js` — pure formulas (this doc, executable) + tests
2. `HebrewIdleBar.jsx` — Ohr counter, per-sec, tap button, prestige button, offline popup. localStorage only, no backend migration
3. Quiz interleave guard (40/40/20) + `audio_url` on every quiz question
4. One prestige: 3 mastered letters → root unlock animation
5. Balance log: record `lifetime_ohr, roots, time_to_first_root` for tuning

## Explicitly out

PaRDeS ascension, gematria exponents, village builder, runner minigame, chests, daily portal, leaderboards. Those are layer 3+. Win the core loop first.

## Adaptive difficulty (player-steered + self-tuning)

Two inputs, one knob (`bias ∈ [-1, 1]`, + = harder). The knob scales ONLY
economy pacing — generator costs, tap size, quiz timers. Mastery thresholds
(0.8), FSRS scheduling, and bidirectional/audio requirements NEVER move.
Learning stays honest; only the pacing adapts.

1. **Explicit feedback** — pace row under the HUD:
   😅 Too hard (−0.25) · 🙂 OK (decay toward neutral) · 😌 Too easy (+0.25).
   - Gentle (−1): 0.7x costs, 1.25x taps, 1.3x timers
   - Fierce (+1): 1.3x costs, 0.75x taps, 0.7x timers
2. **Implicit adaptation** — every graded answer (quiz + audio review) reports
   `{correct, responseMs}` via `reportIdleAnswer()`. Rolling 20-answer window:
   >90% accuracy hardens slowly, <60% eases fast (frustration costs more than
   boredom), 70–90% holds. Fast-correct (<2s) hardens a touch; slow-wrong
   (>20s) eases. Target band = flow channel, same idea as Kittens' bottlenecks
   and Antimatter's autobuyers-as-difficulty-relief.
3. **Readable, not hidden** — pace label (Gentle/Eased/Standard/Spicy/Fierce)
   + recent accuracy always visible. The player steers; the algorithm trims.

## Mobile-first rules

- HUD stacks vertically on phones; letter shop is 6-col with 52px touch
  targets → 11-col on sm+. All buttons ≥44px. `active:scale-95` for tap feel.
- No hover-dependent UI, no precision clicking (lesson from Incremancer:
  click-to-spawn pixel towns fail on touch — our recall is big buttons).
- Timers pause-friendly: typed answers are never force-submitted (quiz change).
- Next: PWA manifest (fullscreen, icons) + tap-to-claim offline modal in the
  Shark Game style ("while you slept your roots grew…") instead of silent grant.

## Open-source lineage (ideas, not code)

- **Incremancer** (the zombie/necromancer one, 2.4M Kongregate plays) —
  autonomous agents as production (letter-minions that "kill" ignorance),
  visible kills over abstract numbers, anti-farm prestige (first-clear per
  verse only), boss every 50 levels. NOTE: no license file = ideas only,
  never copy code.
- **A Dark Room** (MPL-2.0, 8.2k★) — staged reveal as tutorial: hide
  roots/verses until letters are mastered. Narrative IS onboarding.
- **Kittens Game** — prestige with diminishing returns, challenges with
  permanent rewards ("vowel-less challenge"), seasons as pacing.
- **Evolve Idle** (MPL-2.0) — i18n string system for Hebrew↔English; job
  reassignment = auto-easing struggling learners onto easier letters.
- **Swarm Simulator** (GPL-3.0) — twin resources gating each other
  (letters + recall-energy), spreadsheet-driven tuning for educators.
- **Shark Game** (MIT) — idle-detection tap-to-claim, producers with
  personality ("Dalet the door-guard"), world-switch = curriculum chapters.
- **Antimatter Dimensions** (MIT) — dimension cascade (letters make roots
  make words), autobuyers as earned relief, `break_infinity.js` for big numbers.

## Why this is NOT a Cookie Clicker clone

Genre math (exponential costs, sqrt prestige) is infrastructure, like chord
progressions — the game is the theme. Ours: Ohr/light theology, letters as
living minions, roots as forging, verses as bosses, audio + bidirectional
recall as the actual clicker input, adaptive pace the player steers. No
cookies, no grandmas, no document.cookie either — persistence is localStorage
(`hebrew-idle-v1`), server migration later.
