# Macro-Analysis Plan — Beyond Verse-to-Verse Connections

*Adding higher-order biblical analysis to ScriptureEngine: passage-level, book-level, thematic, genre-based, and reception-historical connections.*

---

## Current State

ScriptureEngine has **1.77M verse-to-verse connections** across 11 layers and 100+ types. The new `passage_connections` table and its generators (density cluster, book coherence, chiastic promoter) add the first layer of macro-structural analysis. This plan covers the remaining dimensions.

---

## The 10 Missing Dimensions

| # | Dimension | What It Connects | Effort | Value |
|---|-----------|-----------------|--------|-------|
| 1 | **Passage-level connections** | Verse ranges → verse ranges via density | ✅ Done | ★★★★★ |
| 2 | **Genre clusters** | Passages/books by literary genre | Low | ★★★★★ |
| 3 | **Thematic trajectories** | Passages by shared biblical theme | Medium | ★★★★★ |
| 4 | **Inner-biblical interpretation network** | Quotation/allusion chains with transitive closure | Medium | ★★★★☆ |
| 5 | **Narrative analogy (typology)** | OT type → NT antitype narrative arcs | Medium | ★★★★☆ |
| 6 | **Source/critical layers** | Passages by scholarly source attribution | High | ★★★☆☆ |
| 7 | **Multilingual textual network** | MT ↔ LXX ↔ Vulgate ↔ Peshitta passage alignment | Medium | ★★★☆☆ |
| 8 | **Social setting / Sitz im Leben** | Passages by social context | High | ★★★☆☆ |
| 9 | **Rhetorical analysis** | Passages by rhetorical structure | Medium | ★★★☆☆ |
| 10 | **Reception history** | Passages linked through interpretive tradition | Very High | ★★★☆☆ |

---

## Phase 1: Genre Clusters (Low Effort, High Impact)

### Problem

No generator tags or connects passages by literary genre. A user reading an apocalypse (Daniel 7) has no way to find other apocalyptic passages (Revelation, Mark 13, some Isaiah). Genre is one of the most intuitive ways scholars group biblical texts.

### Schema

Add a `passage_genres` table:

```sql
CREATE TABLE passage_genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    genre TEXT NOT NULL,            -- 'apocalyptic', 'wisdom', 'lament', 'genealogy', etc.
    subgenre TEXT DEFAULT '',
    confidence REAL DEFAULT 0.7,
    assigned_by TEXT DEFAULT 'algorithm',  -- 'algorithm', 'scholar', 'consensus'
    notes TEXT DEFAULT '',
    UNIQUE(start_verse, end_verse, genre)
);

CREATE INDEX IF NOT EXISTS idx_pg_genre ON passage_genres(genre);
```

### Predefined Genres

Using standard biblical genre classifications:

| Genre | Example Passages | Subgenres |
|-------|-----------------|-----------|
| `apocalyptic` | Dan 7-12, Rev, Mark 13, Ezek 38-39 | heavenly ascent, end-times, vision report |
| `wisdom` | Prov, Eccl, Job, James, Sirach, Wis | proverb, reflection, disputation |
| `lament` | Psalms (13, 22, 137), Lam, Job 3 | individual lament, communal lament |
| `genealogy` | Gen 5, 10, 1 Chron 1-9, Matt 1, Luke 3 | linear, segmented, mixed |
| `legal` | Exod 20-23, Lev, Deut 12-26 | apodictic, casuistic, holiness code |
| `covenant_suit` | Deut 32, Isa 1, Mic 6, Hos 4 | prosecution, witness summons, verdict |
| `prophetic_call` | Isa 6, Jer 1, Ezek 1-3, Amos 7 | commission, objection, reassurance |
| `psalm` | Psalms, some OT canticles | royal, thanksgiving, lament, wisdom, pilgrimage |
| `parable` | Gospels, 2 Sam 12 | narrative parable, similitude, example story |
| `epistle` | NT letters, some OT letters | greeting, thanksgiving, body, paraenesis |
| `gospel` | Matt, Mark, Luke, John | synoptic, Johannine |
| `historical_narrative` | Genesis-Kings, Chronicles, Acts | annals, court history, theological history |
| `vision_report` | Ezek 1-3, Dan 7-8, Zech 1-6, Rev 1 | throne vision, tour vision, symbolic vision |
| `torah` | Gen-Deut (as whole) | narrative, legal, poetic |
| `midrash` | Some later OT passages, NT use of OT | pesher, typological, allegorical |
| `song_hymn` | Song of Sol, Ps 18, Exod 15, Judg 5 | wedding song, victory hymn, love song |
| `prophecy_oracle` | Major/minor prophets | judgment oracle, salvation oracle, woe oracle |

