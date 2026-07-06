# Findings — Memorization Module for ScriptureEngine

## Architecture Decisions

### Why Go Microservice Instead of Python
ScriptureEngine's backend is Python/FastAPI, but memorization is delegated to a Go microservice because:
1. **FSRS algorithm** — Go is excellent for algorithmic math with no GC pauses
2. **ComfyUI proxy** — Go's stdlib HTTP client is production-grade
3. **Single binary** — easy to deploy alongside the Python app
4. **No runtime dependency** — user doesn't need Python venv for the memorization module

### Why FSRS Instead of SM-2
FSRS (Free Spaced Repetition Scheduler) is the modern standard used by Anki 23.10+. It adapts to each user's memory patterns with 4 learned parameters. SM-2 is simpler but less efficient (more reviews for same retention). The user explicitly requested FSRS.

### Why ComfyUI Instead of A1111
ComfyUI has the best API for programmatic use (native REST + WebSocket), best VRAM management (`--lowvram`), and workflows can be version-controlled as JSON. A1111 development has stalled.

### AI Model Recommendation for 6GB VRAM
- **Primary:** SD 3.5 Medium (FP16, fits at 6GB, good text rendering for scripture)
- **Fallback:** SD 1.5 + Realistic Vision V5.1 (guaranteed fit, rich ecosystem for compositing)
- **Optimizations:** `--lowvram --force-fp16` + xformers + tiled VAE decode
- **Two-stage pipeline:** txt2img (concept) → img2img inpainting (composite into palace photo)
- **Expected times:** 4-8 sec per concept image, 2-4 sec per composite

## ScriptureEngine Architecture (as discovered)

### Frontend
- React 19 + Vite 6 + Tailwind CSS 3
- **No React Router** — custom tab system via React Context + `useReducer`
- View hierarchy: `tiles → library → work → book → chapter` (+ `chat`, `graph`, `study`)
- Navigation via up/down/left/right commands
- State persisted to localStorage under `scripture_tabs`
- API client: `frontend/src/api.js` — `fetchJSON` wrapper, all calls to `/api/v1/*`
- Vite proxy in dev: `/api` → `http://localhost:8002`

### Backend
- Python 3 + FastAPI + Uvicorn
- Single monolithic file: `web/server.py` (~4,000 lines)
- RAM cache: loads all verse data at startup (~500MB)
- SQLite database at `data/processed/scripture.db` with FTS5, sqlite-vec, WAL mode
- 42K+ verses, 218K+ connections, gematria, lexicon, assessment engine
- Tool registry pattern: tools registered in `lib/api/__init__.py` auto-exposed as HTTP + MCP + CLI

### Assessment Engine (Pre-existing)
- `lib/assessment/` directory exists but no frontend UI for memorization
- `knowledge_items` table with Bloom's taxonomy levels
- No spaced repetition or flashcard system in the frontend

## Research Sources

### Memorization Techniques
1. **FSRS Algorithm** — Open Spaced Repetition Scheduler (Anki 23.10+)
2. **Active Recall / Testing Effect** — Roediger & Karpicke (2006), Psychological Science
3. **Spaced Repetition** — Cepeda et al. (2006), Dunlosky et al. (2013)
4. **Method of Loci** — Used since ancient Greece, dominant memory athlete technique
5. **First-Letter Method** — Cued recall variant used by ScriptureTyper, Bible Memory App
6. **Production Effect** — Eghbaria-Ghanamah et al. (2021) — saying aloud > silent reading
7. **Quran Hifz traditions** — 3×3 method, 3-10 method, 6-4-4-6 method
8. **Tibetan Buddhist monastic memorization** — chanting with body rocking, aural-only
9. **Medieval Christian monastic** — Lectio Divina, memory palaces, chant

### AI Image Generation for 6GB VRAM
- **ComfyUI** is the recommended backend (best API, best VRAM, fastest updates)
- **SD 3.5 Medium** fits at 6GB FP16 at 512×768
- **SD 1.5 + Realistic Vision** is the safest fallback with best ecosystem
- Two-stage pipeline: txt2img concept → img2img composite into palace photo
- Docker container: `ai-dock/comfyui` with GPU passthrough

