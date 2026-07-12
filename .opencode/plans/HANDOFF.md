# Scripture Engine — Agent Handoff

## Project Overview

A deeply connected scripture knowledge engine with **1,356,667 typed connections** across **11 layers** (linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod) spanning **70,956 verses** across **8 works** (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha).

**Stack**: Python 3.14 (FastAPI) + SQLite 3 + React 19 (Vite 6) + Tailwind CSS 4 + Cytoscape.js
**Database**: 1.4GB SQLite at `data/processed/scripture.db`
**API**: FastAPI at `web/server.py` (103+ endpoints) + MCP server at `mcp_server.py` (61 tools)
**Frontend**: React SPA at `frontend/src/` (40 components)

## What Was Built (This Session)

### ✅ Wiki Article System (427 files in `knowledge/wiki/`)
- **Generator**: `generators/generate_wiki_articles.py` creates Markdown articles from live DB
  - 86 entity articles (people, places, concepts, titles)
  - 314 book articles (chapter counts, connections, entities)
  - 8 work overviews (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha)
  - 11 connection layer explainers (star ratings, PaRDeS, Bloom, difficulty explained)
- **Enrichment**: Wikidata SPARQL + Wikipedia REST API for summaries, dates, images, family
- **WikiArticleViewer** (`frontend/src/components/WikiArticleViewer.jsx`): renders articles in app
- **Wiki search**: `GET /api/v1/wiki/search?q=` endpoint
- **Wiki button** in toolbar, wiki tab view, `openWikiTab()` in tabContext

### ✅ Wiki ↔ Assessment Integration
- **Learn More**: Assessment returns `learn_more` wiki links on ALL answers (reason: "explore"/"review")
- **Test Yourself**: `/api/v1/assess/entity/{entity_id}` — entity-filtered assessment
- **Entity sidebar links**: Clickable entities in WikiLayout → open wiki article tab

### ✅ Partial Credit Assessment
- `BLIM.update_bayesian()` accepts float `correctness` (0.0–1.0), interpolates between posteriors
- `submit_answer()` accepts `correctness` param
- Questions return options with `correctness_weight` per option
- `KnowledgeState.record_response()` tracks fractional correctness

### ✅ SVG Force Graph in WikiLayout
- `ConnectionGraphSVG` component renders circular-layout graph with layer-colored edges
- Collapsible edge list below the visual graph

### ✅ Documentation Updates
- All docs updated to use LIVE DB stats (1,356,667 connections, 70,956 verses, 330 books)
- Stats verifier: `scripts/project_stats.py`

## What's PENDING (Needs Next Agent)

### 🔴 High Priority — AssessmentView Frontend
**File**: `frontend/src/components/AssessmentView.jsx`

Needs 3 things:
1. **Learn More rendering** (B2 in plan): After `submit_answer`, the API returns `learn_more` array. Currently the component ignores it. Need to render wiki links:
   - Correct answers: show "Explore more about [Entity]" in green
   - Wrong answers: show "Review [Entity] to master this" in amber
   - Links should open WikiArticleViewer

2. **Entity filtering** (B1 in plan): Support `entityId` prop. When present:
   - Use `/api/v1/assess/entity/{entity_id}` endpoint 
   - Show entity name in header
   - "Test Yourself" from wiki pages passes this

3. **Partial credit UI** (B3 in plan): Options now have `correctness_weight`:
   - Show partial correctness visually (amber for 0.0<weight<1.0)
   - Pass `correctness` param to `submit_answer`
   - Show "% correct" indicator

4. **Fix category stub** (D2): Replace hardcoded `cat = 'word'` fallback (lines 38-43) with actual question data

### 🟡 Medium Priority — WikiLayout Graph Integration
**Plan C1**: The SVG graph is good but the full `ConnectionGraph` component (Cytoscape.js) has interactive features (drag, zoom, hover). Consider wiring it in for WikiLayout's graph panel.

### 🟢 Low Priority — Stubs & Placeholders
- **StructureModal**: Wire to existing chiasms data from chapter endpoint
- **MemorizeView**: "Future phase" cards are placeholders
- **PalaceBuilder**: Verse picker toggle never fires

## Key Files Reference

