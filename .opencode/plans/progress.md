# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P0 | Mobile UX architecture | 🔍 Planning | — | — | Top bar + drawer + settings tab |
| P0b | Two-layer tab system | 🔍 Planning | — | — | Subjects bar on all sizes, [None] option, TileDashboard integration |
| P1 | Go skeleton + FSRS | ⏳ Pending | — | — | Ready to start after P0+P0b |
| P2 | Review queue API | ⏳ Pending | — | — | Blocked on P1 |
| P3 | Memorize tab UI | ⏳ Pending | — | — | Placeholder exists, needs real UI |
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
- Created initial plan files (task_plan.md, findings.md, progress.md)
- Added MemorizeIcon, openMemorizeTab, MemorizeView placeholder, memorizeApi.js
- Built mobile bottom tab bar: Read · Chat · Memorize · Library · Subjects
- Desktop: added Memorize icon to toolbar

### Session 2 (2026-07-06)
- Refined mobile UX: top bar + bottom nav + slide-out drawer
- Settings moves from modal overlay to full tab
- Secondary actions → slide-out drawer
- Chat → bottom bar only (not header)
- Updated plan files

### Session 3 (2026-07-06)
- Added two-layer tab system to plan (P0b)
- Subjects bar visible on mobile too (replaces dropdown)
- [None] option to deselect workspace
- TileDashboard cards set active workspace on click
- Performed memorization techniques audit on the plan

## Notes

### Architecture
- Go microservice at `backend/go-srs/`, serving on `:8090`
- React frontend integration via new "memorize" tab
- ComfyUI as Docker container for AI image generation
- Direct read of ScriptureEngine's SQLite DB for verse data
- Two-layer tab system: Subjects (top) + Tabs (bottom) on all sizes
- Mobile: three-zone layout (top bar, two-layer tabs, bottom tab bar, drawer)
- Desktop: full toolbar, two-layer tabs, no bottom bar

### Memorization Techniques Audit
See findings.md "Memorization Techniques Coverage" section for full audit.

### Dependencies
- Go 1.22+ installed
- Docker + Docker Compose (for ComfyUI)
- NVIDIA GPU with 6GB+ VRAM (for local AI, optional)
- ScriptureEngine running with `data/processed/scripture.db` populated

### Open Questions
- [ ] What's the default style prompt for concept images? (e.g., "biblical illustration style, oil painting")
- [ ] Should the Go service run inside Docker or as a native process?
- [ ] Which port for Go service? (8090 proposed)
