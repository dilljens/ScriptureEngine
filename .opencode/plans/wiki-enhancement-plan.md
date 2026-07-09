# Wiki Enhancement Plan

## Live DB Reality (from production database)

| Metric | Previous (stale) | Actual (live DB) |
|--------|-----------------|-------------------|
| Total connections | 1,028,083 | **1,356,667** |
| Total verses | 42,054 | **70,956** |
| Books | 224 | **330** |
| Gematria entries | 305K | **392,256** |
| Passage guides | 41K | **41,645** |
| Connection types | 131 | **124** (some merged/removed) |
| Wiki articles | unknown | **20** — all people, no Jesus, no places, no concepts |
| LXX Greek text | assumed available | **0 — not loaded** |
| Entity links | 87 | **87** (correct) |

### Wiki Article Gap

**EXISTS** (20 articles, all people):
Abraham, Adam, Daniel, David, Elijah, Eve, Ezekiel, Isaac, Isaiah, Jacob, Jeremiah, John the Baptist, Joseph, Moses, Noah, Paul, Peter, Samuel, Sarah, Solomon

**MISSING — Critical:**
- **Jesus Christ** — no article at all (the central figure!)
- **Mary** (mother of Jesus)
- **John the Apostle** / John the Revelator
- **Matthew, Mark, Luke** (Gospel writers)

**MISSING — Places (87 entities exist but 0 articles):**
Jerusalem, Zion, Egypt, Babylon, Sinai, Jordan, Galilee

**MISSING — Concepts (87 entities exist but 0 articles):**
Covenant, Kingdom, Spirit, Heaven, Earth, Faith, Grace, Atonement, Temple, Messiah

**MISSING — All 66+ books, 8 works, 11 layers**

---

## Track F: Live Stats Update `[ ]`

### Phase F1: Fix All Numbers `[ ]`
- [ ] Update README.md with live DB stats (1,356,667 connections, 70,956 verses, 330 books, 392K gematria)
- [ ] Update CHAT_AGENTS.md header ("1,356,667 typed connections")
- [ ] Update web/server.py docstring ("1,356,667 connections across 124 types")
- [ ] Update knowledge/wiki/_index.md stats
- [ ] Fix scripts/project_stats.py default to use live DB numbers
- ✅ Checkpoint: All doc numbers match live DB output
- ⚙ Fallback: Use /tmp/scripture.db numbers as source of truth

### Phase F2: Fix AGENTS.md Local `[ ]`
- [ ] Update the `.opencode/AGENTS.md` file that says "1,028,083" to the correct "1,356,667"
- [ ] Update "42,054 verses" to "70,956 verses"
- [ ] Update "52 MCP/HTTP tools" to "61"
- ✅ Checkpoint: grep shows correct numbers in AGENTS.md

---

## Track G: Wiki Article Generation `[ ]`

Generate comprehensive wiki articles from the live database — for every entity, book, work, and layer. The DB already has everything needed (connections, gematria, entities, verses). A script can assemble it into prose.

### Phase G1: Entity Article Generator `[ ]`
- [ ] Create `generators/generate_wiki_articles.py` that for each entity in `entity_links`:
  - Fetches all verses mentioning the entity
  - Fetches key connections involving those verses
  - Generates a structured wiki article:
    ```
    # Title (English Name)
    Hebrew: … | Greek: … | Strong's: …
    
    ## Overview
    [Auto-generated summary from entity data]
    
    ## Key Verses
    - verse 1: "text..."
    - verse 2: "text..."
    
    ## Connections
    - type → related verse (layer)
    
    ## Related Entities
    - Person A (co-occurs in X verses)
    - Place B
    ```
  - Outputs to `knowledge/wiki/entities/{entity_id}.md`
  - **Priority order**: Jesus Christ (missing!), Mary, John the Apostle, Matthew, Mark, Luke, then all 87 entities
- ⏱ Timebox: 4hrs
- ✅ Checkpoint: `knowledge/wiki/entities/jesus_christ.md` exists and has substantive content
- ⚙ Fallback: Generate Markdown manually for Jesus Christ first, script the rest