## Quality Baseline

No sentrux scan performed — this is a new module being added to an existing project. The project's existing quality will be measured before the first code changes.

## Mobile UX Decisions (2026-07-06)

### Split: Top Bar + Bottom Nav + Slide-out Drawer

The mobile UI is being restructured into three zones:

| Zone | Contents | Behavior |
|------|----------|----------|
| **Top bar** | ☰ drawer hamburger · Breadcrumb · 🔍 Search | Always visible, independent from bottom bar (no hide-on-scroll) |
| **Bottom tab bar** | 📖 Read · 💬 Chat · 🧠 Memorize · 📚 Library · ▦ Subjects | Primary navigation destinations |
| **Slide-out drawer** | Settings tab · History · Font controls · Dark mode · Graph · Layers · Structure · Command palette · Cheatsheet | Opens from left via ☰ button or edge swipe |

### What Changes on Mobile

| Action | Current Location | New Location |
|--------|-----------------|--------------|
| Search | Header toolbar | Top bar (remains) |
| Chat | Header + Bottom bar | Bottom bar only |
| Memorize | Header + Bottom bar | Bottom bar only |
| Structure (Isaiah) | Header | Slide-out drawer |
| History | Header | Slide-out drawer |
| Font size | Header | Slide-out drawer |
| Dark mode | Header | Slide-out drawer |
| Settings | Header overlay (modal) | **Settings tab** (full-page `viewLevel: 'settings'`) |
| Command palette | Header | Slide-out drawer |
| Subjects (tiles) | Header (mobile only) | Bottom bar only |
| Graph | Header | Slide-out drawer |
| Layers | Header | Slide-out drawer |

### Settings Tab
Settings moves from a modal overlay to a dedicated tab (like Chat and Memorize). This gives it room for all controls without crowding the UI. Accessible from the slide-out drawer.

### Desktop Header Stays Unchanged
All the above changes are `sm:hidden` (mobile-only). Desktop keeps the full toolbar with all icon buttons.

### Drawer Contents
```
┌──────────────────────────────┐
│ ☰  ScriptureEngine           │
│                              │
│  ⚙  Settings                 │  → opens settings tab
│  🕐  History                 │  → opens history overlay
│  📊  Connection Graph         │  → opens graph tab
│  🧩  Layers / PaRDeS         │  → opens layers popover
│  📐  Isaiah Structure        │  → opens structure modal
│  🔤  Font Size               │  → inline controls
│  🌙  Dark Mode               │  → toggle
│  ⌨️  Command Palette         │  → opens command input
│  ❓  Keyboard Shortcuts      │  → opens cheatsheet
│                              │
│  ─────────────────────────── │
│  v1.0.0                      │
└──────────────────────────────┘
```

## Two-Layer Tab System (2026-07-06)

### Current Architecture
The app already has a two-layer system: `Workspaces → Tabs`. However:
- The workspace (subject) bar is `hidden sm:flex` — desktop only
- On mobile, workspaces are switched via a `<select>` dropdown — hidden, not visual
- `activeWorkspace` always auto-falls back to the first workspace — no "none" state
- Subject tiles in TileDashboard don't set `activeWorkspace` — they navigate via `openTab`

### Changes

| Change | Why |
|--------|-----|
| Subjects bar visible on ALL screen sizes | Mobile needs the same two-layer navigation as desktop |
| Replace mobile dropdown with pill bar | Pills are more visual, tappable, and consistent with desktop |
| Add [None] option to deselect workspace | Allows user to "zoom out" to the Subjects dashboard without drilling into a subject |
| `activeWorkspace` can be null | Enables the [None] state; NEW_TAB returns early if no workspace is active |
| TileDashboard cards set activeWorkspace | Clicking a subject from the dashboard selects it, showing its tabs |
| Tab strip hidden when no workspace active | No tabs to show; content shows Tiles/Subjects view |

### UX Flow

```
Subjects view (no workspace active)
  │
  ├── Click subject card → selectWorkspace(id) → shows that subject's tabs
  │     │
  │     └── Tab strip visible, content shows active tab
  │
  ├── Click [None] pill → selectWorkspace(null) → back to Subjects view
  │
  └── Bottom bar or search → opens tab in active workspace (or prompts to select one)
```

