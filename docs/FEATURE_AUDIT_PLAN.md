# Feature Audit & Smoothing Plan

> Systematic review of every feature area, known issues, and fixes needed.
> Last updated: 2026-07-12

## How to Use This Plan

Each section represents a feature area. For each:
1. **Review** — Open the feature, click through every interaction
2. **Check** — Verify against known issues listed below
3. **Test** — Run the associated smoke test if one exists
4. **Fix** — Address all bugs found, then mark section complete

---

## 1. Chat System

### Features
- Welcome message with suggestion buttons
- LLM conversation with tool calling
- Verse ref detection in input with preview
- Markdown rendering (`:verse[]`, `:entity[]`, `:gematria[]`, `:strong[]`, `:conn[]`)
- System prompt with formatting instructions
- Search scope toggles (works, layers, language)
- Conversation history (save/restore)
- Message editing and resend
- Study "Quick Ask"

### Known Issues
- [ ] **DONE** `%%%CLICK:` markers showing as raw text — Fixed
- [ ] **DONE** `:verse[]` / `<span>` tags not interactive — Fixed (rehype-raw added to 6 components)
- [ ] Suggestion buttons don't trigger tool calls — verify `handleSuggestion()` works
- [ ] System prompt may be too long (costs tokens on every message)
- [ ] ChatPanel `BOOK_NAME_MAP` — verify LLM can reference all 9 works
- [ ] `preprocessVerses()` may not handle all edge cases (D&C, DSS book IDs)

### Review Steps
1. Open chat → verify welcome message shows clickable suggestion buttons
2. Click each suggestion → verify LLM responds with formatted content
3. Type `genesis 1:1` in input → verify preview card appears
4. Type `genesis1:1` in input → verify preview card appears (no-space format)
5. Click "Add as context" → verify verse is sent to LLM
6. Type `genesis 1` → verify whole-chapter preview appears
7. Ask "show me gen.1.1" → verify verse ref renders as clickable blue chip
8. Click the verse chip → verify VersePopup opens with verse text
9. Test `:entity[Abraham]`, `:strong[H430]`, `:gematria[יהוה=26]` in responses
10. Toggle search works off for DSS → verify LLM doesn't search DSS
11. Save conversation → close → reopen → verify session restored
12. Edit a user message → resend → verify chat continues from edit point

---

## 2. Navigation & Views

### Features
- Zoom in/out (tiles → library → work → book → chapter)
- Arrow key navigation between works/books/chapters
- Library view with work cards
- Work view with book grid
- Book view with chapter grid
- Chapter view with verse list
- Keyboard shortcuts (Enter, arrows, Escape)
- Breadcrumb navigation
- D&C special handling (flat sections, no book level)

### Known Issues
- [ ] **DONE** `goToWork` hardcoded `book: 'isa'` — Fixed
- [ ] **DONE** `viewRef` null on work→library — Fixed
- [ ] **DONE** `openLibraryView` loses work context — Fixed
- [ ] `lg:grid-cols-15` in BookView — not a valid Tailwind class (ignored)
- [ ] D&C `goUpLevel` hardcodes `'dc'` string — fragile
- [ ] `goToBook` always sets `chapter: 1`, loses user's position
- [ ] Flag icons on work cards (📜📜📜) — three different works share 📜

### Review Steps
1. Start at chapter view (e.g., Genesis 1)
2. Press ↑ (zoom out) → verify book view shows Genesis with correct chapter grid
3. Press ↑ again → verify work view shows OT books list
4. Press ↑ again → verify Library shows OT as focused/highlighted
5. Press ←/→ in Library → verify works cycle correctly
6. Press Enter in Library → verify it opens the focused work
7. Navigate to D&C Section 76 → press ↑ → verify it skips book level (D&C flat)
8. Navigate to Apocrypha → Tobit → verify chapter buttons work (not showing 50)
9. Navigate to DSS → 1QS → verify it opens correctly
10. Navigate to Pseudepigrapha → 1 Enoch → verify 108 chapters
11. Click breadcrumb → verify it takes you back correctly
12. Use `/dss/1qs/1` in search bar → verify path navigation works

---

## 3. Search System

### Features
- FTS5 full-text search across all works
- Semantic search (concept matching)
- Work filter dropdown
- Results with highlighted text + work badges
- Pagination ("Load more")
- Verse reference preview in results
- `/chat`, `/dark`, `/font` slash commands
- Fuzzy book name matching (e.g., "isah 34" → Isaiah)