### Generator: Genre Tag Applier

**File:** `generators/passage/genre_tagger.py`

```python
def run(conn, book_ids=None) -> int:
    """Tag passages with genres based on book-level genre assignments and
    internal structural markers.

    Phase 1: Apply known book-wide genres (e.g., Psalms → psalm, Proverbs → wisdom)
    Phase 2: Detect per-passage genres using structural formulas and keywords
             (e.g., 'Woe to...' marker → woe oracle; 'vision of...' → vision report)
    Phase 3: Create passage_connections for passages sharing the same genre

    Returns count of passage connections created.
    """
```

Two passes:
1. **Book-level defaults** — map known book genres to verse ranges
2. **Structure-based detection** — use existing `structural_formulas` table to refine

### Output

For each genre, create `passage_connections` records between all passages sharing that genre:

```
genre: apocalyptic
  Dan 7-12 → Rev 1-22  (same_genre, strength: 0.9)
  Dan 7-12 → Mark 13   (same_genre, strength: 0.7)
  Rev 1-22 → Mark 13   (same_genre, strength: 0.7)
  Dan 7-12 → Ezek 38-39 (same_genre, strength: 0.6)

genre: wisdom
  Proverbs → Ecclesiastes  (same_genre, strength: 0.9)
  Proverbs → Job           (same_genre, strength: 0.8)
  Sirach → Wisdom of Solomon (same_genre, strength: 0.9)
  James → Proverbs         (same_genre, strength: 0.7)
```

### Lines: ~250

---

## Phase 2: Thematic Trajectories (Medium Effort, Very High Value)

### Problem

Major biblical themes (covenant, temple, exile, remnant) run through the entire canon but aren't tracked. A user studying "the temple" can't see how tabernacle (Exodus 25-31), temple dedication (1 Kings 8), Ezekiel's temple vision (Ezek 40-48), Jesus cleansing the temple (John 2), and the heavenly temple (Rev 21) are connected.

### Schema

Add a `theme_keywords` table and a `passage_themes` bridge:

```sql
CREATE TABLE theme_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,         -- 'temple', 'covenant', 'exile', 'remnant', etc.
    description TEXT DEFAULT '',
    keywords TEXT DEFAULT '[]',        -- JSON array of keyword objects
    parent_theme_id INTEGER REFERENCES theme_definitions(id),
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE passage_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    theme_id INTEGER NOT NULL REFERENCES theme_definitions(id),
    strength REAL DEFAULT 0.5,         -- how strongly this passage embodies the theme
    UNIQUE(start_verse, end_verse, theme_id)
);
```

### Theme Definitions (15 Initial Themes)

