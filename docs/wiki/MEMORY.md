# Scripture Engine — Project Memory

_Last updated: 2026-07-13_

## System Overview

| Metric | Value |
|--------|-------|
| Verses | 70,956 across 8 works (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha) |
| Connections | 1,769,593 typed edges across 11 layers |
| Tradition labels | 5: none (52%), multiple (23%), jewish (22%), christian (2%), lds (2%) |
| Wiki articles | 60 (20 entities + 40 doctrinal) + new PassageReader audio setup |
| Learning modules | 26 with lesson content + worked examples + adaptive questions |
| Hub notes | 14 curated learning paths (88 steps) |
| Assessment questions | 247 (200 MC + 47 LLM-graded open-ended) |
| Thematic clusters | 41 multi-witness consistency themes |
| API endpoints | 60+ HTTP |
| Database | SQLite (`data/processed/scripture.db` — 1.7GB) |
| Hebrew DB | `data/memorize.db` — 642 nodes, FSRS-5 scheduling |
| JS Discourses | 945 texts imported (Joseph Smith discourses, TEV001-945) |
| JST Version | Full Joseph Smith Translation imported as version + 8,796 connections |

## Architecture

- **Web framework**: FastAPI (Python) with Uvicorn
- **Frontend**: React + Vite + Tailwind CSS
- **Deployment**: OVHcloud VPS (4 vCore, 8GB RAM), systemd + Nginx
- **CI**: Pre-deploy gate — Python tests (38), graph regression, DB integrity, frontend build

### Route modules (`web/routes/`)

| Module | Lines | Purpose |
|--------|-------|---------|
| `hebrew.py` | ~1,505 | Hebrew curriculum, FSRS-5, FIRe, gamification |
| `chat.py` | ~980 | LLM proxy to DeepSeek with tool calling |
| `graph.py` | ~1,070 | Connection graph API + LLM grading + provenance |
| `learn.py` | ~460 | Learning modules with lessons + adaptive practice |
| `memorize.py` | ~928 | Verse queue + FSRS-5 memorization review + repetition compression |
| `assessment.py` | ~210 | Adaptive quiz endpoint with user progress tracking |
| `auth.py` | ~300 | Google OAuth + anonymous merge + user progress |
| `audio.py` | 124 | Read-along audio playback + DailyVerse audio |
| `studies.py` | 397 | Study guides CRUD |
| `conversations.py` | 167 | Conversation sessions |
| `js_discourses.py` | NEW | Joseph Smith discourses import server endpoint |

## Core Systems

### Learn (replaces Quiz)
Structured courses following The Math Academy Way:
- 26 modules: 14 from hub notes + 12 from Topical Guide
- Each module: direct instruction → worked examples → adaptive practice
- Questions: adaptive ordering (weakest first), 3 tiers (text, analysis, consistency)
- 47 LLM-graded open-ended questions with AI evaluation (4-dimension rubric)
- Mastery tracking with FSRS-5 spaced repetition

### Hebrew Learning
Biblical Hebrew curriculum (642 nodes across 7 levels):
- Practice: 428 items across MC, typing, recall, transliteration, production
- **New**: Cloze (fill-in-the-blank) cards and translation cards
- **New**: PassageReader — read-along with highlighted verse text synchronized to audio
- **New**: AudioReview — listen to Hebrew audio, type what you hear
- **New**: DailyVerse — daily Hebrew verse with audio
- Smart MC distractors using confusable letter pairs
- FSRS-5 spaced repetition with FIRe implicit credit
- **New**: FIRe penalty flow — failing a review item deducts credit
- **New**: Macro-interleaving — cross-module practice mixing
- **New**: Non-interference scheduling — prevent similar items from conflicting
- **New**: Targeted remediation — weakest items get priority review
- **New**: Summer slide protection — adaptive boost for returning users
- **New**: Student-topic learning speeds — ability/difficulty ratio tracked per topic
- Mukdam u'Meuchar (early/late) literary pattern detection in Hebrew
- 1,716 verse attestations (630/642 nodes show real scripture examples)
- Audio playback for Genesis 1 alignments (Shmuelof recordings)

### Memorize Queue
Verse memorization with FSRS-5:
- Add/search verses by reference, add entire chapters
- Review queue sorted by retrievability (most forgotten first)
- Rating: Again (1) / Hard (2) / Good (3) / Easy (4)
- Per-verse mastery tracking

