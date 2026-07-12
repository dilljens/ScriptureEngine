# Scripture Engine — Master Execution Plan

> Consolidated from: `task_plan.md`, `study-sharing-plan.md`, `knowledge-assessment-plan.md`,
> `memorization-task-plan.md`, `memorization-enhancements.md`, `hebrew-teaching-plan.md`,
> `llm-lexicon-plan.md`, `agent-connections.md`, `rabbinic-kabbalistic-tools.md`,
> `original-architecture-plan.md`, `implementation-review.md`
>
> **Total backlog: ~40h remaining | Phases 0-4 ✅ | Phase 5: ~4h | Phase 6: ~15h | Phase 7: ~20h**

## Priority Key
- 🔴 **P0**: Blocking / foundational — do first
- 🟡 **P1**: High user impact — soon
- 🟢 **P2**: Medium value — when Phase 1 done
- ⚪ **P3**: Nice to have

---

## Phase 0: Infrastructure & Gate (🔴 P0 — ~30m remaining)

> Testing infrastructure, deploy gate, health monitoring.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 0.1 | Wire pytest + FastAPI TestClient for API tests | `task_plan.md` P1.1 | 1h | ✅ |
| 0.2 | 10+ core API endpoint tests (verses, search, gematria, graph, quiz) | `task_plan.md` P1.2 | 2h | ✅ (39 tests) |
| 0.3 | DB schema + integrity tests (no orphaned refs, no duplicates) | `task_plan.md` P1.3 | 1h | ✅ |
| 0.4 | Graph regression tests (layer counts, quality levels, traditions) | `task_plan.md` P1.4 | 1h | ✅ |
| 0.5 | API contract snapshot (OpenAPI diff test) | `task_plan.md` P1.5 | 1h | ✅ |
| 0.6 | Wire deploy.sh gate — E2E tests + OpenAPI snapshot added | `task_plan.md` P1.6 | 30m | ✅ |
| 0.7 | Enhanced health endpoint (DB integrity, cache status, version, uptime) | `task_plan.md` P2.1 | 1h | ✅ |
| 0.8 | Structured JSON logging (replace `print()`) | `task_plan.md` P2.2 | 1h | ✅ |
| 0.9 | ntfy.sh push notifications on health failure | `task_plan.md` P2.3 | 30m | ⏳

---

## Phase 1: Study Sharing & Publishing (🟡 P1 — ~7h remaining)

> Publish/fork/export cycles for study guides, interactive viewer, editor.

### Backend API (`~8h` — ✅ COMPLETE)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 1.1 | `POST /api/v1/studies/{guide_id}/publish` | `study-sharing-plan.md` A2 | 1h | ✅ |
| 1.2 | `GET /api/v1/studies/published/{slug}` | A2 | 30m | ✅ |
| 1.3 | `GET /api/v1/studies/published/{slug}.json` — JSON download | A2 | 30m | ✅ |
| 1.4 | `GET /api/v1/studies/published/{slug}.html` — self-contained HTML export | A2, A3 | 3h | ✅ |
| 1.5 | `GET /api/v1/studies/published` — list published | A2 | 30m | ✅ |
| 1.6 | `POST /api/v1/studies/published/{slug}/fork` — fork | A2 | 1h | ✅ |
| 1.7 | `POST /api/v1/studies/import` — import from JSON | A2 | 1h | ✅ |

### Frontend — StudyViewer (`~10h` — ✅ COMPLETE)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 1.8 | StudyViewer: render steps with graph paths, expand/collapse, layer toggles | B1 | 4h | ✅ |
| 1.9 | Inline Quick Ask bar (LLM question scoped to study context) | B2 | 2h | ✅ |
| 1.10 | `showQuickAsk` setting toggle in SettingsPanel | B3 | 30m | ✅ |
| 1.11 | Clickable verse refs → VersePreviewCard in study steps | B1 | 1h | ✅ |
| 1.12 | `/study/{slug}` standalone page route (via `?study=` param) | D1 | 2h | ✅ |

### Frontend — StudyEditor (`~7h` — ✅ COMPLETE)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 1.13 | StudyEditor: create/edit study form with step management | C1 | 3h | ✅ |
| 1.14 | Preview mode (renders via StudyViewer) | C1 | 1h | ✅ |
| 1.15 | Save as draft (not needed — API persists) | C1 | 1h | ✅ (wontfix) |
| 1.16 | Import JSON (file picker + drag-and-drop) | C2 | 1h | ✅ |
| 1.17 | Export as JSON download | C2 | 30m | ✅ |