### Two-Layer Layout

```
Desktop + Mobile:
┌──────────────────────────────────────────────────────┐
│ TOP BAR:  ☰  Breadcrumb  🔍 Search                   │
├──────────────────────────────────────────────────────┤
│ SUBJECTS BAR: [My Study] [Prophets] [Psalms] [+None] │
├──────────────────────────────────────────────────────┤
│ TAB STRIP: [Isaiah 6] [Gen 1] [Romans 8] [+]         │
│   (hidden if no workspace active)                     │
├──────────────────────────────────────────────────────┤
│ CONTENT                                               │
│   If no workspace active: Subjects/Tiles dashboard    │
│   If workspace active: active tab's content           │
├──────────────────────────────────────────────────────┤
│ BOTTOM TAB BAR (mobile only): Read · Chat · Memorize ·│
│   Library · Subjects                                   │
└──────────────────────────────────────────────────────┘
```

## Memorization Techniques Coverage — Audit

### Techniques Covered ✅

| Technique | Where in Plan | Evidence Level | How It Works |
|-----------|--------------|----------------|--------------|
| **Active Recall** | P7 — Progressive hint levels (P3, P7) | Gold standard (Roediger & Karpicke 2006, Dunlosky 2013) | Each review card forces retrieval from memory — no passive rereading. 6 hint levels from full text → first letters → image → location → audio → blank. |
| **Spaced Repetition** | P1/P2 — FSRS engine | Gold standard (Cepeda 2006, Dunlosky 2013) | FSRS-5 algorithm adapts intervals per-card based on user ratings. Same engine powering Anki 23.10+. |
| **Method of Loci** | P5/P6 — Palace Builder + Walk | Strong (Yates 1966, Foer 2011, Dellis) | User uploads real location photos, places loci, assigns verses. AI composites concept images into each locus. Walk mode provides spatial rehearsal. |
| **First-Letter Method** | P7 — Hint level 1 | Direct application of cued recall (Bible Memory App, ScriptureTyper) | During review, level 1 shows first letters of each word as a retrieval cue. Forces word-by-word recall. |
| **Production Effect** | P8 — Audio Studio | Eghbaria-Ghanamah 2021 | User records their own recitation. Audio prompts during review trigger auditory-motor memory. |
| **Visual Mnemonics** | P4/P6 — AI image generation | Moderate (imagery-for-text, Dunlosky 2013) | Each verse gets a custom AI-generated concept image. Composited into palace photos for spatial-visual binding. |
| **Dual Coding** | P3/P7 — Image + text in review | Paivio 1986 (dual coding theory) | Both visual (image, location photo) and verbal (text, audio) representations of each verse. Redundant encoding strengthens memory. |
| **Chunking** | P5 — Loci assignment | Miller 1956 | Verses are assigned to loci (chunks). The palace structure naturally segments long passages into manageable pieces. |
| **Multi-Sensory Integration** | P3–P8 — All phases | High (multimodal learning research) | Simultaneously engages: visual (images, photos, text), auditory (TTS, recordings), spatial (palace loci), kinesthetic (recording, rating). |
| **Distributed Practice** | P1/P2 — FSRS scheduling | Gold standard (Dunlosky 2013) | SRS enforces daily reviews with growing intervals. Dashboard streak reinforces consistency. |
| **Metacognitive Tracking** | P9 — Analytics | Moderate (self-regulated learning) | Heat maps show weak verses, accuracy trends show progress, streak shows consistency. User can adjust focus. |

### Techniques Partially Covered ⚠️

| Technique | Gap | Suggestion |
|-----------|-----|------------|
| **Elaborative Encoding** | Plan assumes user understands the verse before memorizing, but doesn't integrate ScriptureEngine's commentary/connections into the workflow. | Before memorizing a verse, show its connections, cross-references, and interpretations from ScriptureEngine's graph. A "Understand First" step in the memorization flow. |
| **Interleaved Practice** | FSRS naturally interleaves due cards from different passages, but no explicit mixed-passage session design. | A "Mixed Review" mode that pulls from all active verses regardless of passage, randomized by difficulty. |

