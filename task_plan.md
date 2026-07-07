# Memorization Module for ScriptureEngine — Task Plan

## Goal
Integrate a complete verse memorization system (FSRS SRS + memory palaces + hybrid image pipeline + audio) into ScriptureEngine as a new frontend tab and Go microservice backend.

## Mobile UX Architecture

```
┌─ TOP BAR (always visible, no hide-on-scroll) ────────────┐
│  ☰  │  Breadcrumb (work / book / ch.3)  │  🔍 Search   │
├─ SUBJECTS BAR ──────────────────────────────────────────┤
│  [My Study] [Prophets] [Psalms] [+ Add] [None ◇]       │
├─ TAB STRIP (within active subject) ────────────────────┤
│  [Isaiah 6] [Gen 1] [Romans 8] [+]                      │
├─ CONTENT ───────────────────────────────────────────────┤
│                                                          │
├─ BOTTOM TAB BAR (mobile only) ─────────────────────────┤
│  📖 Read  💬 Chat  🧠 Memorize  📚 Library  ▦ Subjects  │
└─────────────────────────────────────────────────────────┘
```

### Two-Layer Tab System (Desktop + Mobile)

| Layer | What | Behavior |
|-------|------|----------|
| **Subjects bar** | All workspaces as pills + [None] option | Switch active workspace; "None" shows Subjects/Tiles dashboard |
| **Tab strip** | Tabs within the active workspace | New tabs open into the active workspace |
| **Tiles/Subjects view** | Grid of all workspaces + create/rename/delete | Click a subject card → selects it as active workspace |

When **no workspace is selected** (the [None] state):
- Tab strip is hidden or shows "Select a subject to begin"
- Content area shows the Tiles/Subjects dashboard
- From the dashboard, clicking a subject selects it and shows its tabs

---

## Overview

```
ScriptureEngine React SPA
  └── Two-layer tabs: Subjects (top) + Tabs (bottom)
       │
       ├── Subjects: My Study | Prophets | Psalms | +Add | None
       │    │
       │    └── Tabs within active subject:
       │         Chapter tabs · Chat · Memorize · Settings
       │
       ├── Memorize tab
       │    ├── Dashboard        — streak, counts, quick review
       │    ├── ReviewSession    — FSRS card queue with progressive hints
       │    ├── PalaceBuilder    — upload photo, place loci, assign verses
       │    ├── PalaceWalk       — slideshow through loci with composites
       │    ├── ImageStudio      — generate/browse concept images (AI + Openverse + upload)
       │    ├── AudioStudio      — record/playback recitations
       │    └── MemorizeAnalytics — heat maps, trends
       │
       └── Settings tab (replaces modal overlay)

Go Microservice (:8090)
  ├── FSRS SRS engine
  ├── Palace CRUD
  ├── Review queue + rating
  ├── Hybrid image pipeline: AI (ComfyUI) → Openverse → Manual upload
  └── Reads ScriptureEngine DB (read-only)

ComfyUI (Docker, :8188) — optional GPU path
  ├── txt2img concept generation
  └── img2img palace compositing
```

## Build Order

```
         ┌── P0 + P0b (FE structure) ──┐
         │  (parallel with P1)          │
P0+P0b ──┤                              ├── P2 + P3 ──► 🎯 MVP v0.1
P1 ──────┘                              │    (basic FSRS review ships!)
P0c ─── (indep., done anytime)          │
                                        ├── P4 + P5 (images + palaces)
                                        ├── P6 + P7 (compositing + hints)
                                        ├── P8 + P9 (audio + analytics)
                                        └── P10 (PWA/push — any time)
```

**🎯 MVP v0.1** (after P2 + P3): basic FSRS review with text cards. No palaces, no AI, no audio needed.

## Tracks

### Track 0: Mobile UX Architecture
Restructure the mobile layout into three zones: top bar (search + breadcrumb), bottom tab bar (5 nav destinations), slide-out drawer (secondary actions). Settings moves from modal to a full tab.