---

## Phase 2: Knowledge Assessment & Truth-Seeking (🟡 P1 — ~5h remaining)

> Hebrew/Greek tooling, interpretive bias infrastructure, assessment engine.

### Track A — Language Tooling (`~12h` — ✅ COMPLETE)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 2.1 | Greek transliteration (`lib/greek_util.py`, 99 lines) | A1 | 2h | ✅ |
| 2.2 | Morphological parser (`lib/morphology.py`, 417 lines) | A2 | 3h | ✅ |
| 2.3 | Strong's definitions import (lexicon table populated) | A3 | 3h | ✅ |
| 2.4 | Interlinear display tool (`lib/api/interlinear.py`, 106 lines) | A4 | 4h | ✅ |

### Track B — Truth-Seeking (`~17h`)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 2.5 | **Real null-text testing** — empirical p-values, `null_text.py` (130 lines) + `null_text_validation.py` (697 lines) | B1 🔴 | 6h | ✅ |
| 2.6 | Interpretive disagreement model — DB table (140 rows), MCP tool, REST endpoint, frontend panel, 20 real seeds | B2 | 4h | ✅ |
| 2.7 | Faith vs. historical-critical hermeneutic labels — tradition/hermeneutic added to verse connection output, badges in VerseBlock panel, KnowledgeGraph display | B3 | 3h | ✅ |
| 2.8 | Ecumenical consensus scoring per verse | B4 | 4h | ❌ |

### Track C — Assessment Engine (`~50h, Phase 2 subset ~11h`)
| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 2.9 | Knowledge domain definition (~15K atomic items from high-quality connections) | C1 | 3h | ❌ |
| 2.10 | Prerequisite graph (~300 rules across connection types + PaRDeS) | C2 | 6h | ❌ |
| 2.11 | Adaptive assessment engine (BLIM + Bayesian state update) | C3 | 10h | ❌ |
| 2.12 | Auto-generate 1K+ assessment items from connections | C4 | 8h | ❌ |
| 2.13 | IRT calibration (difficulty, discrimination, guess, slip) | C5 | 6h | ❌ |
| 2.14 | FSRS-based spaced repetition for assessment | C6 | 6h | ❌ |
| 2.15 | User progress tracking + dashboard | C7 | 8h | ❌ |
| 2.16 | Study recommendations from gap analysis | C8 | 6h | ❌ |

---

## Phase 3: Memorization & Engagement (🟢 P2 — ~47h)

> FIRe, repetition compression, palace-guided review, connection-aware difficulty.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 3.1 | FIRe: `fi_re_credit` column in memorize_progress | F1.1 | 30m | ✅ |
| 3.2 | FIRe: on review, propagate credit to connected verses via graph | F1.2 | 3h | ✅ |
| 3.3 | FIRe: credit ≥ 1.0 knocks out due review (extends interval) | F1.3 | 2h | ✅ |
| 3.4 | FIRe: credit decay over time (10%/day) | F1.4 | 1h | ✅ |
| 3.5 | Repetition compression — connected due cards grouped together | F2 | 4h | ✅ |
| 3.6 | Palace-guided review ordering | F3 | 4h | ✅ |
| 3.7 | Graph centrality suggestion (`/api/v1/memorize/suggest`) | F4 | 3h | ✅ |
| 3.8 | Connection-aware difficulty estimation | F5 | 3h | ✅ |
| 3.9 | Hebrew verb conjugation drills frontend (`HebrewVerbDrill.jsx`) | hebrew-plan | 4h | ✅ |
| 3.10 | Mukdam u'Meuchar expansion | rabbinic-plan | 3h | ✅ |
| 3.11 | Sefirotic mapping | rabbinic-plan | 4h | ❌ |
| 3.12 | Decay model for overdue reviews (summer slide) | implementation-review | 3h | ✅ |
| 3.13 | Multi-mode FIRe | implementation-review | 8h | ⏳ partial (Hebrew + Memorize separate) |
| 3.14 | Macro-interleaving across works | implementation-review | 3h | ✅ |
| — | Literary pattern detection — 6 types built | new | 8h | ✅ |
| — | Additional patterns documented | new | 18h | 📝 |
| 3.15 | Student-topic learning speeds calibration | implementation-review | 3h | ✅ |

---

## Execution Order