### Phase G2: Book Feature Articles `[ ]`
- [ ] Extend generator to create book wiki pages:
  - Each of 330 books gets a page at `knowledge/wiki/books/{book_id}.md`
  - Content: book title, work, chapter count, total verses, key connections, gematria highlights
  - Top priority: Genesis, Exodus, Psalms, Isaiah, Matthew, John, Acts, Romans, Revelation, 1 Nephi, Alma, D&C 76
- ⏱ Timebox: 3hrs
- ✅ Checkpoint: `knowledge/wiki/books/genesis.md` overwritten with richer content

### Phase G3: Work Overview Pages `[ ]`
- [ ] Create 8 work overview pages at `knowledge/wiki/works/`:
  - OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha
  - Each includes: book count, verse count, key themes, notable connections
- ⏱ Timebox: 1hr
- ✅ Checkpoint: 8 work pages exist

### Phase G4: Connection Layer Explainers `[ ]`
- [ ] Create 11 layer explainer pages at `knowledge/wiki/layers/`:
  - Each explains what the layer detects, types it includes, examples
  - linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod
- ⏱ Timebox: 2hrs
- ✅ Checkpoint: All 11 layer pages exist with examples

---

## Track H: LXX Data Acquisition `[ ]`

### Phase H1: Find & Load Septuagint `[ ]`
- [ ] Research available LXX sources (STEPBible, GreekResources, etc.)
- [ ] Write `scripts/import_lxx.py` that downloads/populates `text_resources` with `version='LXX'`, `language='grc'`
- [ ] Verify Greek display works for OT verses after loading
- ⏱ Timebox: 3hrs
- ✅ Checkpoint: `SELECT COUNT(*) FROM text_resources WHERE version='LXX'` > 20,000
- ⚙ Fallback: Use existing Bible data sources (STEPBible already listed in README)

---

## Track I: Wiki Frontend Integration `[ ]`

### Phase I1: Wiki Article Viewer `[ ]`
- [ ] Create `frontend/src/components/WikiArticleViewer.jsx` — renders wiki articles in the app
  - Fetches from `/api/v1/wiki/{entity_id}`
  - Renders Markdown content
  - Shows key verses as clickable links
  - Shows cross-references
- [ ] Add "Wiki" tab to the app's SubjectTabBar
- ⏱ Timebox: 3hrs
- ✅ Checkpoint: Clicking "Wiki" tab shows Abraham article with verse links

### Phase I2: Entity Links in WikiLayout `[ ]`
- [ ] Make entity names in the WikiLayout sidebar clickable
- [ ] Clicking an entity opens the wiki article for it
- ⏱ Timebox: 1hr
- ✅ Checkpoint: Clicking "Abraham" in sidebar opens the Abraham wiki article

---

## Dependency Map

```
Track F (Stats Update) ── start first, fast fix
Track G (Articles) ───── depends on live DB copy
Track H (LXX Load) ───── independent
Track I (UI) ─────────── independent of G (uses API, not files)
```

## Quick Wins (Today)

| # | What | Time | Why |
|---|------|------|-----|
| 1 | Fix all doc numbers to live DB stats | 30min | Accuracy matters for everything |
| 2 | Write Jesus Christ wiki article | 1hr | Most glaring hole — central figure |
| 3 | Generate script for remaining entity articles | 2hrs | 87 articles from DB data |

## Connection Layer Pages — Quick Reference

| Layer | Key Idea | Example Types |
|-------|----------|---------------|
| linguistic | Same lemma, root, wordplay | same_lemma, same_root, cognate |
| numerical | Gematria values match | same_gematria_standard, divine_name_value |
| structural | Literary mirroring | chiastic, parallel_synonymous, inclusio |
| intertextual | Quotes and allusions | direct_quotation, allusion, type_antitype |
| textual | Manuscript differences | textual_variant, jst_change, dss_variant |
| geographic | Same location | same_location, journey_path, mountain_of_god |
| chronological | Same time period | genealogical, feast_connection, jubilee_cycle |
| interpretive | Tradition's reading | rabbinic_midrash, patristic, giliadi_pattern |
| frequency | Word occurrence patterns | hapax_legomenon, 7_fold_pattern |
| symbolic | Shared symbols | shared_symbol, apocalyptic_creature, temple_symbol |
| sod | Hidden/temple meaning | temple_ascent, divine_council, merkabah |