### Truth Alignment (v2 — New)
Confidence calibration upgraded from linear weighted sum to Bayesian ensemble:
- **Bayesian confidence**: `posterior_odds = prior_odds × product(LR₁...LRₙ)` — each discovery method and connection type has a likelihood ratio. Text-explicit = 20×, algorithm = 1.5×
- **Source tiering**: S0 (canonical text) through S4 (algorithmic) — affects prior odds
- **Inter-source agreement**: 3 independent sources → 2.5× multiplier
- **Contradiction detection**: `CONTRADICTION_MATRIX` with 30+ type-pair conflict scores, `disagreements` table for tracking
- **Temporal decay**: Half-life per method (algorithm=2yr, human=5yr, text=never)
- **Confidence propagation**: Path confidence via product × length penalty × layer compatibility
- Audit script: `scripts/calibration_audit.py` — weekly health report

### Connection Graph
1.77M typed edges with provenance:
- 11 layers: linguistic, numerical, intertextual, structural, interpretive, symbolic, textual, geographic, chronological, frequency, sod
- Tradition labels: each connection tagged with tradition (jewish, christian, lds, multiple)
- 41 thematic clusters showing multi-witness consistency
- Graph exploration API with BFS traversal, centrality scoring
- **New**: Truth-seeking framework — distinguishes textual truth from interpretive tradition; disagreements API cross-references contradictory readings

### Literary Pattern Detection (New)
Multi-verse literary structure analysis:
- **Chiasm detection**: multi-pass algorithmic scanning (v1-v3 final) — A-B-C-C'-B'-A' mirror structures across entire books
- **Mukdam u'Meuchar**: Hebrew literary technique where chronological order is rearranged for thematic purposes
- **All-pattern detection**: unified pipeline scanning for chiasms, inclusios, and other literary forms
- Integration with connection graph: detected patterns become structural connections

### Topical Guide + Bible Dictionary
- 677 LDS Topical Guide topics with descriptions and verse references
- 47 Bible Dictionary entries
- 31,065 verse→TG connections in the graph
- Sefaria Jewish tradition: 387K+ connections (Rashi, Ramban, Talmud, Zohar, Midrash)

### Wiki
- 60 articles: 20 biblical entities + 40 doctrinal topics from Topical Guide
- Integrated into learning modules as supplementary content
- Accessible via tabs (📖 Wiki) on desktop + mobile

### Auth
- Anonymous user ID in localStorage (persists across refreshes)
- Google OAuth endpoint (`POST /api/v1/auth/google`)
- Anonymous progress merge (`POST /api/v1/auth/merge`)
- User progress aggregation (`GET /api/v1/user/progress/{id}`)

### LLM Integration
- DeepSeek API with tool calling (52 MCP tools)
- Chat rendering: react-markdown with verse chip integration
- LLM grading for open-ended answers with user context
- Segment-based rendering (markdown + verse chips coexist)

### Audio System (New)
- **Shmuelof recordings**: Hebrew Genesis 1 audio from Shmuelof.com
- **DailyVerse**: Audio playback for daily Hebrew verse
- **PassageReader**: Read-along text highlighting synchronized to audio
- **AudioReview**: Listen-and-type Hebrew comprehension practice
- **AudioPlay route**: `GET /api/v1/audio/play` serving Hebrew audio segments

### JS Discourses + JST (New)
- **945 Joseph Smith discourses** imported from TEV001-945 PDF corpus
- **Full JST version** ingested as a selectable Bible version
- **8,796 JST connections** (jst_change + jst_addition types) linking JST changes to original text
- **Disagreements system**: seed data for contradictory readings across traditions

## UI Features

- Desktop: Library → Work → Book → Chapter navigation with zoom
- Mobile: 5-tab bottom nav (Read, Chat, Hebrew, Learn, Review) + ⋮ More
- Command palette (`/`), Chat shortcut (`?`)
- Dark mode, font size controls, keyboard shortcut hints
- All features as persistent tabs (hebrew, learn, memorize, wiki, hubnote, chat)
- Double-tap immersion mode (hides all UI bars)
- **New**: Hebrew cloze cards, translation cards in Learn tab
- **New**: PassageReader read-along in Hebrew tab
- **New**: DailyVerse audio widget in Hebrew tab

## Monitoring

- Health endpoint: `GET /api/v1/health` — DB integrity, layer/tradition distribution, version, uptime
- Slow request logging (>2s) via middleware
- JSON structured logger replacing print()
- ntfy.sh push notifications on health check failure
- Pre-deploy gate: 38 Python tests + graph regression + PRAGMA integrity_check
