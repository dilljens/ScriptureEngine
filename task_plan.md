# Memorization Module for ScriptureEngine — Task Plan

## Goal
Integrate a complete verse memorization system (FSRS SRS + memory palaces + AI-generated imagery + audio) into ScriptureEngine as a new frontend tab and Go microservice backend.

## Overview

```
ScriptureEngine React SPA
  └── New "Memorize" tab
       ├── Dashboard        — streak, counts, quick review
       ├── ReviewSession    — FSRS card queue with progressive hints
       ├── PalaceBuilder    — upload photo, place loci, assign verses
       ├── PalaceWalk       — slideshow through loci with composites
       ├── ImageStudio      — generate/browse AI concept images
       ├── AudioStudio      — record/playback recitations
       └── MemorizeAnalytics — heat maps, trends

Go Microservice (:8090)          ComfyUI (Docker, :8188)
  ├── FSRS SRS engine              ├── txt2img concept generation
  ├── Palace CRUD                  └── img2img palace compositing
  ├── Review queue + rating
  └── Reads ScriptureEngine DB (read-only)
```

## Tracks

### Track A: Go SRS Microservice
FSRS-based spaced repetition engine, memory palace CRUD, ComfyUI AI proxy, analytics API.

### Track B: Frontend Integration
New "Memorize" tab in the existing React SPA — all UI components.

### Track C: AI Image Generation (ComfyUI Docker)
Local Stable Diffusion pipeline — requires 6GB+ VRAM GPU.

---

## Phase P1 — Go Skeleton + DB Schema + FSRS Core

**⏱ Timebox:** 120 minutes  
**✅ Checkpoint:** `curl localhost:8090/health` returns `{"status":"ok"}` and FSRS unit tests pass  
**⚙ Fallback:** Implement SM-2 instead of FSRS if FSRS math is too complex within the timebox.

| Step | Description |
|------|-------------|
| P1.1 | Initialize Go module at `backend/go-srs/`, set up project structure |
| P1.2 | SQLite schema: all tables with auto-migration |
| P1.3 | FSRS core: `internal/fsrs/fsrs.go` with complete FSRS-5 algorithm |
| P1.4 | HTTP server on `:8090`, CORS, graceful shutdown |
| P1.5 | `POST /api/memorize/verses/batch` — mirror verses from ScriptureEngine DB |

## Phase P2 — Verse Sync + Review Queue + Rating API

**⏱ Timebox:** 90 minutes  
**✅ Checkpoint:** Can create cards, review with ratings, verify correct next intervals  
**⚙ Fallback:** Add DB indexes if queue queries are slow.

| Step | Description |
|------|-------------|
| P2.1 | Card creation on verse import (5 card types per verse) |
| P2.2 | `GET /api/memorize/queue` — due cards query |
| P2.3 | `POST /api/memorize/review/:card_id` — rating + FSRS update |
| P2.4 | `GET /api/memorize/verses/:ref/cards` — card list per verse |

## Phase P3 — Frontend: Memorize Tab + Review UI

**⏱ Timebox:** 180 minutes  
**✅ Checkpoint:** "Memorize" tab appears in ScriptureEngine, can review cards  
**⚙ Fallback:** Mount as full-page overlay if tab integration is too complex.

| Step | Description |
|------|-------------|
| P3.1 | Add `memorize` viewLevel to `tabContext.jsx` |
| P3.2 | Create `MemorizeView.jsx` dashboard component |
| P3.3 | Create `ReviewSession.jsx` card queue with hint levels |
| P3.4 | Add Memorize button in App.jsx sidebar/toolbar |
| P3.5 | Create `memorizeApi.js` API client for Go service |
| P3.6 | Wire Vite proxy for `/api/memorize` → `:8090` |

## Phase P4 — ComfyUI Docker + AI Proxy

**⏱ Timebox:** 120 minutes  
**✅ Checkpoint:** `POST /api/memorize/generate/concept` returns a generated image  
**⚙ Fallback:** Mock AI endpoints with placeholder images if Docker/GPU setup fails.

| Step | Description |
|------|-------------|
| P4.1 | Docker Compose with ComfyUI service (GPU passthrough) |
| P4.2 | Workflow JSONs: `concept-gen.json`, `composite.json` |
| P4.3 | `internal/ai/comfyui.go` — REST client for ComfyUI |
| P4.4 | `POST /generate/concept` endpoint |
| P4.5 | `POST /generate/composite` endpoint |

## Phase P5 — Palace Builder

**⏱ Timebox:** 120 minutes  
**✅ Checkpoint:** Upload photo, place loci, assign verses, see them listed  
**⚙ Fallback:** Use x/y sliders instead of clickable canvas if needed.