### Known Issues
- [ ] **DONE** `WORK_COLORS` missing 4 works — Fixed
- [ ] No work badges for apoc/pseu/expanded in results — verify
- [ ] Semantic search may not work if vectors aren't loaded
- [ ] Search can timeout on slow connections (10s AbortController)
- [ ] No chapter preview when typing standalone ref like `gen 1`

### Review Steps
1. Type "atonement" → verify results from multiple works
2. Type "covenant" → verify work badges show correct colors
3. Type "atonement" with DSS filtered out → verify no DSS results
4. Click "Load more" → verify pagination works
5. Type `genesis 1:1` → verify preview card appears with verse text
6. Type `genesis1:1` → verify preview works (no-space)
7. Type `gen 1:1-2` → verify verse range preview
8. Type `isah 34` → verify fuzzy matches Isaiah 34
9. Type `/chat what is gematria` → verify opens chat with message
10. Type `/dark` → verify toggles dark mode
11. Toggle semantic search (✦) → verify concept matches appear
12. Open work filter dropdown → verify all 9 works listed

---

## 4. Library View

### Features
- Work cards with icons, book counts, subtitles
- Keyboard navigation (arrows + Enter)
- Focused work highlighting
- D&C flat book handling
- Work color coding

### Known Issues
- [ ] **DONE** `WORK_LABEL` missing apoc/pseu/expanded — Fixed
- [ ] **DONE** `workCardColors` missing apoc/pseu/expanded — Fixed
- [ ] **DONE** `viewRef` null on entry (arrow keys dead) — Fixed
- [ ] Three works share 📜 icon (dss, apoc, pseu, expanded) — consider unique icons
- [ ] "No works loaded" still shows briefly during cold load

### Review Steps
1. Navigate to Library → verify 9 work cards in correct order
2. Verify each work shows correct book count + subtitle
3. Click each work → verify it opens to correct book list (or flat section)
4. Use ←/→ arrows → verify focused work changes
5. Press Enter → verify opens the focused work
6. Verify D&C card is clickable (flat sections)
7. Verify colors match across all views

---

## 5. Study Guides

### Features
- Create with seed verse + theme
- Add/remove/reorder steps
- Graph path suggestions
- Verse preview in steps
- Export as JSON/HTML
- Publish as shareable URL
- Fork published studies
- LLM-powered study editor (`<study-action>` blocks)
- "Quick Ask" per-step Q&A

### Known Issues
- [ ] Study creation with new works — verify seed verses from DSS/Pseudepigrapha work
- [ ] Graph suggestions for non-standard works — verify paths exist
- [ ] Export HTML — does it include all 9 works?
- [ ] Publish slug generation — may conflict with special characters

### Review Steps
1. Create study: "Angel of the Lord", seed `gen.16.7`
2. Add step: verse `exo.3.2`, title "Burning Bush"
3. Add step: verse `judg.13.3`, title "Manoah's Visitor"
4. Suggest path from seed → verify connections appear
5. Export as JSON → verify file contains all steps
6. Export as HTML → open in browser, verify it's self-contained
7. Publish study → verify slug URL works
8. Fork published study → verify editable copy created
9. Open study in StudyEditor → ask LLM "Add a step about Melchizedek"
10. Apply the LLM's `<study-action>` → verify step is inserted

---

## 6. Hebrew Learning

### Features
- Aleph-bet lesson viewer (102 lessons across 7 categories)
- Interactive quizzes (letter recognition, typing, transliteration)
- Verb conjugation drills (HebrewVerbDrill)
- Vocabulary flashcards with SRS
- Hebrew diagnostic assessment
- Hebrew keyboard input helper
- Markdown rendering with `:verse[]` + `:strong[]` for examples

### Known Issues
- [ ] **DONE** `rehype-raw` missing in HebrewVerbDrill — Fixed
- [ ] **DONE** `rehype-raw` missing in LearnView — Fixed
- [ ] Lesson content may use `:verse[]` markers that weren't rendering — should work now
- [ ] Quiz questions for DSS/Pseudepigrapha books — may not exist
- [ ] Hebrew keyboard might not work on mobile

### Review Steps
1. Open Hebrew Lessons → verify categories load (letter, vowel, word, grammar, etc.)
2. Click "Aleph" lesson → verify content renders with interactive verse chips
3. Take a Hebrew quiz → verify questions, typing, and scoring work
4. Open verb drill → verify conjugation exercise works
5. Open vocabulary cards → verify card flip and review
6. Check any `:verse[]` or `:strong[]` markers in lessons → verify they render as clickable chips
7. Test Hebrew keyboard → verify it works in input fields
8. Open Hebrew diagnostic → verify questions adapt

