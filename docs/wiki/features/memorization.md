# Memorization System

Verse memorization queue with FSRS-5 spaced repetition, FIRe implicit credit, repetition compression, palace-guided ordering, and graph centrality optimization.

## Architecture

```
web/routes/memorize.py (928 lines)
        │
        ├── GET  /api/v1/memorize/queue           — list queued verses
        ├── POST /api/v1/memorize/queue            — add a verse
        ├── DELETE /api/v1/memorize/queue/{id}     — remove a verse
        ├── POST /api/v1/memorize/queue/batch      — add chapter or verse range
        ├── GET  /api/v1/memorize/review           — due reviews (sorted by retrievability)
        ├── POST /api/v1/memorize/review/{id}      — submit rating (FSRS-5 + FIRe)
        ├── GET  /api/v1/memorize/suggest          — graph centrality suggestions
        ├── GET  /api/v1/review/interleaved        — macro-interleaving across areas
        ├── GET  /api/v1/review/next               — non-interference scheduling
        └── GET  /api/v1/review/weakest            — targeted remediation
```

## FSRS-5 Scheduling

The same Free Spaced Repetition Scheduler v5 (21-parameter model) used by the Hebrew curriculum drives verse memorization:

- **Stability**: memory strength, grows with successful reviews
- **Difficulty**: per-verse estimate (1.0-10.0), initialized from graph centrality
- **Retrievability**: probability of recall, computed as R(t) = e^(-t/s)
- **Mastery**: accuracy ratio (correct / attempts), 0.0-1.0

Most-forgotten-first ordering: the review queue sorts by retrievability (ascending) so verses closest to being forgotten are shown first.

## Rating

| Rating | Name | Behavior |
|--------|------|----------|
| 1 | Again | Complete failure — stability collapses, difficulty rises |
| 2 | Hard | Partial recall — stability grows minimally |
| 3 | Good | Successful recall — standard stability growth |
| 4 | Easy | Effortless recall — maximum stability growth |

Ratings flow through `_fsrs_schedule()` which computes new stability, difficulty, and next interval.

## FIRe (Fractional Implicit Repetition)

Two-way FIRe credit/penalty flow through the connection graph:

**Success flow** (rating >= 3): credit flows from complex verses to simpler connected verses. When a user reviews John 1:1 (which quotes Gen 1:1), Gen 1:1 receives fractional implicit credit. When `fi_re_credit >= 1.0`, the connected verse's due review is skipped (knocked out) — its interval is extended as if a "Good" review happened.

**Failure flow** (rating < 3): penalty flows from simpler verses to complex dependents. Failing Gen 1:1 reduces the stability of John 1:1 (which depends on it). Penalty is proportional to connection strength and rating severity (Again = full penalty, Hard = 0.3x).

**Summer slide**: credit decays exponentially with time, accelerating when overdue (decay rate doubles every 30 days overdue).

## Repetition Compression

The `compress=True` flag on the review endpoint groups connected due cards together. Verses sharing connection graph edges appear consecutively in the review queue, mimicking Math Academy's "recite passage" flow. Connected cards are detected via SQL `WHERE (source=a AND target=b) OR (source=b AND target=a)` against the connections table.

## Palace-Guided Ordering

When `palace_order=True`, due reviews are sorted by memory palace loci from the `memorize.db` palaces/loci system. Palace-ordered verses appear first (sorted by palace name, then locus label), then remaining verses by retrievability. Each review response includes `palace` and `locus` fields when applicable.

## Graph Centrality Optimization

The suggest endpoint (`/api/v1/memorize/suggest`) identifies the best-connected verses not yet in the user's queue. Verses with more connections have lower initial difficulty (more memorable), and are recommended first. This prioritizes high-value verses that will unlock many connections via FIRe.

Difficulty is mapped from connection count:
- 0 connections -> difficulty 8.0 (very hard)
- 100+ connections -> difficulty 2.0 (very easy)

## Macro-Interleaving

`/api/v1/review/interleaved` pulls due cards from all three areas (memorize, hebrew, learn) and interleaves them with no more than 2 consecutive cards from the same source. Implements Math Academy Ch 19: interleaving across topics doubles retention.

## Non-Interference

`/api/v1/review/next` ensures confusable verse pairs do not appear consecutively. Interference is detected via connection graph strength (>0.7 = moderate interference) and the `hebrew_confusability` table. Cards with interference > 0.4 are skipped.

## Targeted Remediation

`/api/v1/review/weakest` returns verses with lowest accuracy rates and most failed attempts, ordered by accuracy ascending and failures descending. Implements Math Academy Ch 21: target weak areas first.

## Student-Topic Learning Speeds

Per-user, per-verse learning speed calibration (`compute_learning_speed`). Formula (Math Academy Ch 29):

```
speed = (correct_ratio * 1.5) / max(difficulty_penalty, 0.5)
```

- Clamped to [0.3, 3.0]
- Fast learners (speed > 1.0) get longer intervals
- Slow learners (speed < 1.0) get shorter intervals
- Difficulty is adjusted by speed before FSRS computation

## Data Model

Two tables, both in `scripture.db`:

**memorize_queue**: `id`, `user_id`, `verse_id`, `chapter_id`, `added_at`

**memorize_progress**: `user_id`, `verse_id`, `mastery`, `attempts`, `correct`, `stability`, `difficulty`, `fi_re_credit`, `last_review`, `next_review`

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/memorize/queue` | GET | List queued verses with progress |
| `/api/v1/memorize/queue` | POST | Add a verse to queue |
| `/api/v1/memorize/queue/{id}` | DELETE | Remove from queue |
| `/api/v1/memorize/queue/batch` | POST | Add chapter or verse range |
| `/api/v1/memorize/review` | GET | Due reviews (sorted by retrievability) |
| `/api/v1/memorize/review/{id}` | POST | Submit FSRS-5 rating |
| `/api/v1/memorize/suggest` | GET | Graph centrality suggestions |
| `/api/v1/review/interleaved` | GET | Cross-area interleaved review |
| `/api/v1/review/next` | GET | Non-interference next card |
| `/api/v1/review/weakest` | GET | Targeted weakest-first remediation |

## Path Scope

- `web/routes/memorize.py` — 928 lines, all endpoints
- `data/processed/scripture.db` — queue + progress tables
- `data/memorize.db` — palaces + loci table (for palace ordering)

## Git History

- `d54b089` — Phase 3: Student-topic learning speeds, Mukdam u'Meuchar
- `6957d4f` — Phase 3 completion: FIRe penalty flow, macro-interleaving, non-interference, targeted remediation, summer slide
- `4e16617` — Phase 3: FIRe enhancements, repetition compression, palace-guided ordering, graph centrality
- `d25c21f` — Knowledge consolidation: Learn system, Memorize queue

## Related

- [MEMORY.md](../MEMORY.md) — Memorize Queue section (lines 75-80), Hebrew FSRS-5 section
- [plans/memorization-enhancements.md](../plans/memorization-enhancements.md) — FIRe, compression, palace, centrality plans
- [plans/math-academy-way-reference.md](../plans/math-academy-way-reference.md) — FSRS-5, FIRe, interleaving reference
- [plans/card-based-learning.md](../plans/card-based-learning.md) — Card queue architecture
- [features/lib-core.md](lib-core.md) — Database, connection graph

_Last updated: 2026-07-13_