| Theme | Keywords (Hebrew/English) | Key Passages |
|-------|--------------------------|-------------|
| `temple` | mishkan, hekal, bayit, naos, hieron | Exod 25-31, 1 Kings 5-8, Ezek 40-48, John 2, Rev 21 |
| `covenant` | berit, diatheke, brit | Gen 15, Exod 19-24, Deut 29, Jer 31, Luke 22, Heb 8-10 |
| `exile` | golah, galut, diaspora | Deut 28, 2 Kings 25, Jer 29, Ezek 1, Dan 1, 1 Pet 1 |
| `remnant` | shear, sarid, leimar | Isa 10, Zeph 3, Rom 9-11, Ezek 6 |
| `exodus_new_exodus` | yetziah, apolutrosis | Exod 1-15, Isa 40-55, Mark 1, Luke 9, 1 Cor 10 |
| `day_of_the_lord` | yom yhwh, hemera kyriou | Joel 2, Zeph 1, Mal 4, 1 Thess 5, 2 Pet 3 |
| `wisdom_presence` | chokmah, sophia | Prov 8, Wis 7, John 1, Col 1, Heb 1 |
| `divine_presence` | shekinah, kavod, doxa | Exod 40, 1 Kings 8, Ezek 43, John 1, Rev 21 |
| `sacrifice_atonement` | korban, hilasterion | Lev 1-7, Lev 16, Isa 53, Heb 9-10, 1 John 2 |
| `kingdom_of_god` | malkut, basileia | Dan 2, 7, Synoptic Gospels, Rev 11-12 |
| `creation_new_creation` | bara, ktisis | Gen 1-2, Isa 65, Rom 8, Rev 21-22 |
| `election_chosen_people` | bachar, eklektos | Deut 7, 14, Isa 41-45, Rom 8-11, 1 Pet 2 |
| `land_promised_land` | eretz, ge | Gen 12, 15, 17, Deut 8, Josh 1-12, Heb 11 |
| `suffering_servant` | ebed, pais | Isa 42, 49, 50, 52-53, Phil 2, 1 Pet 2 |
| `judgment_mercy` | mishpat, krisis, eleos | Amos, Hos, Mic, Matt 23, Rom 9-11, James 2 |

### Generator: Theme Tracer

**File:** `generators/passage/theme_tracer.py`

```python
def run(conn, book_ids=None) -> int:
    """Trace thematic keywords through the canon and create
    passage-level connections between passages sharing themes.

    1. Load theme definitions with keyword lists
    2. Search verses for keyword occurrences (using existing word_frequency table)
    3. Cluster consecutive keyword-heavy verses into theme passages
    4. Create passage_connections for same-theme passages
    5. Also create cross-theme connections where themes overlap (e.g., temple+covenant)

    Returns count of passage connections created.
    """
```

### Output

For each theme, create passage_connections between all passages that strongly embody it:

```
theme: temple
  Exod 25-31 → 1 Kings 5-8        (tabernacle dedication → temple dedication)
  Exod 25-31 → Ezek 40-48         (tabernacle → Ezekiel's temple vision)
  1 Kings 5-8 → John 2            (Solomon's temple → Jesus' cleansing)
  Ezek 40-48 → Rev 21             (Ezekiel's temple → heavenly Jerusalem)

theme: covenant
  Gen 15 → Exod 19-24             (Abrahamic → Sinaitic)
  Exod 19-24 → Jer 31             (Sinaitic → New Covenant)
  Jer 31 → Luke 22                (New Covenant prophecy → institution)
  Luke 22 → Heb 8-10              (Institution → theological exposition)
```

### Lines: ~400 (definitions) + ~300 (generator) = ~700

---

## Phase 3: Inner-Biblical Interpretation Network (Medium Effort)

### Problem

`direct_quotation` and `allusion` connections exist at verse level, but there's no transitive network analysis. If Isaiah 40:3 is quoted in Matthew 3:3 and Matthew 3:3 is alluded to in Mark 1:3, there should be a connection between Isaiah 40 and Mark 1 (transitive closure). Also, the network should track how interpretive tradition accumulates — later citations carry the interpretive weight of earlier ones.

### Algorithm

```
1. Build graph: verse → quoted_verse edges from direct_quotation connections
2. Compute transitive closure (up to depth 5):
   If A quotes B and B alludes to C, create A → C with decreased strength
3. Cluster chains into passage-level trajectories:
   Isa 40 → Matt 3 → Mark 1 → Luke 3 → John 1 → various Church Fathers
4. Store as passage_connections with type='quotation_chain'
```

### Schema Extension

Add to `passage_connections` metadata:
```json
{
    "chain_length": 5,
    "intermediaries": ["matt.3.3", "mark.1.3", "luke.3.4"],
    "chain_types": ["direct_quotation", "allusion", "allusion", "allusion"],
    "interpretive_shift": "wilderness → preparation → herald → incarnation"
}
```

### Generator: Quotation Chain Network

