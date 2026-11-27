# Findings: Scripture Feed

## Devote-style target (assumed, confirm in review)
Devote-like = daily verse card + devotional snippet + topic/mood browse + streaks + share image + save/journal. Cloned as: FeedCard (verse + reflection prompt + why-this-verse), topic/mood chips, daily pinned, streak counter (no-anxiety copy), share/save/skip, audio. No social graph, no LLM devotional at request time in v1.

## Open-source algorithms selected (with rationale)
- **Reddit Hot** (`hot.py`, Apache-licensed, public): `score = log10(max(|s|,1)) + sign(s)*t/45000` where `s = ups-downs`, `t = epoch_seconds - 1134028003`. Chosen because it is the canonical open time-decayed engagement ranker, trivially portable to stdlib `math`, and explainable. Maps to: ups = saves+likes+shares+long-dwells, downs = skips/hides.
- **Wilson score lower bound** (Wilson 1927, standard statistics, public domain math): ` (p̂ + z²/2n − z√(p̂(1−p̂)/n + z²/4n²)) / (1+z²/n)`. Chosen to rank high-confidence loved verses above low-sample flukes. `pos` = likes+saves+shares, `n` = all ratings.
- **HN gravity** (`arc` ranking, public): `score = points / (age_hours+2)^1.8`. Kept as comparator/fallback and exploration ranker; simple to A/B against hot.
- **MMR diversity** (Carbonell & Goldstein 1998, published algorithm): `MMR = λ·Rel − (1−λ)·maxSim`, λ=0.7. Penalizes same-book/entity/pericope runs.
- All constants (45000, 1.8, z=1.96, λ=0.7, N=14d freshness) documented in `docs/feed-algorithm.md` (Track C3) with worked examples.

## Why this fits ScriptureEngine
- Graph gives a strong cold-start prior (`log(1+connections)`, star-weight, entity richness, consensus) so the feed is good before any user data — unlike pure engagement rankers.
- Existing `lookup_verse`, `lookup_verses` (batch), `graph_reachable`, `query_cache`, `DailyVerse` audio pattern, and `memorize.db` session keys mean no new infra.
- Quality calibration + tradition labels satisfy the pastoral guardrail requirement that raw Reddit/HN lack.

## Risks
- Ancient verses all "old" → solved by time-base = lectionary/publish date + freshness window, not row age.
- Wilson too conservative at low n → fallback to Laplace-smoothed mean, flagged.
- Feedback sparsity → cold-start lectionary + top-centrality shuffle; anon device-seed deterministic.

## Outside-canon inventory (from `works` table, verified 2026-11-26)
- Canon default: ot, nt, bom, dc, pgp.
- Opt-in scripture-adjacent: apoc (Apocrypha), dss (Dead Sea Scrolls), pseu/pseudepigrapha (Pseudepigrapha incl. 1 Enoch — verse IDs like `1en.x.y` already in DB), expanded (Early Christian & Patristic).
- Scholar/context-only (never verse-ranked by default, Scholar-lane cards only): josephus, philo, hellenistic_jewish, ane_texts, targums, mishnah, sibylline_oracles, nag_hammadi, ugaritic_texts.
- Implementation: `works` table is the allowlist source of truth; `books.work` (verify column name in Phase A1) filters candidates pre-rank so outside texts can't leak into canon-only mode. Card must show `work` + human label (e.g. `DSS · Community Rule`) + scholar source from `get_sources_for_verse`.