### Track 0b: Two-Layer Tab System
Make the subjects bar visible on both desktop AND mobile (replacing mobile dropdown). Add [None] option to deselect workspace. Subjects/Tiles view sets active workspace on click.

### Track 0c: Split-Pane Reading
Side-by-side chapter reading using the existing `companion` tab field. Split button in ChapterView, two-column layout in App.jsx.

### Track A: Go SRS Microservice
FSRS-based spaced repetition engine, memory palace CRUD, hybrid image pipeline (AI + Openverse + upload), analytics API.

### Track B: Frontend — Memorization Features
Memorize tab UI with review, palaces, images, audio, analytics.

### Track C: Image Pipeline
Three-tier image sourcing: ComfyUI (GPU, best quality) → Openverse (free API, no key) → Manual upload (always works).

---

## Phase P0 — Mobile UX Architecture

**⏱ Timebox:** 150 minutes  
**✅ Checkpoint:** Mobile view shows: top bar (☰ + breadcrumb + search), bottom tab bar (5 buttons), drawer slides out from left with all secondary actions  

| Step | Description |
|------|-------------|
| P0.1 | Create `SlideDrawer.jsx` — left slide-out panel with backdrop, animation, edge-swipe gesture |
| P0.2 | Populate drawer: Settings tab opener, History, Graph, Layers, Structure, Font+Dark controls, Command, Cheatsheet |
| P0.3 | Create `SettingsView.jsx` — full-page settings tab (moved from modal overlay) |
| P0.4 | Add `settings` viewLevel to tabContext.jsx reducer + App.jsx renderMainContent |
| P0.5 | Restructure mobile top bar: ☰ hamburger + breadcrumb + search only — remove ALL icon buttons |
| P0.6 | Bottom tab bar: Read · Chat · Memorize · Library · Subjects |
| P0.7 | Desktop header stays unchanged (all icon buttons remain) |

## Phase P0b — Two-Layer Tab System (Desktop + Mobile)

**⏱ Timebox:** 90 minutes  
**✅ Checkpoint:** Subjects bar visible on both desktop AND mobile as scrollable pill row. [None] option deselects workspace. TileDashboard cards set active workspace on click.

| Step | Description |
|------|-------------|
| P0b.1 | Allow `activeWorkspace = null` in tabContext reducer: NEW_TAB returns if null (tabs require active subject). Update SELECT_WORKSPACE to accept `null`. |
| P0b.2 | Add "None" pill to SubjectTabBar that sets `activeWorkspace = null` |
| P0b.3 | Replace mobile workspace `<select>` dropdown with the pill-based SubjectTabBar (remove `sm:hidden`, show on all widths) |
| P0b.4 | When `activeWorkspace` is null in App.jsx: hide tab strip, show Tiles/Subjects view as content |
| P0b.5 | TileDashboard: clicking a subject's name/card calls `selectWorkspace(ws.id)` |
| P0b.6 | After selecting a workspace from Tiles view, route to its first tab or show empty state |
| P0b.7 | Desktop: make two rows explicit (subjects bar + tab strip), always visible together |

## Phase P0c — Split-Pane Reading

**⏱ Timebox:** 60 minutes  
**✅ Checkpoint:** ChapterView shows a "Split" button; tapping it opens a chapter picker; selecting renders two chapters side by side; "Close split" restores single view.

| Step | Description |
|------|-------------|
| P0c.1 | App.jsx: update `renderMainContent()` to detect `currentTab.companion` — when set, render two ChapterViews in a flex row (left=primary, right=companion) with a border divider |
| P0c.2 | App.jsx: add `handleSplitView` callback — prompts user for companion book+chapter, calls `updateTab(currentTab.id, { companion: { book, chapter } })` |
| P0c.3 | App.jsx: add "Close split" button on companion pane header |
| P0c.4 | ChapterView: accept `onSplit` prop, add "⊞ Split" button in the chapter header toolbar |
| P0c.5 | Handle split across all view levels — only works at `viewLevel === 'chapter'` |
| P0c.6 | Touch/mobile: companion pane scrolls independently; responsive collapse at very narrow widths |

