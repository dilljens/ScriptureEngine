# Sources & Attribution

Every connection in the scripture knowledge graph has a `discovered_by` field and optionally a `metadata` JSON field that tracks **who** found it, **what work** it came from, and a **tag** for cross-referencing. This page documents all sources.

---

## How Source Tracking Works

Two fields on every connection:

```
discovered_by   — who/what discovered this connection
metadata        — JSON with scholar, source, tag, note
```

The `discovered_by` field uses a trust-weight system (see `lib/controls/calibration.py`):

| discovered_by | Trust Weight | Meaning |
|---|---|---|
| `text` | 1.0 | Explicit text-level connection (the text itself makes this connection) |
| `tsk` | 0.85 | Treasury of Scripture Knowledge (historical cross-reference) |
| `human` | 0.80 | Human-curated by a scholar explicitly |
| `llm` / `ai` | 0.75 | Agent-driven (person read both verses and judged) |
| `algorithm` | 0.35 | Machine-detected pattern, not yet verified |

The `metadata` field stores scholarly attribution:
```json
{
  "scholar": "L. Michael Morales",
  "source": "Who Shall Ascend the Mountain of the Lord",
  "tag": "morales_ascent",
  "note": "Morales: 'Who shall ascend the mountain of YHWH?'..."
}
```

### Source Tags

Every scholarly source has a unique **tag** that appears in connection metadata. Tags let you query all connections from a specific scholar using `scripture_sources(scholar_tag="morales_ascent")`.

---

## Discovery Methods

### `tsk` — Treasury of Scripture Knowledge
- **Tag:** `tsk`
- **Connections:** 213,176
- **Description:** The Treasury of Scripture Knowledge is a classic Bible cross-reference compiled by 19th-century scholars. It identifies every place where a verse is quoted, alluded to, or echoed elsewhere in scripture.
- **License:** Public domain
- **Reference:** Torrey, R. A. *The Treasury of Scripture Knowledge*. Revell, 1870+.

### `algorithm` — Algorithmic Generators
- **Tag:** `algorithm`
- **Connections:** 812,002
- **Description:** 35 automated generators detect connections by matching lemmas, roots, gematria values, structural patterns, geographic references, etc. See `generators/__init__.py` for the full list.
- **License:** Project-internal (generator code)

### `text` — Text-Explicit
- **Tag:** `text`
- **Connections:** 4,603
- **Description:** Connections that are explicit in the text itself — mostly Dead Sea Scrolls variants where the text directly differs from the Masoretic Text.
- **License:** CC-BY-NC (BiblicalDSS, ETCBC/dss)

### `human` / `llm` — Human & Agent-Driven
- **Tag:** varies (see scholarly sources below)
- **Connections:** 680
- **Description:** Connections curated by human scholars or LLM agents reading both verses and judging the relationship. These include all sod-layer and interpretive-layer connections.

---

## Biblical Text Sources

| Source | Text | Content | License |
|--------|------|---------|---------|
| Open Scriptures Hebrew Bible (OSHB) | Hebrew (MT) | 23,213 verses with morphology | Public domain / CC-BY |
| SBL Greek New Testament (SBLGNT) | Greek (NT) | 7,925 verses with morphology | CC-BY 4.0 |
| Latin Vulgate (Clementine) | Latin | 31,077 verses | Public domain |
| StepBible Data | Hebrew + Greek | Text tagging, morphology | CC-BY 4.0 |
| Open Scriptures HebrewLexicon | Hebrew | Strong's definitions, BDB | CC-BY 4.0 |
| morphgnt strongs-dictionary-xml | Greek | Strong's definitions | **CC0** (public domain) |
| BiblicalDSS | DSS Hebrew | 266 scrolls, verse-alignned | CC-BY-NC 4.0 |
| ETCBC/dss | DSS Hebrew | 797 scrolls with morphology | CC-BY-NC 4.0 |

---

## Scholarly Sources (Sod Layer)

### Margaret Barker — Temple Theology
- **Tag:** `barker_temple`
- **Connections:** 75
- **Key Works:**
  - *Temple Theology: An Introduction* (2004)
  - *The Great Angel: A Study of Israel's Second God* (1992)
  - *Temple Mysticism: An Introduction* (2011)
  - *The Great High Priest: The Temple Roots of Christian Liturgy* (2003)