| Step | Description |
|------|-------------|
| P5.1 | Backend: palace CRUD, loci CRUD, verse assignment |
| P5.2 | Frontend: `PalaceBuilder.jsx` with clickable photo canvas |
| P5.3 | Frontend: verse selector modal |
| P5.4 | Frontend: `PalaceList.jsx` gallery |

## Phase P6 — AI Compositing Pipeline

**⏱ Timebox:** 90 minutes  
**✅ Checkpoint:** Palace walk shows concept images composited into palace photos  
**⚙ Fallback:** Synchronous generation instead of async queue.

| Step | Description |
|------|-------------|
| P6.1 | Auto-trigger composite generation on verse assignment |
| P6.2 | Frontend: `PalaceWalk.jsx` slideshow |
| P6.3 | Frontend: `ImageStudio.jsx` browse/regenerate |
| P6.4 | Batch generation button |

## Phase P7 — Progressive Hint Levels

**⏱ Timebox:** 60 minutes  
**✅ Checkpoint:** Review cycles through 6 hint levels correctly  
**⚙ Fallback:** Fixed levels (no adaptive progression).

| Step | Description |
|------|-------------|
| P7.1 | 6 hint levels in `ReviewSession.jsx` |
| P7.2 | Card-type to hint-level mapping |
| P7.3 | Adaptive level changes based on rating |
| P7.4 | Store hint level in DB, persist across sessions |

## Phase P8 — Audio Recording/Playback

**⏱ Timebox:** 45 minutes  
**✅ Checkpoint:** Record recitation, play back during review  
**⚙ Fallback:** Use Web Speech API TTS if MediaRecorder fails.

| Step | Description |
|------|-------------|
| P8.1 | Backend: audio upload/serve endpoints |
| P8.2 | Frontend: `AudioStudio.jsx` with MediaRecorder |
| P8.3 | Wire audio prompts into review cards |

## Phase P9 — Analytics + Polish

**⏱ Timebox:** 60 minutes  
**✅ Checkpoint:** Dashboard shows streak, heat maps; palace walk works  
**⚙ Fallback:** Plain-text stats instead of charts.

| Step | Description |
|------|-------------|
| P9.1 | Backend: analytics endpoints (summary, heatmap) |
| P9.2 | Frontend: `MemorizeAnalytics.jsx` with charts |
| P9.3 | Polish PalaceWalk with auto-advance |
| P9.4 | Final cleanup, error handling, loading states |

---

## API Specification (Go service, all under `/api/memorize/`)

```
GET    /health
POST   /verses/batch          — Mirror verses
GET    /queue                 — Due cards (?limit=&card_type=)
GET    /verses/:ref/cards     — All cards for a verse
POST   /review/:card_id       — Rate card {rating: again|hard|good|easy}

GET    /palaces               — List palaces
POST   /palaces               — Create
GET    /palaces/:id           — Details + loci
POST   /palaces/:id/loci      — Add locus
POST   /loci/:id/assign       — Assign verse
POST   /generate/concept      — txt2img
POST   /generate/composite    — Composite into palace
POST   /audio                 — Upload recording
GET    /audio/:id             — Serve audio
GET    /analytics/summary
GET    /analytics/heatmap
```

## FSRS Algorithm (Go)

Standard FSRS-5 parameters. Core function signature:

```go
type FSRSState struct {
    Stability, Difficulty, ElapsedDays, ScheduledDays float64
    Reps, Lapses int
    State CardState
}
func NextState(current FSRSState, rating Rating, params FSRSParams) FSRSState
```

## Database Tables

- `verses` — mirrored from ScriptureEngine (id, book, chapter, verse, text, reference)
- `palaces` — id, name, photo_path
- `loci` — id, palace_id, label, x_pct, y_pct, verse_id
- `cards` — id, verse_id, card_type, FSRS fields, hint_level, due
- `review_log` — id, card_id, rating, elapsed_seconds, review_date
- `concept_images` — id, verse_id, file_path, prompt, model
- `composite_images` — id, verse_id, palace_id, locus_id, file_path
- `audio_recordings` — id, verse_id, file_path, duration_secs

## Integration Points

| Where | What |
|-------|------|
| `tabContext.jsx` | Add `memorize` viewLevel + reducer cases |
| `App.jsx` | Add `<MemorizeView>` in `renderMainContent()` |
| `App.jsx` | Add Memorize button in header/sidebar |
| `memorizeApi.js` (new) | API client for Go service |
| `vite.config.js` | Proxy `/api/memorize` → `:8090` |
| ScriptureEngine `data/processed/scripture.db` | Go reads verses (read-only) |
| `docker-compose.yml` | Add Go + ComfyUI services |
