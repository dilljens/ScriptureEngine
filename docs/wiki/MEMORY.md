# Scripture Engine — Project Memory

_Last updated: 2026-07-08_

## Current State

| Metric | Value |
|--------|-------|
| Verses | 70,956 across 8 works |
| Connections | 1,356,667 typed |
| Knowledge items | 685,086 |
| Lexicon entries | 25,813 |
| Tools/Endpoints | 52+ HTTP + MCP |

## Backend Architecture

- **server.py**: 2,402 lines (was 4,965 — refactored into route modules)
- **Route modules** (`web/routes/`):
  - `hebrew.py` (876 lines) — Hebrew learning + vocabulary + grammar reference + FSRS
  - `audio.py` (124 lines) — Read-along + audio playback
  - `chat.py` (979 lines) — LLM chat proxy + tool definitions
  - `studies.py` (369 lines) — Study guides CRUD
  - `conversations.py` (151 lines) — Conversation sessions
  - `assessment.py` (22 lines) — Knowledge assessment endpoints
- **Go backend** (`backend/go-srs/`): FSRS-5 algorithm + FIRe engine + Hebrew concept graph
- **Database**: SQLite (`data/processed/scripture.db` — 1.4GB, connections + verses + gematria)
- **Hebrew DB**: `data/memorize.db` — 642 node curriculum with progress tracking

## Hebrew Learning System

Full Biblical Hebrew curriculum aligned with The Math Academy Way:

| Component | Status |
|-----------|--------|
| 642 concept nodes (11 categories) | ✅ Deployed |
| Practice items | 3,467 across 7 types |
| Prerequisite edges | 229 |
| Confusability pairs | 28 |
| FSRS-5 spaced repetition | ✅ 21-parameter algorithm with FIRe |
| Student-topic learning speeds | ✅ ability/difficulty ratio |
| Diagnostic pre-assessment | ✅ 22 questions across all categories |
| Automaticity timed drills | ✅ Per-question countdown, content-scaled |
| Micro-scaffolding | ✅ 3 Knowledge Points per lesson |
| Targeted remediation | ✅ Wrong answers show prerequisite buttons |
| Systematic interleaving | ✅ Round-robin category diversity |
| Non-interference | ✅ Confusable topics separated |
| Gamification | ✅ Streaks + XP (localStorage) |
| On-screen Hebrew keyboard | ✅ Floating + lesson-integrated |
| Audio (Shmueloff) | ✅ Word-level playback for Genesis 1 |

## Knowledge Assessment

- 685,086 knowledge items across 4 PaRDeS layers
- 18,717 prerequisite relationships
- BLIM-based IRT scoring with adaptive item selection
- Dedicated AssessmentView UI (no LLM dependency)
- Direct API endpoints: `/api/v1/assessment/start`, `/answer`, `/progress`

## LLM Integration

- DeepSeek-v4-flash API with 600s timeout for thinking mode
- 3 chat modes: `chat`, `hebrew`, `knowledge`
- 52 registered MCP tools
- Tool definitions for assessment, Hebrew lessons, scripture lookup, graph traversal

## UI Features

- Desktop: Library → Work → Book → Chapter navigation with infinity zoom
- Mobile: 7-tab bottom nav (Read, Chat, Hebrew, Quiz, Review, Go, Menu)
- Command palette with autocomplete (`/` prefix for commands)
- Double-tap immersion mode (hides all UI bars)
- Collapsible tab strip
- Hebrew, Knowledge, Memory accessed from toolbar + mobile nav
