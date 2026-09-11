# Findings: Cookie-Clicker Hebrew clone

## Requirements (discovery answers, pre-resolved from prior sessions)
1. Goal: clone the most popular idle game with a Hebrew-learning theme, learning as currency.
2. Workstreams: Ohr core (A) · Kavod prestige+buffs (B) · retention (C) · analytics (D) · minigames future (E).
3. Pre-resolution: clone target = Cookie Clicker (composite #1; see verdict). Mechanics only — proprietary license, no assets/names/text/code.
4. Constraints: no new deps; localStorage trial first; mobile-first ≥44px; punishment ban (wrong answers never drain).
5. Acceptance: per-phase checkpoints (node self-check + vite build + event logged).
6. Out of scope: PaRDeS, gematria exponents, runner/chest minigames, leaderboards, minigame quartet (Track E).

## Verdict recap (research 2026-09-10)
- Cookie Clicker: 67.8k Steam peak, 93k reviews 94.9%, 2.55M Steam owners, 13y dominance.
- Monthly-slice leader IdleOn (9.7k avg) is one update spike; revenue leader AFK Arena ($1.5B) is gacha not incremental; Bongo Cat (150k+) has no progression to clone.
- Exact public formulas available: 1.15 growth, CpS table, prestige cube-root, buff multipliers.

## Architecture notes
- Existing: `frontend/src/lib/idle-game.js` (pure formulas + 39-assert self-check), `components/HebrewIdleBar.jsx` (HUD+loop), `components/HebrewModePicker.jsx` (Classic/Games registry), `components/HebrewQuiz.jsx` (grading, reports answers), `web/routes/hebrew.py` (SRS backend).
- Ohr/Kavod split already live: Ohr ticks, Kavod mints on correct answers only; Frenzy (20🌟 x3/60s) + Time Warp (30·3^n 🌟/1h) shipped.
- Analytics attaches at `reportIdleAnswer` (central event bus) + IdleBar action handlers; mode/game tags read from localStorage keys.
- Backend analytics table deferred to D3; local ring buffer first (offline-safe, no migration).

## Open questions → resolved
- Q: Which "most popular" metric? → A: composite (peak+reviews+longevity+clonability) = Cookie Clicker. Documented alternatives in research report.
- Q: Copy art/text? → A: never. Mechanics only; Hebrew-original names (Etzba, Savta, Aliyah, Shemen, Talmidim).
- Q: Reflex gates (golden cookie 13s)? → A: replaced by 20s accuracy windows; fails fizzle, never punish.
- Q: Backend quiz interleave (40/40/20 + audio_url)? → A: still pending, independent of this plan; do before B2.
- Q: Legal review before art commission? → A: flagged as follow-up; mechanics reimplementation is the plan's basis.
