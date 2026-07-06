# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P1 | Go skeleton + FSRS | ⏳ Pending | — | — | Ready to start |
| P2 | Review queue API | ⏳ Pending | — | — | Blocked on P1 |
| P3 | Frontend tab | ✅ Done | 2026-07-06 | 2026-07-06 | Tab + mobile button + placeholder view |
| P4 | ComfyUI + AI proxy | ⏳ Pending | — | — | Blocked on P1 |
| P5 | Palace builder | ⏳ Pending | — | — | Blocked on P3 skeleton |
| P6 | Compositing | ⏳ Pending | — | — | Blocked on P4+P5 |
| P7 | Hint levels | ⏳ Pending | — | — | Blocked on P3 skeleton |
| P8 | Audio | ⏳ Pending | — | — | Blocked on P3 skeleton |
| P9 | Analytics + polish | ⏳ Pending | — | — | Blocked on all |

## Current Session

**Started:** 2026-07-06  
**Current focus:** Phase 3 — Frontend tab integration done; next: Phase 1 Go skeleton  

### Completed This Session
- [x] Research memorization techniques
- [x] Research AI image gen for 6GB VRAM
- [x] Explore ScriptureEngine architecture
- [x] Plan integration architecture
- [x] Create plan files (task_plan.md, findings.md, progress.md)
- [x] Add MemorizeIcon to icons.jsx
- [x] Add openMemorizeTab action to tabContext.jsx
- [x] Add memorize view handling in App.jsx renderMainContent
- [x] Add memorize button to mobile footer (bottom bar)
- [x] Add memorize button to desktop toolbar
- [x] Create MemorizeView.jsx with dashboard/status placeholders
- [x] Create memorizeApi.js client for Go service
- [x] Wire Vite proxy for /api/memorize → :8090

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
