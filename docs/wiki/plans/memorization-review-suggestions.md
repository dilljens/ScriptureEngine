# Plan Review: Suggestions & Improvements

Comprehensive review of the memorization module plan covering architecture, build order, missing features, UI/UX, and technical risks.

---

## 🏗️ Architecture

### A1. Too Many Processes to Run

**Issue:** The final system requires 4 running processes:
1. Python FastAPI (`:8002`)
2. Vite dev server or nginx (`:5176` / `:80`)
3. Go microservice (`:8090`)
4. ComfyUI Docker (`:8188`, optional but needed for composites)

For a local-first app, this is a significant startup burden.

**Suggestions:**

| Option | Complexity | Benefit |
|--------|-----------|---------|
| **Docker Compose** for everything (FastAPI + Go + ComfyUI) | Medium | One `docker compose up` starts the whole stack |
| **Go sidecar** — Python auto-starts Go as a subprocess on startup | Low | Seamless single-command dev experience |
| **Go embeds in Python** — run Go binary as subprocess from `server.py` | Low | Current user just runs `python web/server.py` and Go starts automatically |

**Recommended:** Add a `scripts/start.sh` or Docker Compose that launches all services. Document clearly. The Go sidecar approach (Python spawns Go as subprocess) is the lowest friction for development.

### A2. Tight Coupling on DB Schema

**Issue:** Go reads ScriptureEngine's `data/processed/scripture.db` directly. If the Python backend changes its schema (column renames, table changes), the Go service breaks silently.

**Suggestions:**
- Add a **schema version check** in Go on startup — compare expected vs actual table columns
- Or have Go call `GET /api/v1/verses/{ref}` from FastAPI instead of direct DB reads (looser coupling, adds latency)
- Or define a **shared schema contract** as a SQL file both sides agree on

**Recommended:** Schema version check on startup + mirror to Go's own SQLite. Already partially planned (P1.5 mirrors verses).

### A3. Port Proliferation

**Issue:** Four services on different ports — easy to forget which is which.

**Suggestion:** Add a `docker-compose.yml` in the project root that ties them together with a unified port (e.g., nginx on `:8080` routing to all services). Already partially planned.

---

## 📦 Build Order

### B1. Long Dependency Chain

**Issue:** The current build order is mostly sequential:

```
P0 (FE) → P0b (FE) → P1 (BE) → P2 (BE) → P3 (FE) → P4 (BE) → ...
```

P3 (Memorize tab UI) is blocked on P0+P0b (FE structure) AND P2 (BE API). That's 4 phases before anything visible ships.

**Suggestion:** Define a **vertical-slice MVP** after P2/P3:

```
        ┌── P0 + P0b (FE structure) ──┐
        │                               ├── P3 (Memorize tab) ── 🎯 MVP v0.1
        │                               │    (basic review, no palaces)
P0+  P0b (FE) ── parallel ── P1 (BE) ──┤
                                        └── P2 (Review API)
```

P0/P0b and P1 can run **in parallel** since they're independent. This cuts the chain from 4 phases to 2.

**🎯 Define MVP v0.1:**
- FSRS review with text cards (no palaces, no AI, no audio)
- Memorize tab with dashboard + review queue
- PWA shell (manifest + service worker)
- **Shippable after P2 + P3**

Everything else (palaces, AI, audio, analytics) is post-MVP.

### B2. No "Quick Win" for New Users

**Issue:** A new user must set up a palace, assign verses, generate images, etc. before memorizing anything. That's a high barrier.

**Suggestion:** Add a **P3.0 quick start path** that bypasses all setup:

```
New user taps "Memorize" →
  → "Pick a verse to memorize" (search/browse)
  → "Get a concept image" (Openverse auto-searches)
  → "Start reviewing" (FSRS card created immediately, default palace-less mode)
  → "Create a memory palace? Later."
```

This gives a 3-tap path from "open app" to "first review." Palace building becomes an optional enhancement, not a prerequisite.

---

## 🧠 Missing Memorization Features

### M1. "Memorize This Verse" from Chapter View

**Issue:** The user reads scripture in ChapterView but can't add verses to their review queue without switching to the Memorize tab.

**Suggestion:** Add a **memorize button** to `VerseBlock.jsx`:

```
┌──────────────────────────────────────┐
│  3  And he spake many things...      │
│                                     │
│  [Copy] [Share] [🧠 Memorize]       │
└──────────────────────────────────────┘
```

Tapping "Memorize" creates a card immediately and shows a confirmation toast: "Added to review queue. [Start Review →]"

**Implementation:** < 30 min — just calls `POST /api/memorize/queue/add` with the verse reference.

### M2. No "Understand First" Step

**Issue:** Elaborative encoding (deep understanding) dramatically improves retention, but the plan doesn't integrate ScriptureEngine's connections/commentary into the memorization flow.

**Suggestion:** Add a **P3.5 understanding step** before first review:

```
First time memorizing a verse:
  1. Show verse text
  2. Show related connections from ScriptureEngine's graph
     (cross-references, gematria, chiasms, lexical insights)
  3. "Tap when you understand the meaning"
  4. First review begins
```

This leverages ScriptureEngine's existing 218K+ connections and 40+ study tools. It's the unique advantage this platform has over standalone memorization apps.

### M3. Review Streak Calendar

**Issue:** Streaks are powerful motivators but not in the plan.

**Suggestion:** Add a **GitHub-style contribution heatmap** to the Memorize dashboard:

```
┌──────────────────────────────────────┐
│  Review Streak: 12 days 🔥           │
│                                      │
│  Mon ██▒▒▒▒▒▒▒▒  Wed ████████▒▒  █  │
│  Tue ██████▒▒▒▒  Thu ██▒▒▒▒▒▒▒▒     │
│                ...                   │
└──────────────────────────────────────┘
```

**Implementation:** 1 new endpoint (`GET /analytics/streak`), 1 new component. ~30 min.

### M4. Palace Walk Should Be Active Recall, Not Passive

**Issue:** The palace walk (P6.2) is described as a "slideshow through loci showing composites + verse text." That's passive viewing — the weakest form of learning.

**Suggestion:** Make the palace walk an **active review session**:

```
Walk through palace (step through loci in order)

At each locus:
  Step 1: Show the palace photo, highlight the locus area
  Step 2: **Wait for user to recall** the verse (blank or first-letter hint)
  Step 3: User taps "Show" → reveals the verse
  Step 4: User rates: Again / Good / Easy
  Step 5: This review is logged via the FSRS API
  Step 6: Move to next locus
```

This turns the palace walk from a passive tour into a **spatially-grounded active recall session** — combining Method of Loci with Active Recall, two of the most powerful techniques.

---

## 🎨 UI/UX

### U1. Due Count Badge on Bottom Tab Bar

**Issue:** The user must open the Memorize tab to see if anything is due. No external cue.

**Suggestion:** Show a badge on the Memorize tab icon when cards are due:

```
  🧠 Memorize      →      🧠 3 Memorize
  (no badge)              (red badge, white text)
```

**Implementation:** The Memorize tab's `useEffect` polls `GET /queue?limit=1` and shows the count. ~15 min.

### U2. Direct-to-Review Flow

**Issue:** Tapping "Memorize" in the bottom bar opens the dashboard. If cards are due, the user must tap again to start reviewing.

**Suggestion:** If cards are due when the user opens the Memorize tab, **skip the dashboard and go directly into review mode**. Dashboard is the fallback when no cards are due.

```js
if (dueCount > 0) {
  navigateTo('/memorize/review')  // skip dashboard
} else {
  navigateTo('/memorize/dashboard')
}
```

### U3. Keyboard Shortcuts for Review

**Issue:** The existing hotkey system (`getHotkey`, `matchesHotkey`) covers navigation but not review actions.

**Suggestion:** Add review-specific shortcuts:

| Key | Action |
|-----|--------|
| `1` | Again |
| `2` | Hard |
| `3` | Good |
| `4` | Easy |
| `Space` | Show Answer |
| `R` | Restart current card |

This makes the review session feel fast and responsive, especially on desktop.

### U4. Tap Verse → Preview → Add to Memorize

**Issue:** Currently the user must go to the Palace Builder and use a "verse selector modal" to pick verses. That's heavy.

**Suggestion:** Allow adding verses from anywhere:

1. **Long-press** any verse in ChapterView → "Memorize this verse" context menu
2. **Search results** → "Add all to memorization" button
3. **Chapter-level** → "Memorize this chapter" (batch-imports all verses)