## Phase P1 — Go Skeleton + DB Schema + FSRS Core

**⏱ Timebox:** 120 minutes  
**✅ Checkpoint:** `curl localhost:8090/health` returns `{"status":"ok"}` and FSRS unit tests pass  
**⚙ Fallback:** Implement SM-2 instead of FSRS if FSRS math is too complex within the timebox.

| Step | Description |
|------|-------------|
| P1.1 | Initialize Go module at `backend/go-srs/`, set up project structure |
| P1.2 | SQLite schema: all tables with auto-migration (add `source` column to concept_images) |
| P1.3 | FSRS core: `internal/fsrs/fsrs.go` with complete FSRS-5 algorithm, verified against published test vectors from `fsrs-rs` repo |
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
**🎯 This phase completes MVP v0.1** — basic FSRS review ships here  
**✅ Checkpoint:** "Memorize" tab appears in ScriptureEngine, can review cards, due count badge shows on tab icon  
**⚙ Fallback:** Mount as full-page overlay if tab integration is too complex.

| Step | Description |
|------|-------------|
| P3.1 | Create `MemorizeView.jsx` dashboard component (placeholder exists, build real UI) |
| P3.2 | **Quick-start path**: "Pick a verse → Get concept image → Start reviewing" in 3 taps, no palace setup required |
| P3.3 | **Elaborative encoding step**: before first review of a verse, show its connections/cross-references from ScriptureEngine's graph. "Understand the meaning before memorizing." |
| P3.4 | **Due count badge**: poll `GET /queue?limit=1` on Memorize tab icon in bottom tab bar, show red badge if count > 0 |
| P3.5 | **"Memorize this verse" button**: add to `VerseBlock.jsx` — long-press or icon in verse header creates a card immediately |
| P3.6 | Create `ReviewSession.jsx` card queue with hint levels |
| P3.7 | Wire `memorizeApi.js` to Go service for live data |
| P3.8 | FSRS review flow: queue → show card → rate → next card |
| P3.9 | **Keyboard shortcuts** in review mode: 1=Again, 2=Hard, 3=Good, 4=Easy, Space=Show Answer |

## Phase P4 — Image Acquisition Pipeline

**⏱ Timebox:** 150 minutes  
**✅ Checkpoint:** `POST /api/memorize/generate/concept` returns an image from one of three sources (AI → Openverse → upload)  
**⚙ Fallback:** Skip ComfyUI setup if no GPU — system works with Openverse + upload only.

| Step | Description |
|------|-------------|
| P4.1 | Docker Compose with ComfyUI service (GPU path, optional) |
| P4.2 | Workflow JSONs: `concept-gen.json`, `composite.json` |
| P4.3 | ComfyUI REST client in Go (`internal/ai/comfyui.go`) |
| P4.4 | **NEW: Openverse API client** (`internal/ai/openverse.go`) — calls `https://api.openverse.engineering/v1/images/` with search query, auto-selects top result. No API key needed. |
| P4.5 | **NEW: Search query builder** (`internal/ai/query.go`) — extracts key nouns/verbs from verse text using stop-word removal, adds "bible illustration" qualifier |
| P4.6 | `POST /generate/concept` — source auto-select (ComfyUI if GPU available → Openverse → 404) |
| P4.7 | `POST /generate/composite` — AI-only, needs ComfyUI for inpainting into palace photo |
| P4.8 | `POST /images/upload` — multipart file upload for manual images |
| P4.9 | Add `source` column to `concept_images` table (`ai`, `openverse`, `upload`) |

### Image Source Auto-Select Logic

