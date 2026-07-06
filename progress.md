# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P1 | Go skeleton + FSRS | ⏳ Pending | — | — | Ready to start |
| P2 | Review queue API | ⏳ Pending | — | — | Blocked on P1 |
| P3 | Frontend tab | ⏳ Pending | — | — | Blocked on P2 |
| P4 | ComfyUI + AI proxy | ⏳ Pending | — | — | Blocked on P1 |
| P5 | Palace builder | ⏳ Pending | — | — | Blocked on P3 |
| P6 | Compositing | ⏳ Pending | — | — | Blocked on P4+P5 |
| P7 | Hint levels | ⏳ Pending | — | — | Blocked on P3 |
| P8 | Audio | ⏳ Pending | — | — | Blocked on P3 |
| P9 | Analytics + polish | ⏳ Pending | — | — | Blocked on all |

## Current Session

**Started:** 2026-07-06  
**Current focus:** Phase 1 — Go skeleton + FSRS core  

### Completed This Session
- [x] Research memorization techniques
- [x] Research AI image gen for 6GB VRAM
- [x] Explore ScriptureEngine architecture
- [x] Plan integration architecture
- [x] Create plan files

### Next Actions
- [ ] Initialize Go module at `backend/go-srs/`
- [ ] Implement SQLite schema + auto-migration
- [ ] Implement FSRS core algorithm
- [ ] Set up HTTP server with health check

## Notes

### Architecture
- Go microservice at `backend/go-srs/`, serving on `:8090`
- React frontend integration via new "memorize" tab
- ComfyUI as Docker container for AI image generation
- Direct read of ScriptureEngine's SQLite DB for verse data

### Dependencies
- Go 1.22+ installed
- Docker + Docker Compose (for ComfyUI)
- NVIDIA GPU with 6GB+ VRAM (for local AI, optional)
- ScriptureEngine running with `data/processed/scripture.db` populated

### Open Questions
- [ ] What's the default style prompt for concept images? (e.g., "biblical illustration style, oil painting")
- [ ] Should the Go service run inside Docker or as a native process?
- [ ] Which port for Go service? (8090 proposed)