---

## 7. Learning System (Cards/Memorization)

### Features
- Card queue with spaced repetition
- Daily verse card
- Passage reader for memorization
- Audio review session (Shmuelof recordings)
- FIRe penalty flow
- Palace-guided ordering
- Macro-interleaving
- Card factory (lesson→cards conversion)

### Known Issues
- [ ] Audio alignments — only 108 verses have audio
- [ ] Card factory — may not handle new works
- [ ] Passage reader — verify navigation works for all 9 works

### Review Steps
1. Open Daily Verse → verify verse + word breakdown + audio (if available)
2. Add verse to memorize queue → verify it appears in queue
3. Open CardQueue → verify card flip, rate buttons, progress
4. Open PassageReader → type a ref from Pseudepigrapha → verify it loads
5. Open AudioReview → verify audio plays for verses that have it
6. Check PalaceView → verify palace rooms and loci work

---

## 8. Wiki

### Features
- Entity article viewer (people, places, concepts)
- Browse by entity type
- Full-text search within wiki
- Markdown rendering with `:verse[]`, `:entity[]`, `:strong[]`
- Cross-linked entities

### Known Issues
- [ ] **DONE** `rehype-raw` missing in WikiArticleViewer — Fixed
- [ ] Wiki content may reference entities that don't exist in new works
- [ ] Browse may only show limited entity types

### Review Steps
1. Open wiki article for "Abraham" → verify content renders with interactive verse chips
2. Click a `:verse[]` link → verify verse popup opens
3. Click an `:entity[]` link → verify navigates to that entity's article
4. Browse entities → verify categories show results
5. Search wiki for "covenant" → verify results appear
6. Check article for DSS entity (e.g., "Melchizedek" from 11Q13) → verify content

---

## 9. Connection Graph

### Features
- Visual force-directed graph of verse connections
- Center verse with N-hop connections
- Work-colored nodes
- Edge type filtering
- Click to navigate

### Known Issues
- [ ] **DONE** `WORK_COLORS` missing 4 works — Fixed
- [ ] **DONE** `guessWorkFromRef` misidentifies everything as PGP — Fixed
- [ ] Graph may be slow for highly-connected verses
- [ ] Force layout may overlap nodes on small screens

### Review Steps
1. Open graph for `gen.1.1` → verify nodes appear with correct work colors
2. Check connections from `tob.1.1` → verify node color is rose (apocrypha)
3. Check connections from `1QS.1.1` → verify node color is amber (DSS)
4. Check connections from `1en.1.1` → verify node color is indigo (pseudepigrapha)
5. Filter by connection layer → verify graph updates
6. Click a node → verify it navigates to that verse
7. Test on mobile — verify graph is usable

---

## 10. Verse Features (Gematria, Connections, PaRDeS)

### Features
- Verse text with Hebrew/Greek/English
- Interlinear word-by-word analysis
- Gematria (standard, ordinal, reduced)
- Connections (11 layers, typed edges)
- PaRDeS levels (Pshat, Remez, Drash, Sod)
- Hidden patterns (atbash, acrostics, temurah)
- Passage guide (instant all-in-one view)
- Verse comparison
- Entity detection and linking

### Known Issues
- [ ] Interlinear may not have data for all DSS/Pseudepigrapha texts
- [ ] Gematria only works for Hebrew/Greek texts
- [ ] Passage guide may be slow for new books (no pre-computed guide)
- [ ] Entity linking may not cover non-canonical entities

### Review Steps
1. Open `gen.1.1` → verify text, Hebrew, connections, gematria all display
2. Open interlinear for `gen.1.1` → verify word-by-word breakdown
3. Open `gen.1.1` connections → verify 11 layers listed
4. Open PaRDeS for `gen.1.1` → verify 4 levels with content
5. Open Sod for `gen.1.1` → verify hidden patterns
6. Compare `gen.1.1` vs `john.1.1` → verify comparison view
7. Check passage guide for a Pseudepigrapha verse → verify it loads
8. Check entity links for a DSS verse → verify entities detected

---

## 11. Assessment System

### Features
- Adaptive scripture knowledge assessment
- Configurable target layer (Pshat → Sod)
- Question branching based on answers
- Progress tracking

