# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P0 | Mobile UX architecture | 🔍 Planning | — | — | Top bar + bottom nav + drawer design finalized |
| P1 | Go skeleton + FSRS | ⏳ Pending | — | — | Ready to start after P0 |
| P2 | Review queue API | ⏳ Pending | — | — | Blocked on P1 |
| P3 | Memorize tab UI | ⏳ Pending | — | — | Placeholder created, needs real UI |
| P4 | ComfyUI + AI proxy | ⏳ Pending | — | — | Blocked on P1 |
| P5 | Palace builder | ⏳ Pending | — | — | Blocked on P3 |
| P6 | Compositing | ⏳ Pending | — | — | Blocked on P4+P5 |
| P7 | Hint levels | ⏳ Pending | — | — | Blocked on P3 |
| P8 | Audio | ⏳ Pending | — | — | Blocked on P3 |
| P9 | Analytics + polish | ⏳ Pending | — | — | Blocked on all |

## Session History

### Session 1 (2026-07-06)
- Research memorization techniques + AI image gen for 6GB VRAM
- Explored ScriptureEngine architecture
- Planned integration architecture (Go microservice + React tab)
- Created plan files (task_plan.md, findings.md, progress.md)
- Added MemorizeIcon, openMemorizeTab, MemorizeView placeholder, memorizeApi.js
- Built mobile bottom tab bar: Read · Chat · Memorize · Library · Subjects
- Desktop: added Memorize icon to toolbar

### Session 2 (2026-07-06) — Current
- Refined mobile UX: top bar + bottom nav + slide-out drawer
- Settings moves from modal overlay to full tab
- Secondary actions (History, Font, Dark mode, Graph, Layers, etc.) → slide-out drawer
- Chat → bottom bar only (not header)
- Top bar: always visible, independent from bottom bar
- Desktop toolbar stays unchanged

## Notes

### Architecture
- Go microservice at `backend/go-srs/`, serving on `:8090`
- React frontend integration via new "memorize" tab
- ComfyUI as Docker container for AI image generation
- Direct read of ScriptureEngine's SQLite DB for verse data
- Mobile: three-zone layout (top bar, bottom tab bar, slide-out drawer)

### Dependencies
- Go 1.22+ installed
- Docker + Docker Compose (for ComfyUI)
- NVIDIA GPU with 6GB+ VRAM (for local AI, optional)
- ScriptureEngine running with `data/processed/scripture.db` populated

### Open Questions
- [ ] What's the default style prompt for concept images? (e.g., "biblical illustration style, oil painting")
- [ ] Should the Go service run inside Docker or as a native process?
- [ ] Which port for Go service? (8090 proposed)
