# Scripture Engine — Master Execution Plan

> **See `task_plan.md` for the detailed implementation plan with phases, tracks, and checkpoints.**
> **See `findings.md` for pre-resolved decisions, architecture notes, and risk assessment.**
> **See `progress.md` for session-level execution tracking.**

This file is the **top-level system status** — what's done, what's remaining, and where the detailed plans live.

---

## Full System Status

| Area | Status | Detail |
|------|--------|--------|
| **Connection Graph** | ✅ | 1.77M connections, 11 layers, 100+ types, 53 generators |
| **Infrastructure** | ✅ | Deploy gate, structured logging, health endpoint, CI |
| **Search** | ✅ | FTS5, vector (sqlite-vec), graph-enhanced (3-way RRF), reranker, cache |
| **Graph DB** | ✅ | 71+ tables, entities, gematria, lexicon, passage_connections |
| **API** | ✅ | 146 endpoints, 12 route modules, 52 MCP tools |
| **Frontend** | ✅ | 56 components, React 19 + Vite + Tailwind, responsive |
| **Wiki** | ✅ | 20+ articles, search/browse/concordance |
| **Hebrew teaching** | ✅ | 102-node curriculum, diagnostic, quiz, FSRS-5, gamification, verb drills, interleaved review |
| **Memorization** | ✅ | FSRS-5 (Go SRS), FIRe credit flow, palaces, hints, audio, interleaving |
| **Study guides** | ✅ | Full backend (create/publish/fork/export) + StudyViewer + StudyEditor + Quick Ask |
| **Assessment** | ✅ | 200 deep questions, LLM grading, adaptive engine, null-text validation |
| **Language** | ✅ | Greek transliteration, morphology parser, Strong's, interlinear tool |
| **Markdown** | ✅ | Unified `:verse[]` / `:entity[]` / `:gematria[]` / `:strong[]` / `:conn[]` syntax |
| **Card system** | ✅ | CardQueue + CardRenderer (9 types) + card-factory + interleaving |
| **Truth-seeking** | ✅ | Null-text validation, disagreements panel (20 seeds), hermeneutic badges, tradition labels, ecumenical consensus |
| **Codebase audit** | ✅ | Convention violations 129→0, Ruff 5969→2023, tests green |
| **JST** | ✅ | 8,895 JST↔KJV diff connections + 31,262 JST verses in text_resources |

---

## Remaining Work (~40h)

| Phase | Effort | Tracks | Status |
|-------|--------|--------|--------|
| **Track 0: Trigram FTS5** | ~2h | Index script, wire search, Hebrew/Greek integration | ❌ Standalone |
| **Phase 5: Polish & Quick Wins** | ~5h | ntfy.sh notifications, sefirotic mapping, FIRe penalty flow | ❌ Next |
| **Phase 6: Hebrew & Language** | ~15h | 7 Hebrew features (cloze, freq vocab, passage study mode, 2-way trans, daily verse, audio mode, Hebrew-only), entity expansion, LLM lexicon | ⏳ After Phase 5 |
| **Phase 7: Assessment Engine** | ~20h | Domain definition, prerequisite graph, adaptive engine (BLIM), auto-generate items, IRT, FSRS spacing, progress tracking, recommendations | ⏳ After Phase 6 |

### Quick Reference to Detailed Plans

| What | Where |
|------|-------|
| Full implementation plan (phases, tracks, checkpoints) | `task_plan.md` |
| Pre-resolved decisions, architecture notes, risk | `findings.md` |
| Execution tracking per session | `progress.md` |
| Trigram FTS5 detail | `trigram-fts-plan.md` |
| Hebrew enhancement detail | `docs/wiki/plans/hebrew-enhancement-plan.md` |
| Assessment engine detail | `docs/wiki/plans/knowledge-assessment-plan.md` |
| Rabbinic tools (sefirot, etc.) | `docs/wiki/plans/rabbinic-kabbalistic-tools.md` |
| LLM lexicon definitions | `docs/wiki/plans/llm-lexicon-plan.md` |
| Macro-analysis (deferred) | `docs/plans/macro-analysis-plan.md` |
| Math Academy Way reference | `docs/wiki/plans/math-academy-way-reference.md` |

---

## Remaining Items (from original Phases 0-3)

### Phase 0: Infrastructure
| # | Task | Status | Now in |
|---|------|--------|--------|
| 0.9 | ntfy.sh push notifications on health failure | ⏳ | Phase 5 → Track A |

### Phase 2C: Assessment Engine
| # | Task | Status | Now in |
|---|------|--------|--------|
| 2.9 | Knowledge domain definition | ❌ | Phase 7 → Track F |
| 2.10 | Prerequisite graph | ❌ | Phase 7 → Track F |
| 2.11 | Adaptive assessment engine (BLIM) | ❌ | Phase 7 → Track F |
| 2.12 | Auto-generate assessment items | ❌ | Phase 7 → Track F |
| 2.13 | IRT calibration | ❌ | Phase 7 → Track G |
| 2.14 | FSRS-based spaced repetition | ❌ | Phase 7 → Track G |
| 2.15 | User progress tracking + dashboard | ❌ | Phase 7 → Track H |
| 2.16 | Study recommendations from gap analysis | ❌ | Phase 7 → Track H |

### Phase 3: Memorization
| # | Task | Status | Now in |
|---|------|--------|--------|
| 3.11 | Sefirotic mapping | ❌ | Phase 5 → Track B |
| 3.13 | Multi-mode FIRe (penalty flow) | ⏳ | Phase 5 → Track B |

---

## Deferred Work (not in current ~40h plan)

| Item | Effort | Rationale |
|------|--------|-----------|
| API test coverage (152→ tested) | ~8h | Existing 829 smoke tests + 38 pytest → adequate baseline |
| Macro-analysis (genre, trajectories, etc.) | ~2,700 lines | Low priority vs. Hebrew + assessment |
| Neural chiastic detection | Research | Separate research track |
| Cross-canon pattern mining | Research | Depends on neural chiastic |
| JS Discourses import | Research | Data ingestion, not feature work |
| Hebrew passage study mode (PHASE 2) | Ongoing | Phase C3 covers the MVP; deeper LingQ-style later |
| Playwright E2E test expansion | Ongoing | Continuous improvement |

---

## Key DevOps

| Service | Port | Status |
|---------|------|--------|
| FastAPI (dev) | 8002 | ✅ |
| FastAPI (prod) | 8000 | ✅ |
| Go SRS | 8090 | ✅ |
| Vite frontend (dev) | 5176 | ✅ |
| Vite frontend (prod) | 5173 | ✅ |
| Production | scriptureengine.org | ✅ |