### Known Issues
- [ ] Assessment questions may not cover new works
- [ ] Difficulty calibration for non-standard texts

### Review Steps
1. Start an assessment (Pshat level) → verify questions appear
2. Answer correctly → verify next question is harder
3. Answer incorrectly → verify branching to easier question
4. Check progress → verify score and position shown
5. Complete assessment → verify summary

---

## 12. Audio System

### Features
- Daily verse audio playback
- Read-along audio alignment
- Shmuelof recordings (Hebrew OT)
- Audio review for memorization

### Known Issues
- [ ] Only 108 verses have audio alignments
- [ ] No audio for NT, BoM, or other works
- [ ] Audio may not load on slow connections

### Review Steps
1. Open Daily Verse for a Psalm → verify audio plays audio button appears
2. Click read-along → verify audio syncs with text
3. Open AudioReview → verify queue plays consecutively

---

## 13. Settings & Theming

### Features
- Dark/light mode toggle
- Font size adjustment
- Footnotes, gematria, lemma display toggles
- Search scope (works, layers, language)
- Bible version preference
- Display language (English/Hebrew/Greek)
- Transliteration toggle

### Known Issues
- [ ] **DONE** `searchWorks` missing 3 works in ToggleProvider — Fixed
- [ ] Font size changes may not persist across sessions
- [ ] Bible version preference only affects verse display

### Review Steps
1. Toggle dark mode → verify theme changes
2. Change font size → verify text resizes
3. Uncheck "Apocrypha" in search scope → verify chat scope updates
4. Change Bible version → verify verse display changes
5. Toggle footnotes/gematria/lemma in chapter view → verify display updates

---

## 14. Tabs & Workspaces

### Features
- Multiple workspaces (subjects)
- Tab management (open, close, reorder)
- Drag-and-drop tabs between workspaces
- Session persistence
- Tile dashboard view

### Known Issues
- [ ] **DONE** `deleteWorkspaces` and `reorderWorkspaces` are undefined props — need audit
- [ ] Tab state may not restore correctly after app refresh
- [ ] Drag-and-drop may not work on mobile

### Review Steps
1. Create new workspace → verify it appears in tile view
2. Navigate to Genesis 1 in one workspace
3. Navigate to Isaiah 55 in another workspace
4. Switch between workspaces → verify each remembers position
5. Close a tab → verify remaining tabs reorder
6. Open tile dashboard → verify all workspaces shown
7. Refresh page → verify last workspace/tab restored

---

## 15. MCP & API Tools

### Features
- 60+ HTTP API endpoints
- MCP server with 52 tools
- RAM cache for fast responses
- Auto-generated OpenAPI docs
- Cross-lingual search (Hebrew/Greek/English)
- Graph traversal (path, reachable, hubs, centrality)

### Known Issues
- [ ] Some endpoints may not have been tested with new `position` column
- [ ] Books cache needs warmup on server restart (already fixed for single-worker)
- [ ] Multi-worker mode skips RAM cache for verses/guides (but not books)

### Review Steps
1. `GET /api/v1/books` → verify 9 works in correct order
2. `GET /api/v1/verses/gen.1.1` → verify response with text + connections
3. `GET /api/v1/verses/1en.1.1` → verify DSS/Pseudepigrapha work
4. `GET /api/v1/verses/1her.1.1` → verify Expanded Canon work
5. `GET /api/v1/search?q=covenant` → verify results from all works
6. `POST /api/v1/chat` with test message → verify response
7. `GET /api/v1/studies` → verify study CRUD works
8. `GET /api/v1/graph/path?start=gen.1.1&end=john.1.1` → verify path found

---

## Execution Strategy

### Phase 1: Critical Fixes (1-2 sessions)
- Navigation/viewRef bugs
- Chat rendering (DONE)
- Missing work maps (DONE)

### Phase 2: Feature Coverage (2-3 sessions)  
- Study guides with new works
- Hebrew learning with all works
- Wiki entity coverage

### Phase 3: Polish (1-2 sessions)
- Icon consistency
- Mobile responsiveness
- Error states and empty states
- Loading indicators

### Phase 4: Performance (1 session)
- API response times with cold cache
- Frontend bundle size
- Graph rendering performance

---

## How to Track Progress

For each section above, create a checklist item in the session's todo list:

```
[ ] Section N: Feature Name — reviewed, issues documented, fixed
```

When you complete a section, note:
- What was tested
- What issues were found
- What was fixed
- Any remaining concerns