### U5. Onboarding / First-Run Tutorial

**Issue:** New users won't know what a "memory palace" is or how FSRS works.

**Suggestion:** A 3-step overlay on first visit to the Memorize tab:

```
Step 1: "Review verses daily to build long-term memory."
Step 2: "Create memory palaces — attach verses to places you know."
Step 3: "Record yourself. Hear your own voice during review."
```

Keep it short (3 cards, dismissable). Link to the full techniques comparison doc.

---

## ⚠️ Technical Risks

### T1. ComfyUI Compositing Reliability

**Risk:** AI inpainting requires the right SD model, workflow JSON, GPU, and VRAM. Any break in the chain = no composites.

**Mitigation:** Already planned as fallback ("skip compositing — show side by side"). Ensure the fallback is well-tested. The palace walk should look good even without composites.

### T2. Openverse API Availability

**Risk:** Openverse is a free API from WordPress with no SLA. Rate limiting or downtime could block image search.

**Mitigation:**
- Cache images locally after first fetch (already planned — stored in `concept_images` table)
- If Openverse returns 429 (rate limit), back off and try again later
- If Openverse is down, show a generic placeholder or fall back to upload
- Never block the user from reviewing — images are optional

### T3. FSRS Parameters Need Tuning

**Risk:** Out-of-the-box FSRS parameters may not be optimal for verbatim text memorization. The algorithm was designed for general knowledge (facts, vocabulary), not word-perfect scripture.

**Mitigation:**
- Start with default parameters (they're well-tuned by Anki's user base)
- Add a P2.5 step: collect enough review data to optimize parameters
- FSRS has a built-in optimizer — implement `POST /api/memorize/optimize-params` that runs the optimizer on accumulated review logs
- Document which parameters differ for verbatim memory (likely: higher initial stability, lower difficulty scaling)

### T4. Verse Sync Drift

**Risk:** If ScriptureEngine's DB is re-generated or updated, the Go service's mirrored verses could become stale.

**Mitigation:**
- `POST /verses/batch` should be **idempotent** and able to re-sync without duplicating
- Add a `last_synced` timestamp to the verses table
- Add a `GET /health` check that compares verse counts with ScriptureEngine's DB

### T5. Cross-Device Sync Not Addressed

**Risk:** The plan doesn't mention syncing between devices. User memorizes on phone, opens desktop — their progress is gone.

**Mitigation:** This is a v2 concern, not v1. Document it as a known limitation:
- v1: single-device, SQLite file is portable
- v2: add sync via Syncthing or a lightweight sync server
- The data model supports it (cards/review_log have UUIDs and timestamps)

---

## 📋 Summary: Top 5 Recommended Changes

| # | Change | Impact | Effort | Phase |
|---|--------|--------|--------|-------|
| 1 | **Direct-to-review flow** when cards are due (skip dashboard) | Reduces taps from 4→1 to start reviewing | ~15 min | P3 |
| 2 | **"Memorize this verse"** button in ChapterView/VerseBlock | Lets users add verses from anywhere, not just palace builder | ~30 min | P3 |
| 3 | **Due count badge** on Memorize tab icon | External cue — user doesn't need to open the tab to check | ~15 min | P3 |
| 4 | **Palace walk as active recall** not passive slideshow | Turns Method of Loci from passive → active learning | ~30 min | P6 |
| 5 | **Quick-start path** (pick verse → get image → review, no palace needed) | Lowers barrier from ~10 steps to 3 taps | ~60 min | P3 |

---

## 📈 Build Order (Revised)

```
Week 1:        P0 ──┐
                P0b ─┤  (parallel)
                P1 ──┘
                        
Week 2:              ├── P2 ──┐
                      P3 ─────┤── 🎯 MVP v0.1 (basic FSRS review)
                              │
Week 3:              P4 ──────┤  (images)
                      P5 ─────┤  (palaces)
                              │
Week 4:              P6 ──────┤  (composites + walk)
                      P7 ─────┤  (hint levels)
                      P8 ─────┤  (audio)
                      P9 ─────┤  (analytics)
                     P10 ─────┤  (PWA/push — can start any time)
```

MVP v0.1 after phases P2+P3 is the first shippable milestone: basic FSRS review with text cards, no palace dependencies.