```go
func (s *Server) getConceptImage(verseID string) (*ConceptImage, error) {
    // 1. Check if image already exists for this verse
    if existing := s.db.GetConceptImage(verseID); existing != nil {
        return existing, nil
    }
    // 2. Try ComfyUI if available
    if s.comfyUI.IsAvailable() {
        if img, err := s.comfyUI.Generate(verseID); err == nil {
            return s.db.SaveConceptImage(verseID, img, "ai"), nil
        }
    }
    // 3. Fallback to Openverse search
    verse := s.db.GetVerse(verseID)
    query := buildSearchQuery(verse.Text, verse.Reference)
    if img, err := s.openverse.Search(query); err == nil {
        return s.db.SaveConceptImage(verseID, img, "openverse"), nil
    }
    // 4. No image available
    return nil, ErrNoImage
}
```

### Openverse API Integration

```go
// internal/ai/openverse.go
func SearchConceptImage(verseText, reference string) (*OpenverseImage, error) {
    query := buildSearchQuery(verseText, reference)
    // GET https://api.openverse.engineering/v1/images/
    //   ?q=good+shepherd+bible+illustration
    //   &page_size=5&license=cc-by,cc0
    resp, err := http.Get("https://api.openverse.engineering/v1/images/?q=" + 
        url.QueryEscape(query) + "&page_size=5")
    // Auto-select first valid result
    // Download and store in data/images/concept/{verse_id}.jpg
    // Save metadata to concept_images table
}
```

### Search Query Builder

```go
func buildSearchQuery(text, ref string) string {
    // 1. Strip punctuation and digits
    // 2. Remove stop words (the, a, an, and, or, but, in, on, at, etc.)
    // 3. Extract top 5 meaningful words
    // 4. Add book context if helpful
    // 5. Append "bible" qualifier
    return "good shepherd bible"
}
```

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
**⚙ Fallback:** Skip compositing — show concept image and palace photo side by side.

| Step | Description |
|------|-------------|
| P6.1 | Auto-trigger composite generation on verse assignment (requires ComfyUI) |
| P6.2 | Frontend: `PalaceWalk.jsx` — **active recall walk**: at each locus, pause and prompt user to recall the verse (first-letter or blank) before revealing. Ratings feed FSRS. Not a passive slideshow. |
| P6.3 | Frontend: `ImageStudio.jsx` browse/regenerate with source indicators |
| P6.4 | Batch generation button (AI or search per verse) |

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

## Phase P10 — PWA + Push Notifications

**⏱ Timebox:** 120 minutes  
**✅ Checkpoint:** Add to home screen prompts on mobile; push notification fires when review is due  
**⚙ Fallback:** Skip push service for local-only setups — use `setInterval` in service worker for in-browser reminders.

| Step | Description |
|------|-------------|
| P10.1 | Create `public/manifest.json` — app name, icons, theme colors, display: standalone, start URL |
| P10.2 | Create app icons at 192×192 and 512×512 (SVG-based, or simple generated PNGs) |
| P10.3 | Link manifest in `index.html` head |
| P10.4 | Create service worker `public/sw.js` — install, activate, fetch (cache-first for static assets) |
| P10.5 | Register service worker from `index.html` or main entry |
| P10.6 | **Push subscription flow**: `POST /api/memorize/push/subscribe` — save endpoint + keys in DB. `POST /api/push/unsubscribe` — remove. |
| P10.7 | Service worker `push` event handler — parse payload, show notification with due card count |
| P10.8 | **Backend push scheduler**: Go service checks for due cards every N minutes. Sends push via Web Push Protocol (no Firebase needed). Uses `golang.org/x/time/rate` or a simple ticker. |
| P10.9 | Add new DB table `push_subscriptions` — endpoint, p256dh key, auth key, created_at |
| P10.10 | Notification click handler in service worker — opens/focuses the memorize tab |
| P10.11 | Settings toggle: "Review reminders" on/off in settings tab |
| P10.12 | Test: add to home screen on Android + iOS, verify notifications fire on schedule |

### Push Notification Architecture