**File:** `generators/passage/quotation_network.py`

### Lines: ~250

---

## Phase 4: Narrative Analogy / Typology (Medium Effort)

### Problem

Typology connects OT patterns to NT fulfillments, but these are narrative arcs, not single verses. The Exodus narrative (Exod 1-15) as a type of Christ's work is a connection between two large narrative blocks, not between any specific verse in Exodus and any specific verse in the Gospels.

### Approach

Define **typological patterns** as named narrative arcs with slot-based matching:

```
Pattern: "Deliverance through a divinely-appointed leader"
  Slots:
    - Oppressed people (Israel in Egypt / humanity in sin)
    - Reluctant leader (Moses / Christ in Gethsemane)
    - Signs/wonders (plagues / miracles)
    - Passover sacrifice (lamb / Christ)
    - Deliverance through water (Red Sea / baptism)
    - Wilderness testing (40 years / 40 days)
    - Covenant at mountain (Sinai / Sermon on Mount)

Known typological pairs:
  Exodus 1-15  →  Gospel passion narratives   (Exodus typology)
  Tabernacle   →  Christ's incarnation         (Temple typology)
  Manna        →  Lord's Supper               (Sacrament typology)
  Bronze serpent →  Cross                     (Salvation typology)
  Flood        →  Baptism                     (Judgment typology)
```

### Schema

```sql
CREATE TABLE typological_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    slots_json TEXT DEFAULT '[]',          -- JSON array of slot definitions
    created_by TEXT DEFAULT 'algorithm',
    source TEXT DEFAULT ''                 -- 'scholar', 'church_father', 'algorithm'
);
```

### Generator: Typology Matcher

**File:** `generators/passage/typology_matcher.py`

For each defined typological pair, create a passage_connection between the OT type passage and the NT antitype passage with type `type_antitype` at passage level (already exists at verse level).

### Lines: ~250

---

## Phase 5-10: Lower Priority

| Phase | What | Why Lower Priority |
|-------|------|-------------------|
| **5** | Source/Critical layers | Requires importing external scholarly data; no existing dataset |
| **6** | Multilingual network | Requires full text alignment infrastructure; existing variants module covers some |
| **7** | Social setting | Requires manual tagging or NLP classification of 30K+ passages |
| **8** | Rhetorical analysis | Builds on structural_formulas; could be added incrementally |
| **9** | Reception history | Requires importing patristic, rabbinic, and reformation data |
| **10** | Covenant structure matcher | Already partially handled by structural generators |

---

## Implementation Summary

| Phase | What | Files | Lines | Priority |
|-------|------|-------|-------|----------|
| P0 | Passage-level (already done) | Schema + 3 generators + API + MCP | ~1,100 | ✅ Done |
| **P1** | **Genre clusters** | `passage_genres` table, `genre_tagger.py`, API endpoint | ~250 | 🔴 Next |
| **P2** | **Thematic trajectories** | `theme_definitions`, `passage_themes`, `theme_tracer.py`, API | ~700 | 🔴 Next |
| **P3** | Quotation network | `quotation_network.py` + transitive closure | ~250 | 🟠 Soon |
| **P4** | Typology patterns | `typological_patterns` table, `typology_matcher.py` | ~250 | 🟠 Soon |
| P5 | Source layers | External data, `source_layers` table | ~300 | 🟡 Later |
| P6 | Multilingual alignment | Text alignment infrastructure | ~400 | 🟡 Later |
| P7 | Social setting | NLP + manual tagging | ~300 | 🟡 Later |
| P8 | Rhetorical analysis | Structure-based generator | ~200 | 🟡 Later |
| P9 | Reception history | External data import | ~350 | 🟢 Future |

**Total remaining: ~2,700 lines across 9 phases.**

---

## Architecture Note

All these features write to the same `passage_connections` table. The API endpoints (`GET /api/v1/passage/{ref}/connections`, `GET /api/v1/chapter/{book}/{chapter}/connections`, etc.) automatically surface any new connection type. Frontend components (heatmap, KnowledgeGraphView, WikiLayout sidebar) display them without modification.

The key principle: **one schema, many generators, unified API**.