```
Week 1:    0.1–0.9 (deploy gate + test infra)             8h
Week 2:    1.1–1.7 (study sharing backend)                 8h
Week 3:    1.8–1.12 (StudyViewer frontend)                 10h
Week 4:    1.13–1.17 (StudyEditor + import/export)         7h
Week 5-6:  2.1–2.4 (language tooling)                      12h
Week 7-8:  2.5–2.8 (truth-seeking)                         17h
Week 9+:   2.9–2.16 (assessment engine)                    50h
Interleaved: 3.1–3.15 (memorization enhancements)           47h
```

---

### Markdown Syntax System — Phase A-D complete
- **`frontend/src/lib/scripture-markdown.jsx`** — unified preprocessing module for `:verse[]`, `:entity[]`, `:gematria[]`, `:strong[]`, `:conn[]` inline syntax
- Wired into WikiArticleViewer, ChatPanel, and LearnView
- Replaced both `verse://` protocol (wiki) and `%%%VERSE:` markers (chat)
- All generators updated to emit `:verse[...]` syntax

### Hebrew Verb Drills — `HebrewVerbDrill.jsx`
- Interactive verb conjugation practice with category selector (Qal, Niphal, Piel, Hiphil, Weak Verbs, All)
- Multiple-choice questions from `/api/v1/hebrew/verb-drill` endpoint
- Progress tracking, explanations, category switching
- Wired into HebrewLearnView as a "Verb Drills" button

### Card-Based Learning System — Phases 1-6 ✅, 7 planned
- **`CardQueue.jsx`** — generic card engine: show one card, click to reveal, rate 1-4 (Again/Hard/Good/Easy), auto-advance, progress bar, completion stats. Supports `onAnswer` callback for interactive card types (textarea input, MC selection before rating)
- **`CardRenderer.jsx`** — 9 card type renderers: `verse`, `knowledge`, `connection`, `gematria`, `vocab`, `drill`, `study_step`, `hebrew_letter`, `learn_question`
- **`card-factory.js`** — converts any content (lessons, wiki, hebrew, connections, gematria, studies, drills) into generic cards
- **LearnView** — practice mode now uses CardQueue with `learn_question` card type. Supports MC + open-ended with LLM grading. Independent from Hebrew/Memorize.
- **HebrewLearnView** — "Review Mode" button converts unlocked nodes to `hebrew_letter`/`vocab` cards via CardQueue. Independent from Learn/Memorize.
- **MemorizeView** — refactored to use CardQueue for verse review. Independent from Hebrew/Learn.
- **`docs/wiki/plans/card-based-learning.md`** — full architecture plan with per-area separation diagram

### Structured JSON Logging

### Structured JSON Logging
- JSONLogger replaces all `print()` startup logging with structured JSON
- Request timing middleware (logs slow requests >2s)
- Cache loading events logged as `{"level":"info","msg":"Cache loaded","cache":"verses","count":70956}`

### Deploy Gate
- E2E Playwright tests + OpenAPI snapshot now run before deploy
- 5-step validation: pytest → graph regression → DB integrity → API contract → E2E tests

## Full System Status

| Area | Status |
|------|--------|
| **Infrastructure** | ✅ Deploy gate, structured logging, health endpoint, 39 Python tests, 32 E2E tests |
| **Graph DB** | ✅ 1,769,494 connections, 11 layers, 60 MCP tools, entities, gematria, lexicon |
| **Wiki** | ✅ 20 articles, search/browse/concordance endpoints |
| **Hebrew teaching** | ✅ 102-node curriculum, diagnostic, quiz, FSRS-5, gamification, verb drills, interleaved review |
| **Memorization** | ✅ FSRS-5, palaces, hints, audio, FIRe credit flow |
| **Study guides** | ✅ Full backend (create/publish/fork/export) + StudyViewer + StudyEditor + Quick Ask |
| **Assessment** | ✅ 200 deep questions, LLM grading, adaptive engine, null-text validation |
| **Language** | ✅ Greek transliteration, morphology parser, Strong's, interlinear tool |
| **Markdown** | ✅ Unified `:verse[]` / `:entity[]` / `:gematria[]` / `:strong[]` / `:conn[]` syntax |
| **Card system** | ✅ CardQueue + CardRenderer (9 types) + card-factory + interleaving |
| **Truth-seeking** | ✅ Disagreements panel (20 seeds), hermeneutic badges, tradition labels |
| **JST** | ✅ 8,895 JST↔KJV diff connections + 31,262 JST verses in text_resources |
| **Chiastic detection** | ⏳ Neural embedding approach planned |
| **Cross-canon consensus** | ⏳ Truth score API planned |
| **JS discourses** | ⏳ Import from Restoration Archives planned |
