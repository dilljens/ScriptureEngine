# Progress — Memorization Module for ScriptureEngine

## Status Overview

| Phase | Track | Status | Started | Completed | Notes |
|-------|-------|--------|---------|-----------|-------|
| P0 | Mobile UX architecture | 🔍 Planned | — | — | Top bar + drawer + settings tab |
| P0b | Two-layer tab system | 🔍 Planned | — | — | Subjects bar on all sizes, [None] option |
| P1 | Go skeleton + FSRS | ⏳ Pending | — | — | Ready to start after P0+P0b |
| P2 | Review queue API | ⏳ Pending | — | — | Blocked on P1 |
| P3 | Memorize tab UI | ⏳ Pending | — | — | Placeholder exists, needs real UI |
| P4 | Image pipeline | 🔍 Planned | — | — | 3-tier: AI → Openverse → Upload |
| P5 | Palace builder | ⏳ Pending | — | — | Blocked on P3 |
| P6 | Compositing | ⏳ Pending | — | — | P6 depends on P5 |
| P7 | Hint levels | ⏳ Pending | — | — | Blocked on P3 |
| P8 | Audio | ⏳ Pending | — | — | Blocked on P3 |
| P9 | Analytics + polish | ⏳ Pending | — | — | Blocked on all |

## Session History

### Session 1 (2026-07-06)
- Research memorization techniques + AI image gen for 6GB VRAM
- Explored ScriptureEngine architecture
- Planned integration architecture (Go microservice + React tab)
- Created initial plan files
- Added MemorizeIcon, openMemorizeTab, MemorizeView placeholder, memorizeApi.js
- Built mobile bottom tab bar: Read · Chat · Memorize · Library · Subjects
- Desktop: added Memorize icon to toolbar

### Session 2 (2026-07-06)
- Refined mobile UX: top bar + bottom nav + slide-out drawer
- Settings → full tab, secondary actions → drawer
- Chat → bottom bar only

### Session 3 (2026-07-06)
- Added two-layer tab system (P0b)
- Subjects bar on mobile too, [None] option
- TileDashboard selects workspace on click
- Performed memorization techniques audit

### Session 4 (2026-07-06)
- Added hybrid image pipeline to P4
- Three tiers: ComfyUI (AI) → Openverse (free search) → Manual upload
- No API key needed for Openverse
- Auto-select best result, no user picking
- Updated all plan files

## Notes

### Architecture
- Go microservice at `backend/go-srs/`, serving on `:8090`
- React frontend integration via new "memorize" tab
- ComfyUI Docker optional (GPU path) — app works without it
- Openverse API fallback — free, no key, CC-licensed religious art
- Direct read of ScriptureEngine's SQLite DB for verse data
- Two-layer tab system: Subjects (top) + Tabs (bottom) on all sizes
- Mobile: three-zone layout (top bar, two-layer tabs, bottom tab bar, drawer)
- Desktop: full toolbar, two-layer tabs, no bottom bar

### Memorization Techniques Audit
All 7 highest-utility techniques from Dunlosky et al. (2013) are covered.
See findings.md "Memorization Techniques Coverage" section.

### Dependencies
- Go 1.22+ installed
- Docker + Docker Compose (for ComfyUI — optional)
- NVIDIA GPU with 6GB+ VRAM (for local AI — optional)
- ScriptureEngine running with `data/processed/scripture.db` populated

### Open Questions
- [ ] Should the Go service run inside Docker or as a native process?
- [ ] Which port for Go service? (8090 proposed)
