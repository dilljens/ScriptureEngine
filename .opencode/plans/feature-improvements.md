# Site Feature Improvements — Detailed Plan

## Completed (this session)
- [x] Learn More shows on ALL answers (correct + wrong), with reason="explore"/"review"
- [x] Partial credit assessment: BLIM.update_bayesian accepts `correctness` float (0.0–1.0)
- [x] assess_response passes correctness through to BLIM + KnowledgeState
- [x] submit_answer accepts optional `correctness` parameter
- [x] Questions return `options` with `correctness_weight` per option
- [x] Options normalized so frontend always gets structured `{label, correctness_weight}`

---

## Track A: Wiki in the App `[ ]`

### Phase A1: WikiArticleViewer Component `[ ]`
- [ ] Create `frontend/src/components/WikiArticleViewer.jsx`:
  - Fetches from `/api/v1/wiki/{entity_id}`
  - Renders article content as Markdown (uses existing react-markdown)
  - Shows "Test Yourself" button that links to `/api/v1/assess/entity/{id}`
  - Shows related entities as clickable links
  - Shows key verses as VerseChip links
  - Displays article metadata (type, generated date)
- [ ] Add "Wiki" tab to SubjectTabBar that opens entity browser
- [ ] Create entity browser: list of all 86 entities by type (person, place, concept)
- ⏱ 3hrs | ✅ Checkpoint: Navigating to `/wiki/covenant` shows full article with rendered Markdown

### Phase A2: Entity Links in WikiLayout Sidebar `[ ]`
- [ ] Make entity names in WikiLayout sidebar clickable
- [ ] Click opens WikiArticleViewer in a modal or new tab
- [ ] Entities show tooltip with summary on hover
- ⏱ 1hr | ✅ Checkpoint: Clicking "Abraham" in WiKiLayout sidebar opens Abraham wiki article

### Phase A3: Wiki Search Integration `[ ]`
- [ ] Add `/api/v1/wiki/search?q=` endpoint that searches wiki article titles + summaries
- [ ] Modify `/api/v1/search` to include wiki results alongside verse results
- [ ] Frontend SearchBar shows wiki article results with "📖 Wiki" badge
- ⏱ 2hrs | ✅ Checkpoint: Searching "covenant" shows the Covenant wiki article as a top result

---

## Track B: Assessment Improvements `[ ]`

### Phase B1: AssessmentView Entity Filtering `[ ]`
- [ ] Support `?entity=covenant` query param in AssessmentView
- [ ] When entity param present, call `/api/v1/assess/entity/{entity_id}` instead of default start
- [ ] Show entity name and item count in assessment header
- ⏱ 2hrs | ✅ Checkpoint: `/assess?entity=covenant` starts an assessment on covenant connections

### Phase B2: Learn More Rendering in AssessmentView `[ ]`
- [ ] After each answer, check response for `learn_more` array
- [ ] If present, render wiki article links with reason:
  - Correct: "Explore more about [Entity] →" (green)
  - Wrong: "Review [Entity] to master this →" (amber)
- [ ] Clicking link opens WikiArticleViewer
- ⏱ 1.5hrs | ✅ Checkpoint: Wrong answer shows "Review Covenant" link that opens wiki article

### Phase B3: Partial Credit in AssessmentView `[ ]`
- [ ] For questions with options that have `correctness_weight`, show partial correctness:
  - Fully correct (weight=1.0): green check, full credit
  - Partially correct (0.0<weight<1.0): amber indicator, partial credit
  - Wrong (weight=0.0): red x
- [ ] Pass `correctness` parameter to `submit_answer` based on selected option's weight
- [ ] Show visual indicator of how correct the answer was
- ⏱ 2hrs | ✅ Checkpoint: Selecting a partially right option shows "67% correct" and passes correctness=0.67

---

## Track C: Graph & Visualization `[ ]`

### Phase C1: WikiLayout Graph → Real ConnectionGraph `[ ]`
- [ ] Replace text-list graph panel in WikiLayout with the existing `ConnectionGraph` component
- [ ] Lazy-load ConnectionGraph (already lazy-loaded in App.jsx)
- [ ] Pass chapter-level connections as graph data
- ⏱ 2hrs | ✅ Checkpoint: WikiLayout shows interactive Cytoscape.js graph instead of text edge list

### Phase C2: Layer Filters in ConnectionGraph `[ ]`
- [ ] Wire ToggleProvider layer toggles to ConnectionGraph edge filtering
- [ ] Toggling "numerical" off hides numerical edges in the graph
- [ ] Toggling quality filter shows only ★★★+ connections
- ⏱ 2hrs | ✅ Checkpoint: Can filter graph to show only intertextual connections

---

## Track D: Fix Stubs & Placeholders `[ ]`

### Phase D1: StructureModal `[ ]`
- [ ] Wire to chapter endpoint's existing chiasms data
- [ ] Render detected chiastic structures with A-B-C-B'-A' visualization
- [ ] Show scholar attribution and confidence scores
- ⏱ 1hr | ✅ Checkpoint: StructureModal shows actual chiasms for Isaiah

### Phase D2: AssessmentView Category Stub `[ ]`
- [ ] Replace hardcoded `cat = 'word'` fallback
- [ ] Use actual knowledge_items layer or connection_type from the question data
- ⏱ 30min | ✅ Checkpoint: AssessmentView shows the correct category for each question

---

## Dependency Map

```
Track A (Wiki in App) ── independent, can start immediately
  A1 → A2 → A3 (sequential, A1 unlocks A2/A3)
Track B (Assessment) ─── independent
  B1 → B2, B3 parallel (B1 needed for entity assessment)
Track C (Graph) ─────── independent
Track D (Fixes) ─────── independent, quick wins
```

## Priority Order

```
Week 1:
  A1: WikiArticleViewer ⭐⭐⭐ — biggest gap
  B2: Learn More in AssessmentView ⭐⭐⭐ — already have the API
  D2: Fix category stub ⭐ — 30min quick win

Week 2:
  A2: Entity sidebar links ⭐⭐
  B3: Partial credit in AssessmentView ⭐⭐⭐
  C1: WikiLayout → real ConnectionGraph ⭐⭐

Week 3:
  A3: Wiki search ⭐⭐
  B1: Entity filtering ⭐⭐
  C2: Graph layer filters ⭐
  D1: StructureModal ⭐
```
