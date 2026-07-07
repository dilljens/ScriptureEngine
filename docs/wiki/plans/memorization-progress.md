# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P0 | Mobile UX architecture | 🔍 Planned | — | — | Top bar + drawer + settings tab |
| P0b | Two-layer tab system | 🔍 Planned | — | — | Subjects bar on all sizes, [None] option |
| P0c | Split-pane reading | ✅ Done | 2026-07-06 | 2026-07-06 | Companion in tab state, split layout in App.jsx |
| P1 | Go skeleton + FSRS | ✅ Done | 2026-07-07 | 2026-07-07 | FSRS-5 verified against Rust test vectors |
| P2 | Review queue API | ✅ Done | 2026-07-07 | 2026-07-07 | Queue + rating + stats endpoints |
| P3 | Memorize tab UI | ✅ Done | 2026-07-07 | 2026-07-07 | **🎯 MVP v0.1 shipped** |
| P4 | Image pipeline | ✅ Done | 2026-07-07 | 2026-07-07 | Openverse search + concept images in review |
| P5 | Palace builder | ✅ Done | 2026-07-07 | 2026-07-07 | CRUD + clickable canvas + verse picker |
| P6 | Compositing | 🔍 Planned | — | — | Active-recall palace walk |
| P7 | Hint levels | ⚠️ Partial | 2026-07-07 | — | First-letter hints in review; full progressive levels pending |
| P8 | Audio | ⏳ Pending | — | — | |
| P9 | Analytics + polish | ⏳ Pending | — | — | |
| P10 | PWA + push notifications | 🔍 Planned | — | — | Independent |
| F1 | FIRe Implicit Repetition | ✅ Done | 2026-07-07 | 2026-07-07 | Cloned from MIT reference; boosts connected verses |
| E4 | Interleaved Review | 🔍 Planned | — | — | Mixed-passage ordering |
| H1 | Hebrew Teaching | 🔍 Planned | — | — | Knowledge graph + curriculum design done |

## Session History

### Sessions 8-10 (2026-07-07) — Memorization MVP + FIRe
- **P1**: Built Go FSRS-5 backend at `backend/go-srs/`
  - Implemented FSRS-5 from Rust reference, verified against 17 published test vectors
  - Full SQLite schema (10 tables) with auto-migration
  - HTTP server on :8090 with CORS + graceful shutdown
  - Endpoints: health, verse sync, card CRUD, queue, review, stats

- **P2**: Review queue + rating API
  - FSRS state transitions on every review
  - XP + streak tracking
  - Due queue ordering

- **P3**: Frontend Memorize tab
  - MemorizeView dashboard with stats grid
  - ReviewSession with first-letter hints, 4 rating buttons, keyboard shortcuts (1-4, Space)
  - Direct-to-review: skips dashboard when cards due
  - Celebration view when queue empty

- **P4**: Image pipeline
  - Openverse API client (free CC-licensed biblical art)
  - Search query builder (extracts keywords via stop-word removal)
  - Concept images shown in review when answer revealed

- **P5**: Palace Builder
  - CRUD backend for palaces + loci
  - Clickable photo canvas for placing loci
  - Verse search modal (uses main scripture API)

- **F1**: FIRe (Fractional Implicit Repetition)
  - Cloned from `moaaz-ae/plcourse` (MIT) — verified reference implementation
  - DFS traversal of verse connection graph with chain weight multiplication
  - Connection type weights (direct_quotation=0.8, same_lemma=0.4, etc.)
  - Best-path-wins: strongest path used when multiple routes reach same verse
  - Verified: Gen 1:1 review boosts John 1:1 stability by +40%

## Architecture

```
Frontend (React) ← Vite proxy → Go Backend (:8090) ← SQLite (data/memorize.db)
                                       │
                                       ├── FSRS-5 algorithm (Rust-verified)
                                       ├── FIRe engine (MIT reference)
                                       ├── Openverse client
                                       └── Palace CRUD
```

### Dependencies
- Go 1.26+ installed
- ScriptureEngine running with `data/processed/scripture.db` populated
- Openverse API (free, no key needed)

### Running
```bash
# Terminal 1: Go backend
backend/go-srs/go-srs-server --port 8090 --db data/memorize.db

# Terminal 2: Main web server
./run.sh web
```
