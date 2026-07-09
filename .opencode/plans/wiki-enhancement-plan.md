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

## Track J: Online Enrichment — Wikipedia & Wikidata `[ ]`

Enrich all wiki articles with data from free online sources — summaries, dates, family relationships, coordinates, images, and external links.

### Phase J1: Wikidata Integration `[ ]`
- [ ] Add Wikidata SPARQL queries to the generator script:
  - For each entity, query `https://query.wikidata.org/sparql` for:
    - Wikipedia summary / description
    - Birth/death dates (for people)
    - Father, mother, spouse, children (family relationships)
    - Coordinate location (for places)
    - Image (Commons thumbnail)
    - Occupation, religion, title
- [ ] Fallback: Wikipedia REST API (`en.wikipedia.org/api/rest_v1/page/summary/{name}`)
- [ ] Cache results to avoid repeated API calls
- ⏱ Timebox: 2hrs
- ✅ Checkpoint: Jesus Christ article includes Wikidata-sourced birth/death dates and family relationships
- ⚙ Fallback: Skip Wikidata if unreachable, use only DB data

### Phase J2: Geographical Data Integration `[ ]`
- [ ] Download OpenBible.info Geocoding data (`https://github.com/openbibleinfo/Bible-Geocoding-Data`)
- [ ] Create `scripts/import_geodata.py` that ingests:
  - `ancient.jsonl` — biblical places with coordinates and verse refs
  - `modern.jsonl` — modern location equivalents
- [ ] Create a new table `place_geography` (or extend `entity_links`) with coordinates
- [ ] Add `/api/v1/geo/{entity_id}` endpoint to serve map data
- [ ] For each place entity (Jerusalem, Zion, Egypt, etc.), embed coordinates in wiki article
- ⏱ Timebox: 3hrs
- ✅ Checkpoint: Jerusalem wiki article includes coordinates and map link
- ⚙ Fallback: Use hardcoded coordinates for top 20 places

### Phase J3: Image Integration `[ ]`
- [ ] For each entity, fetch Wikipedia Commons image via Wikidata
- [ ] Store image URL in wiki article frontmatter
- [ ] Display thumbnail in Wiki Article Viewer
- ⏱ Timebox: 1hr
- ✅ Checkpoint: Abraham article shows an image
- ⚙ Fallback: Use openbible.info thumbnails (180MB zip available)

### Phase J4: Cross-Reference Import `[ ]`
- [ ] Import OpenBible.info cross-reference data (~340K cross-references)
- [ ] Add `cross_references` table if it doesn't already exist (check existing `text_resources` or `connections` table)
- [ ] Use to suggest related wiki articles
- ⏱ Timebox: 2hrs
- ✅ Checkpoint: Entity articles show cross-references to related articles

---

## Track K: Book-Level Wiki Content `[ ]`

Generate comprehensive wiki pages for each of the 330 books and 8 works. Each book page aggregates all available data from the DB.

### Phase K1: Book Page Generator `[ ]`
- [ ] Extend `generators/generate_wiki_articles.py` with book mode:
  - For each book in `books` table, query:
    - Total verses, chapters
    - Unique connection types that appear
    - Top connected verses (hubs)
    - Gematria highlights
    - Entities mentioned most frequently
    - Key intertextual connections (OT-in-NT, etc.)
    - Chiastic structures detected
  - Output to `knowledge/wiki/books/{book_id}.md`
- [ ] **Priority**: Genesis, Exodus, Psalms, Isaiah → Matthew, John, Acts, Romans, Revelation → 1 Nephi, Alma → all 330 books
- ⏱ Timebox: 3hrs
- ✅ Checkpoint: `knowledge/wiki/books/matthew.md` exists with chapter counts, key connections, entities

### Phase K2: Work Overview Pages `[ ]`
- [ ] Generate 8 work pages at `knowledge/wiki/works/{work_id}.md`:
  - OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha
  - Each includes: book count, verse count, total connections, key themes, notable entities
  - Historical context (sourced from Wikipedia/Wikidata)
- ⏱ Timebox: 1.5hrs
- ✅ Checkpoint: 8 work pages exist with substantive content

### Phase K3: Connection Layer Pages `[ ]`
- [ ] Generate 11 layer explainer pages at `knowledge/wiki/layers/{layer}.md`:
  - What the layer detects, examples of each type, how to interpret results
  - Example verses with that connection type
- ⏱ Timebox: 2hrs
- ✅ Checkpoint: All 11 layer pages exist

---

## Track L: Wiki Content Pipeline Automation `[ ]`

### Phase L1: Run Script `[ ]`
- [ ] Add `./run.sh wiki-generate` command that runs the full wiki generation pipeline:
  1. Generate entity articles (Track G1 — all 87+ entities)
  2. Generate book articles (Track K1 — all 330 books)
  3. Generate work overviews (Track K2 — 8 works)
  4. Generate layer explainers (Track K3 — 11 layers)
  5. Optionally fetch online enrichment (Track J)
- ⏱ Timebox: 1hr
- ✅ Checkpoint: `./run.sh wiki-generate` produces output to `knowledge/wiki/`

### Phase L2: Content Quality Review `[ ]`
- [ ] Manual review of top-10 articles (Jesus Christ, Abraham, Jerusalem, Covenant, etc.)
- [ ] Fix any factual errors or gaps in auto-generated content
- [ ] Verify cross-references between articles
- ⏱ Timebox: 2hrs
- ✅ Checkpoint: Top-10 articles reviewed and corrected

---

## Dependency Map

```
Track F (Stats Update) ── ✅ DONE — live DB numbers fixed
Track G (Articles) ───── depends on live DB (we have it at /tmp/scripture.db)
Track H (LXX Load) ───── independent
Track I (UI) ─────────── depends on G (needs articles to browse)
Track J (Online Enrich) ─ independent of G, parallel
Track K (Book Content) ── depends on G generator script
Track L (Pipeline) ───── depends on G, J, K all done
```

## Execution Order (Parallel)

```
Week 1:
  Track G1 (Entity Generator) ───── start now!
  Track J1 (Wikipedia/Wikidata) ─── parallel — online lookup
  Track I (UI) ──────────────────── parallel — frontend work

Week 2:
  Track J2 (Geography) ──────────── load coordinate data
  Track K1-K3 (Books/Works/Layers) ── generate remaining content
  Track H (LXX) ─────────────────── find and load Septuagint

Week 3:
  Track L1 (Pipeline) ───────────── automate regeneration
  Track L2 (Quality Review) ─────── manual polish
```

## Quick Wins (Today)

| # | What | Time | Why |
|---|------|------|-----|
| 1 | ✅ Fix all doc numbers to live DB stats | 30min | Done in previous commit |
| 2 | Build wiki article generator script | 2hrs | Core engine for all content |
| 3 | Generate Jesus Christ article | 30min | Most glaring hole |
| 4 | Fetch Wikipedia summaries for top 20 entities | 30min | Enrich with online data |

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