| File | Purpose |
|------|---------|
| `generators/generate_wiki_articles.py` | Wiki article generator (entities, books, works, layers) |
| `frontend/src/components/WikiArticleViewer.jsx` | Renders wiki articles in the app |
| `frontend/src/components/WikiLayout.jsx` | Wikipedia-style chapter view with SVG graph |
| `frontend/src/components/ChapterView.jsx` | Main chapter reader with wiki mode toggle |
| `frontend/src/components/AssessmentView.jsx` | **NEEDS WORK** — knowledge assessment UI |
| `frontend/src/App.jsx` | Main app — view router, toolbar, keyboard shortcuts |
| `frontend/src/tabContext.jsx` | Tab/workspace system, view management |
| `frontend/src/api.js` | API client functions |
| `lib/api/assessment.py` | Assessment API (learn_more, partial credit) |
| `lib/assessment/models.py` | BLIM IRT model with partial credit |
| `lib/assessment/engine.py` | Adaptive assessment engine |
| `web/server.py` | FastAPI server — learn + assess endpoints at lines ~1558-1640 |
| `lib/api/verse.py` | study_verse tool, LXX detection |
| `lib/api/graph.py` | graph_context, entity_deep tools |
| `lib/api/connections.py` | compare_verses, research_topic tools |
| `knowledge/wiki/entities/*.md` | 86 generated entity articles |
| `knowledge/wiki/books/*.md` | 314 generated book articles |
| `knowledge/wiki/works/*.md` | 8 work overviews |
| `knowledge/wiki/layers/*.md` | 11 layer explainers with educational content |
| `.opencode/plans/feature-improvements.md` | Full plan with remaining tasks |

## Running the Project

```bash
# Start API server
./run.sh web            # http://localhost:8002/docs

# Generate wiki articles
python3 generators/generate_wiki_articles.py --entity covenant
python3 generators/generate_wiki_articles.py --all-entities
python3 generators/generate_wiki_articles.py --all-layers

# With Wikidata enrichment (slower)
python3 generators/generate_wiki_articles.py --all-entities --enrich

# Generate top book articles
python3 -c "
from generators.generate_wiki_articles import generate_book_article, write_article, BOOKS_DIR
import sqlite3
conn = sqlite3.connect('data/processed/scripture.db')
conn.row_factory = sqlite3.Row
for bk in ['gen','exo','matt','john','rev']:
    article = generate_book_article(conn, bk)
    if article: write_article({'id': bk, **article}, BOOKS_DIR)
conn.close()
"

# Start frontend dev server
cd frontend && npm run dev

# Project stats
python3 scripts/project_stats.py
```

## Key Architecture Details

### View System (App.jsx)
```
viewLevel determines what renders:
  tiles → library → work → book → chapter (zoom hierarchy)
  Also: chat, graph, memorize, study, wiki
```

### Tab System (tabContext.jsx)
- Workspaces → Tabs → View
- Each tab has: `book, chapter, view, viewRef, companion`
- `openWikiTab(entityId, label)` — opens/focuses wiki tab
- `openMemorizeTab()` — opens/focuses memorize tab

### Wiki ↔ Assessment Bridge
- `GET /api/v1/learn/{knowledge_item_id}` — wiki articles for a knowledge item
- `GET /api/v1/assess/entity/{entity_id}` — assessment filtered to entity
- `GET /api/v1/wiki/{entity_id}` — get wiki article content
- `GET /api/v1/wiki/search?q=` — search wiki articles

### Assessment Data Flow
1. Knowledge items (685K) → filtered connections with quality, PaRDeS, difficulty, Bloom level
2. `AssessmentEngine.select_item()` → picks most informative item using IRT + fringe boost
3. `BLIM.update_bayesian(prior, correct, correctness)` → posterior mastery probability
4. Response includes `learn_more` wiki article links on all answers

## Known Issues & Gotchas

1. **No LXX Greek text loaded**: The Greek fallback in `web/server.py` checks `text_resources WHERE version='LXX'` but returns 0 rows. OT Greek won't work until Septuagint data is imported.

2. **DB is 1.4GB**: Can't commit to git. Available via GitHub Releases or copy from production VPS (40.160.241.74 — needs SSH key).

3. **Wiki articles are static files**: The `knowledge/wiki/` files are committed to git. They get stale if the DB changes — regenerate with the generator script.

4. **WikiArticleViewer uses WIKI_CACHE**: The server loads `wiki_articles` DB table into RAM at startup. The generated files in `knowledge/wiki/` are independent from this — they're Markdown on disk, not served by the API. The API serves from `wiki_articles` table (20 articles, all people). The 427 generated files are human-readable in the repo but NOT served by the API yet.

5. **AssessmentView incomplete**: The `AssessmentView.jsx` component exists but doesn't handle `learn_more`, `correctness_weight`, or entity filtering. These all work on the backend but the frontend hasn't been wired up.

6. **Biblical_transliteration dependency**: Not installed in the dev environment. The Python import chain from `lib.api.verse.py` requires it. Tests need `pip install biblical-transliteration`.
