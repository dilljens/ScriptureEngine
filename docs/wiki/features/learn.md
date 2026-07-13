# Learn System

Structured courses following The Math Academy Way: 26 modules with direct instruction, worked examples, adaptive practice, and FSRS-5 spaced repetition.

## Architecture

```
web/routes/learn.py (468 lines)
        │
        ├── GET  /api/v1/learn/modules               — list all modules with progress
        ├── GET  /api/v1/learn/modules/{id}           — full module: lesson + examples + practice
        ├── POST /api/v1/learn/modules/{id}/practice  — submit practice answer
        ├── GET  /api/v1/learn/review                 — due reviews (FSRS-scheduled)
        └── POST /api/v1/learn/review/{id}            — submit review rating (future)
```

## Module Inventory

26 modules in two groups:

### 14 Hub Note Modules (from curated learning paths)

| Module | Theme | Difficulty |
|--------|-------|------------|
| `covenant` | The covenant thread: Noah, Abraham, Moses, David, Christ | 1 |
| `temple` | Eden to Tabernacle to Temple to Body of Christ | 2 |
| `exodus` | The Exodus as redemption pattern | 2 |
| `atonement` | Why Jesus had to die | 3 |
| `lamb_of_god` | The Lamb throughout scripture | 3 |
| `angel_of_the_lord` | Malach YHWH appearances | 3 |
| `wisdom` | Wisdom literature and Christ as Wisdom | 3 |
| `son_of_man` | Son of Man in Daniel, Enoch, Gospels | 4 |
| `zion` | Zion from Genesis to Revelation | 4 |
| `priesthood` | Priesthood: Melchizedek, Aaron, Christ | 4 |
| `faith_unto_salvation` | Faith and salvation across the canon | 4 |
| `restoration` | Restoration theme: OT prophets through D&C | 5 |
| `garden_to_city` | Garden of Eden to New Jerusalem | 5 |
| `dispensations` | Gospel dispensations across scripture | 5 |

### 12 Topical Guide Modules

Thematically-rich doctrinal topics from the LDS Topical Guide with 20+ verse references each, ordered by verse count descending (e.g., `tg_atonement-of-jesus-christ`, `tg-resurrection`, `tg-holy-ghost`).

## Three-Tier Question System

| Tier | Focus | Question Count |
|------|-------|----------------|
| **Text** | Factual recall of scripture content | ~80 |
| **Analysis** | Understanding connections and meaning | ~80 |
| **Consistency** | Cross-canon thematic synthesis | ~87 |

Questions come from the `assessment_items` table and are linked to modules via `module_questions`. Each module gets 5-7 questions (mix of multiple-choice and LLM-graded open-ended).

## Adaptive Ordering

Practice questions within each module are ordered weakest-first:

1. Questions never attempted (new)
2. Questions with lowest accuracy rate
3. By sort order (stable tiebreaker)

This implements Math Academy's **outer fringe targeting** — the system fights the student's weakest areas.

## Module Structure

Each module contains:

1. **Direct instruction** — lesson content built from hub note steps (verse citations, explanations, and connection types)
2. **Worked examples** — up to 4 real verse examples from the Topical Guide or hub note links
3. **Adaptive practice** — MC and open-ended questions from `assessment_items`
4. **Wiki enrichment** — related wiki articles appended to lesson content (matched by title)

Hub note modules seed their lesson content by iterating hub_note_steps: each step contributes its verse text and explanation, formatted as markdown with verse references.

Topical Guide modules use the topic's description and verse count for lesson content, with worked examples drawn from the topic's verse references.

## FSRS-5 Review Scheduling

The `learning_progress` table tracks per-module FSRS parameters:

- **mastery** (0.0-1.0): accuracy ratio
- **stability**: memory strength
- **difficulty**: per-module difficulty estimate
- **last_review / next_review**: review timing

The review endpoint (`GET /api/v1/learn/review`) returns modules where retrievability < 0.8, sorted by last review ascending (most forgotten first). Retrievability uses the same exponential decay: R = e^(-t/s).

Modules are considered mastered at mastery >= 0.8 and removed from the review queue.

## Integration Points

| Component | Integration |
|-----------|-------------|
| **Hub Notes** | 14 curated learning paths seed module content and worked examples |
| **Topical Guide** | 12 doctrinal topics with 20+ verses each become TG modules |
| **Assessment System** | All practice questions sourced from `assessment_items` via `module_questions` |
| **Wiki Articles** | Related wiki content appended to lesson material |
| **Memorize Queue** | Macro-interleaving endpoint combines learn + memorize + hebrew reviews |
| **Connection Graph** | Prerequisite relationships implicit across modules |

## Data Model

**learning_modules**: `id`, `title`, `description`, `category`, `icon`, `difficulty`, `prerequisite_ids`, `lesson_content`, `worked_examples`, `estimated_minutes`, `sort_order`

**module_questions**: `module_id`, `question_id`, `is_required`, `sort_order`

**learning_progress**: `user_id`, `module_id`, `mastery`, `attempts`, `correct`, `stability`, `difficulty`, `last_review`, `next_review`

Modules are seeded on first access via `seed_modules()`. The seeder checks for existing modules before inserting — safe to call repeatedly.

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/learn/modules` | GET | List all modules with per-user progress |
| `/api/v1/learn/modules/{id}` | GET | Full module content + questions |
| `/api/v1/learn/modules/{id}/practice` | POST | Submit answer, update progress |
| `/api/v1/learn/review` | GET | Due module reviews (retrievability < 0.8) |

## Path Scope

- `web/routes/learn.py` — 468 lines, all endpoints + module seeding + FSRS
- `data/processed/scripture.db` — learning_modules, module_questions, learning_progress tables
- `lib/assessment/` — question source (`assessment_items` table)

## Git History

- `e202263` — Question quality: LLM open-ended grading, Hebrew improvements, UI fixes
- `d25c21f` — Knowledge consolidation: Learn system, Memorize queue, Auth, Wiki expansion

## Related

- [MEMORY.md](../MEMORY.md) — Learn section (lines 48-54), module count (line 13), hub notes (line 14)
- [plans/knowledge-assessment-plan.md](../plans/knowledge-assessment-plan.md) — Assessment system that feeds Learn practice
- [plans/math-academy-way-reference.md](../plans/math-academy-way-reference.md) — Knowledge graph, mastery learning, interleaving reference
- [plans/card-based-learning.md](../plans/card-based-learning.md) — Card queue architecture shared with Learn
- [features/assessment.md](assessment.md) — Question inventory and grading
- [features/lib-core.md](lib-core.md) — Database schema

_Last updated: 2026-07-13_
