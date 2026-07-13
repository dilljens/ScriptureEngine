# Assessment Engine

Adaptive quiz engine with item response theory, Bayesian knowledge state tracking, and 247 assessment questions across 3 tiers.

## Architecture

```
lib/assessment/                      lib/api/assessment.py (670 lines)
    __init__.py (41 lines)                     │
    engine.py    (256 lines)                   ├── start_assessment()  — BLIM item selection
    models.py    (143 lines)                   ├── submit_answer()    — Bayesian update + FIRe
    items.py     (DeepQuestionGenerator)       └── get_progress()     — mastery stats
                                               
web/routes/assessment.py (208 lines)
    ├── GET  /api/v1/quiz                      — new adaptive quiz endpoint
    ├── POST /api/v1/quiz/answer               — record answer + update progress
    ├── POST /api/v1/assessment/start          — legacy BLIM-based session start
    ├── POST /api/v1/assessment/answer         — legacy answer submission
    └── GET  /api/v1/assessment/progress       — legacy session progress
```

## Adaptive Quiz Engine

Two assessment paths:

### 1. New Quiz Endpoint (`/api/v1/quiz`)

Serves questions from the `assessment_items` table with adaptive ordering:

- **Unseen first**: questions the user hasn't attempted are prioritized
- **Weakest first**: lowest accuracy questions come next
- **Tier filtering**: `?tier=text`, `?tier=analysis`, `?tier=consistency`, or comma-separated combinations
- **Bloom level filtering**: `?bloom_level=analyze` narrows by cognitive level
- **Progress tracking**: per-question accuracy stored in `quiz_progress` table

Answer recording at `POST /api/v1/quiz/answer` upserts accuracy stats and timestamps.

### 2. Legacy BLIM Assessment (`/api/v1/assessment/*`)

Full adaptive session powered by the lib-based assessment engine:

- **Item selection**: maximum information criterion with outer fringe boost (items at 30-70% mastery get 1.5x boost)
- **Bayesian update**: BLIM model updates mastery probability after each response
- **Prerequisite propagation**: mastering a high-level item (mastery > 0.8) boosts prerequisites to 0.5; failing a prerequisite (mastery < 0.2) suppresses postrequisites to 0.3
- **Termination**: stops when entropy converges (< 0.1), minimum items met (3), or maximum reached (default 20)

## Question Inventory

| Tier | Description | Count |
|------|-------------|-------|
| Text | Factual recall of verse content | ~80 |
| Analysis | Understanding connections and meaning | ~80 |
| Consistency | Cross-canon thematic consistency | ~87 |
| Total | 200 MC + 47 LLM-graded open-ended | **247** |

Questions are stored in the `assessment_items` table with fields: `question_type`, `question_text`, `options_json`, `correct_answer`, `bloom_level`, `tier`, `explanation`, `question_type_open`.

## LLM-Graded Open-Ended Questions

47 open-ended questions use an LLM grader with a 4-dimension rubric:

1. **Accuracy** — does the answer reflect scripture correctly?
2. **Completeness** — does it cover the key aspects?
3. **Analysis** — does it demonstrate understanding beyond recall?
4. **Consistency** — does it harmonize cross-canon evidence?

Partial credit via the `correctness` parameter (0.0-1.0) enables weighted scoring for multiple-choice distractors and nuanced LLM grading.

## Student-Topic Learning Speeds

The quiz endpoint tracks per-topic ability/difficulty ratios. The ratio governs how quickly a student moves through the spaced repetition schedule:

- Speed > 1.0: longer intervals (fast learner)
- Speed < 1.0: shorter intervals (slow learner)
- Formula: `speed = (correct_ratio * 1.5) / max(difficulty_penalty, 0.5)`

## Integration with Learning Modules

The quiz system feeds into the Learn system:

- `module_questions` table links learning modules to assessment questions
- Practice answers submitted via `/api/v1/learn/modules/{id}/practice` update `quiz_progress` and `learning_progress` simultaneously
- Review scheduling uses FSRS-5 stability/difficulty tracking

## BLIM Model

The Basic Local Independence Model (in `lib/assessment/models.py`) implements 2PL IRT:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| Difficulty (beta) | 0.0 | Higher = harder item |
| Discrimination (alpha) | 1.0 | How well item separates ability levels |
| Guess (g) | 0.15 | P(correct | not mastered) |
| Slip (s) | 0.10 | P(wrong | mastered) |

Discrimination scales with PaRDeS level: P'shat=1.0, Remez=1.2, Drash=1.5, Sod=2.0.

## KnowledgeState

Per-user mastery tracking across items:

- `mastery_prob[item_id]` — P(mastered) in [0, 1]
- `times_correct[item_id]` — success count
- `times_wrong[item_id]` — failure count
- `overall_mastery()` — mean across all items
- `mastery_by_layer(conn)` — grouped by PaRDeS level

Persisted to `~/.cache/scriptureengine/assess_sessions.json` for CLI resilience.

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/quiz` | GET | Get adaptive quiz questions (tier/bloom filtered) |
| `/api/v1/quiz/answer` | POST | Record answer + update progress |
| `/api/v1/assessment/start` | POST | Start BLIM-based adaptive session |
| `/api/v1/assessment/answer` | POST | Submit answer, get next question |
| `/api/v1/assessment/progress` | GET | Current session mastery stats |

## Path Scope

- `web/routes/assessment.py` — 208 lines, quiz + assessment endpoints
- `lib/api/assessment.py` — 670 lines, MCP tools for assessment sessions
- `lib/assessment/engine.py` — 256 lines, BLIM engine with item selection + propagation
- `lib/assessment/models.py` — 143 lines, KnowledgeState + BLIM IRT model
- `lib/assessment/items.py` — DeepQuestionGenerator for auto-generating items

## Git History

- `e202263` — Question quality: LLM open-ended grading, Hebrew improvements, UI fixes
- `d25c21f` — Knowledge consolidation: Learn system, Memorize queue, Auth, Wiki expansion
- `479177e` — Dedicated assessment UI + engine fixes + vocabulary enhancement

## Related

- [MEMORY.md](../MEMORY.md) — Assessment questions count (line 15), Learn system overview (section)
- [plans/knowledge-assessment-plan.md](../plans/knowledge-assessment-plan.md) — Full Track C plan: domain definition, prerequisite graph, IRT calibration, study recommendations
- [plans/math-academy-way-reference.md](../plans/math-academy-way-reference.md) — FIRe, mastery learning, interleaving reference
- [features/learn.md](learn.md) — Learn system integration
- [features/lib-core.md](lib-core.md) — Database, connection graph

_Last updated: 2026-07-13_
