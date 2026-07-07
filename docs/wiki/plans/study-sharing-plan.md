# Phase 1: Study Engine Enhancement — Graph Paths, Publish API, Interactive Viewer

**Goal:** Enhance study guides with full graph path data, publish API endpoints, interactive study viewer tab with clickable verse refs and inline LLM Quick Ask.

## Pre-resolved Decisions

- **Study storage:** Add `content_json` TEXT column to `study_guides` — the canonical source of truth. Steps, graph paths, and metadata are stored as a single JSON blob. The existing `study_guide_steps` table remains for backward compat but the JSON is primary.
- **Export format:** Single JSON file with all step data, graph paths (source, target, layer, type, strength, confidence), verse texts, and metadata. Self-contained — no DB needed to view a study from the JSON.
- **Verse refs:** Clickable refs use the existing `VersePreviewCard` component. Just wire it into study steps.
- **LLM Quick Ask:** Toggle in settings (default: off). Compact bar at bottom of study tab. "Continue in ChatPanel" opens the full chat scoped to the study.
- **Auth:** Not now. Settings + studies persist in localStorage for now.

## Track A: Backend — Study Data Model & API

### Phase A1: Study JSON Format & Export (`lib/api/study.py`)
- [x] Add `content_json` column via migration
- [x] Design canonical JSON schema for study with full graph paths
- [x] `export_json(conn, guide_id)` — serialize study + steps + graph paths as JSON
- [x] `import_json(conn, json_data)` — create/update study from JSON blob
- [x] `publish_study(conn, guide_id)` — freeze snapshot, return unique slug
- [x] `get_published(conn, slug)` — fetch published study
- [x] Update MCP tool registry with new tools

### Phase A2: Publish API Endpoints (`web/server.py`)
- [ ] `POST /api/v1/studies/publish` — publish a study
- [ ] `GET /api/v1/studies/{slug}` — get published study data
- [ ] `GET /api/v1/studies/{slug}.json` — download JSON
- [ ] `GET /api/v1/studies/{slug}.html` — download self-contained HTML
- [ ] `GET /api/v1/studies` — list published studies
- [ ] `GET /api/v1/studies/{id}/fork` — fork a published study

### Phase A3: HTML Export Generation (`lib/export/html_study.py`)
- [ ] Template for self-contained HTML page
- [ ] Include verse texts, CSS, minimal interactivity (expand/collapse)
- [ ] Verse refs link to main reader

## Track B: Frontend — Study Tab

### Phase B1: StudyViewer Component (`frontend/src/components/StudyViewer.jsx`)
- [ ] Interactive tab that renders a study's steps
- [ ] Each step: verse ref (clickable → VersePreviewCard), explanation, graph paths
- [ ] Expand/collapse per step
- [ ] Reorder steps (drag handle)
- [ ] Toggle connection layers on/off
- [ ] Open verse refs in new tabs alongside study

### Phase B2: Inline Quick Ask (`StudyViewer.jsx`)
- [ ] Collapsible bar at bottom of study tab
- [ ] Single-turn LLM query with full study context as system prompt
- [ ] "Continue in ChatPanel →" button opens scoped full conversation
- [ ] Respects settings toggle (default: off)

### Phase B3: Settings Toggle (`settings.jsx` + `SettingsPanel.jsx`)
- [ ] Add `showQuickAsk` setting
- [ ] Render toggle in SettingsPanel under new "LLM" section
- [ ] Persist to localStorage

## Track C: Study Editor

### Phase C1: StudyEditor Component (`frontend/src/components/StudyEditor.jsx`)
- [ ] Form to create/edit a study
- [ ] Add step: verse reference (auto-suggest), title, explanation, graph paths
- [ ] Preview mode: see how it looks
- [ ] Save as draft (localStorage)

### Phase C2: Import/Export
- [ ] Import study from JSON (drag-and-drop)
- [ ] Export study as JSON download
- [ ] Publish → server → shareable URL

## Track D: Routing

### Phase D1: Frontend route for `/study/{slug}`
- [ ] App.jsx routes `/study/{slug}` to StudyViewer in read-only mode
- [ ] Works as a standalone page anyone can open

## Checkpoints

| # | Checkpoint | Verifies |
|---|-----------|----------|
| 1 | Create study with 5 steps + graph paths → export JSON → all data present | JSON schema is lossless |
| 2 | Import JSON back → all 5 steps render correctly | Round-trip works |
| 3 | Click a verse ref → VersePreviewCard popup with highlighted verse | Verse ref integration works |
| 4 | Open study tab next to chapter tab → flip between them | Tab system integration works |
| 5 | Settings toggle → Quick Ask shows/hides | Settings persist correctly |
| 6 | Publish study → get URL → open in incognito → see all steps | Public viewing works |
| 7 | Download JSON from published study → re-import → modify → publish new version | Fork cycle works |