- **Contribution:** First Temple theology — the Angel of YHWH as a distinct divine being, temple as microcosm, Day of Atonement as cosmic ritual, theosis through temple access.
- **Sod Types:** `angel_of_yhwh`, `temple_microcosm`, `divine_council`, `holy_of_holies`, `theosis`, `eden_temple`, `divine_marriage`, `kingdom_priesthood`, `watchers_enedochic`, `mercy_seat`, `divine_ascent`, `cosmic_mountain`, `sacred_center`

### L. Michael Morales — Ascent Theology
- **Tag:** `morales_ascent`
- **Connections:** 27
- **Key Works:**
  - *Who Shall Ascend the Mountain of the Lord? A Biblical Theology of Leviticus* (IVP Academic, 2015, NSBT Vol. 37)
- **Contribution:** The organizing question of Psalm 24:3 — "Who shall ascend the mountain of the LORD?" — frames the entire Pentateuch. The tabernacle cult, Day of Atonement, and Christ's ascension are God's answer. The Exodus is a journey from exile to God's dwelling; Leviticus is the liturgy of ascent.
- **Sod Types:** `temple_ascent`, `cosmic_mountain`, `eden_temple`, `holy_of_holies`

### Dead Sea Scrolls (ETCBC/BiblicalDSS)
- **Tag:** `dss_etcbc`, `dss_biblical`
- **Connections:** 4,603 (variants) + 20 (sectarian)
- **Data Sources:**
  - ETCBC/dss dataset (CC-BY-NC 4.0)
  - BiblicalDSS JSON (CC-BY-NC 4.0)
- **Contribution:** DSS variant readings compared verse-by-verse with the Masoretic Text. Sectarian texts (1QS, 11Q13, 4Q400, etc.) connected to biblical parallels.
- **Sod Types:** `dead_sea_scrolls_variant` (textual), `dss_sectarian` (sod)

---

## License Information

| Dataset | License | Attribution Required |
|---------|---------|---------------------|
| OSHB Hebrew text | Public domain / CC-BY | Yes |
| SBLGNT | CC-BY 4.0 | "SBL Greek New Testament (SBLGNT)" |
| Latin Vulgate | Public domain | — |
| StepBible Data | CC-BY 4.0 | "STEPBible.org / Tyndale House, Cambridge" |
| HebrewLexicon | CC-BY 4.0 | "Open Scriptures Hebrew Lexicon" |
| morphgnt strongs | **CC0** | No attribution needed |
| BiblicalDSS | CC-BY-NC 4.0 | "BiblicalDSS — ETCBC/dss data" |
| ETCBC/dss | CC-BY-NC 4.0 | "ETCBC/dss — Martin Abegg data" |
| Treasury of Scripture Knowledge | Public domain | — |
| Connection generator code | Project-internal | — |

---

## Plans for Expansion

- **G.K. Beale** (`beale_temple`) — temple-creation typology
- **Michael Heiser** (`heiser_council`) — divine council, Deuteronomy 32
- **Andrei Orlov** (`orlov_merkabah`) — Enoch-Metatron, two powers in heaven
- **Peter Schäfer** (`schafer_hekhalot`) — Hekhalot mysticism, origins of Jewish mysticism
- **Jon Levenson** (`levenson_temple`) — Sinai/Zion, creation and temple
- **Hugh Nibley** (`nibley_temple`) — comparative temple traditions
- **Stephen Dempster** (`dempster_dominion`) — dominion/dynasty, land as temple
- **John Walton** (`walton_cosmic`) — cosmos as temple in ANE context
- **Christopher Rowland** (`rowland_apocalyptic`) — apocalyptic as mysticism
- **April DeConick** (`deconick_mystic`) — early Christian ascent mysticism
- **Crispin Fletcher-Louis** (`fletcherlouis_temple`) — angelomorphic Christology
- **John Day** (`day_canaanite`) — divine council, Chaoskampf
- **Mark S. Smith** (`smith_divine_family`) — divine family, monotheism origins
- **James VanderKam** (`vanderkam_dss`) — DSS, Enoch, priesthood
- **Martha Himmelfarb** (`himmelfarb_ascent`) — heavenly ascent in apocalypses
- **Gabriele Boccaccini** (`boccaccini_enoch`) — Enochic Judaism
- **Richard Bauckham** (`bauckham_christology`) — divine identity Christology
- **Loren Stuckenbruck** (`stuckenbruck_angel`) — Watchers, angel veneration
- **Tryggve Mettinger** (`mettinger_presence`) — divine presence, Shem/Kabod
- **Moshe Weinfeld** (`weinfeld_deut`) — temple ideology, rest theology