```
┌─────────────────┐         ┌──────────────────────┐
│  Go Backend      │         │  Browser (SW)         │
│                  │         │                        │
│  Ticker (15min)  │───push──│  sw.onpush → notify() │
│  checks due cards│  event  │  click → focus tab    │
│  sends via Web   │         │                        │
│  Push Protocol   │         │  POST /push/subscribe  │
│                  │◄────────│  (VAPID keys)          │
└─────────────────┘         └────────────────────────┘
```

### VAPID Keys
Required for Web Push Protocol. Generated once via CLI:
```bash
go run tools/generate-vapid.go
```
Stored as env vars (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`). Public key served to the frontend so it can subscribe.

---

## API Specification (Go service, all under `/api/memorize/`)

```
GET    /health
POST   /verses/batch              — Mirror verses
GET    /queue                     — Due cards (?limit=&card_type=)
GET    /verses/:ref/cards         — All cards for a verse
POST   /review/:card_id           — Rate card {rating: again|hard|good|easy}

GET    /palaces                   — List palaces
POST   /palaces                   — Create
GET    /palaces/:id               — Details + loci
POST   /palaces/:id/loci          — Add locus
POST   /loci/:id/assign           — Assign verse
POST   /generate/concept          — {verse_id} → auto-selects source (AI→Openverse→404)
POST   /generate/composite        — AI-only: {verse_id, palace_id, locus_id}
POST   /images/upload             — Multipart: {verse_id, file} → manual upload
GET    /images/:id                — Serve image
POST   /audio                     — Upload recording
GET    /audio/:id                 — Serve audio
GET    /analytics/summary
GET    /analytics/heatmap
POST   /push/subscribe              — Save push subscription {endpoint, keys}
POST   /push/unsubscribe            — Remove push subscription
GET    /push/vapid-public-key       — VAPID public key for browser subscription
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
- `concept_images` — id, verse_id, file_path, prompt, model, source (ai|openverse|upload)
- `composite_images` — id, verse_id, palace_id, locus_id, file_path
- `audio_recordings` — id, verse_id, file_path, duration_secs
- `push_subscriptions` — id, endpoint, p256dh_key, auth_key, created_at

## Integration Points

| Where | What |
|-------|------|
| `tabContext.jsx` | Add `memorize` + `settings` viewLevels; allow `activeWorkspace = null` |
| `App.jsx` | Add `<MemorizeView>` + `<SettingsView>` in `renderMainContent()` |
| `App.jsx` | Restructure mobile: top bar + two-layer tabs + bottom tab bar + drawer |
| `App.jsx` | When `activeWorkspace` is null: hide tab strip, show Tiles view |
| `SubjectTabBar.jsx` | Remove `sm:hidden`, add [None] pill, add click-to-select in Tiles view |
| `SubjectTabBar.jsx` | Replace mobile dropdown with pill-based subject bar |
| `TileDashboard.jsx` | Click subject card → calls `selectWorkspace(ws.id)` |
| `SlideDrawer.jsx` (new) | Slide-out drawer with all secondary actions |
| `SettingsView.jsx` (new) | Full-page settings tab |
| `memorizeApi.js` (new) | API client for Go service |
| `vite.config.js` | Proxy `/api/memorize` → `:8090` |
| ScriptureEngine `data/processed/scripture.db` | Go reads verses (read-only) |
| `docker-compose.yml` | Add Go + ComfyUI (optional) services |
| `VerseBlock.jsx` | Add "Memorize this verse" button (P3.5) |
| `ChapterView.jsx` | Add "⊞ Split" button, accept `onSplit` prop (P0c) |
| `public/manifest.json` (new) | PWA manifest — app name, icons, standalone, theme |
| `public/sw.js` (new) | Service worker — push handler, cache strategy |
| `public/icon-192.png`, `icon-512.png` (new) | App icons for home screen |
| `index.html` | Link manifest, register service worker |
| `golang.org/x/time/rate` | Go dependency — push rate limiting |
| `github.com/sherclockholmes/webpush-go` | Go dependency — Web Push Protocol |