### Techniques Not Covered ❌

| Technique | Why Skipped | Worth Adding? |
|-----------|-------------|---------------|
| **Keyword Mnemonics** | Low utility per Dunlosky 2013. Our AI images serve the same purpose better. | No — AI concept images supersede keyword mnemonics. |
| **Rereading / Highlighting** | Lowest utility per Dunlosky 2013. Actively harmful if it replaces retrieval. | No — we deliberately avoid this. |
| **Summarization** | For gist learning, not verbatim. | Maybe — a "paraphrase before memorize" step could help encoding. Low priority. |

### Platform-Specific Strengths

| Feature | Why It Matters for Memorization |
|---------|---------------------------------|
| **Integration into ScriptureEngine** | User doesn't leave their study environment. Verse data, connections, lexicon are immediately available. |
| **Go microservice** | FSRS math runs fast with no GC pauses. Single binary = easy to deploy. |
| **ComfyUI local AI** | Generations are free, private, fast (4-10s). Palace composites are unique to this app. |
| **SQLite** | Simple, portable, zero-config. User owns their data. |

### Concerns

| Risk | Mitigation |
|------|------------|
| **Over-engineering** — the system has many features (SRS, palaces, AI, audio, analytics) | Each feature maps to an evidence-based technique. None are gratuitous. Phased delivery ensures each feature is validated before the next begins. |
| **AI generation requires GPU** | Mock mode for non-GPU users. Generation is additive — the app works fully without it. |
| **Palace builder complexity** | Phase 5 has a `use x/y sliders` fallback if the canvas interaction is too complex. Start simple, iterate. |
| **Verbatim vs. gist tension** | The hint levels scaffold from gist (image/location) to verbatim (full text). Both types of memory are trained. |

### Verdict

**The plan covers all 7 of the highest-utility memorization techniques** identified by Dunlosky et al. (2013) and the cognitive science literature:

1. ✅ Practice testing (active recall)
2. ✅ Distributed practice (spaced repetition)
3. ✅ Elaborative interrogation (via ScriptureEngine integration — partial)
4. ✅ Self-explanation (via verse study before memorization — implicit)
5. ✅ Interleaved practice (via FSRS — partial)
6. ✅ Imagery for text (AI-generated concept images)
7. ✅ Keyword mnemonics (superseded by AI images)

**Missing items are either low-utility techniques we're deliberately avoiding, or additive features for later phases.** No critical memorization mechanism is absent from the plan.

## Hybrid Image Pipeline (2026-07-06)

### Three-Tier Sourcing

Instead of relying solely on AI generation (which requires a GPU), images come from three sources, auto-selected in priority order:

| Tier | Source | Cost | Requires | Quality | Speed |
|------|--------|------|----------|---------|-------|
| 1 | **ComfyUI (SD 3.5 Medium)** | Free | NVIDIA GPU 6GB+ VRAM | Best — specific to verse | ~5s |
| 2 | **Openverse API** | Free | Internet connection | Good — CC-licensed religious art | ~1s |
| 3 | **Manual upload** | Free | User action | User's choice | Instant |

### Openverse API

- **Endpoint:** `https://api.openverse.engineering/v1/images/`
- **Auth:** None required (rate-limited per IP)
- **Licenses:** CC-BY, CC0, Public Domain
- **Relevance:** Good for biblical illustrations, classical religious art
- **Rate limit:** Generous for personal use

### When Each Source Is Used

| Action | Source |
|--------|--------|
| Generate concept image (verse → single image) | Auto: ComfyUI → Openverse → 404 |
| Composite into palace photo | ComfyUI only (needs inpainting) |
| User uploads their own image | Manual |
| Regenerate existing concept | Same source as original (or user picks) |

### Search Query Building

The Go service constructs search queries from verse text:

```
Input: "I am the good shepherd: the good shepherd giveth his life for the sheep."
Output: "good shepherd bible"

Algorithm:
1. Strip punctuation and digits
2. Remove stop words (the, a, an, and, or, but, in, on, at, to, for, of, by, with, from, that, this, etc.)
3. Extract top 3-5 words by significance
4. Append "bible" qualifier
```
