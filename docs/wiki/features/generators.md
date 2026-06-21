# Connection Generators — generators/

All connection discovery algorithms live in `generators/`. Each generator creates typed connections between verses in the `connections` table.

**35 generators** registered (33 algorithmic + 2 manual), generating across all 10 layers.

## Architecture

```
generators/
  ├── __init__.py                       — GENERATOR_DEFS registry + run_all()/run_generator()
  #
  # Core algorithmic generators
  ├── linguistic.py                     — Same rare lemma matches
  ├── same_root.py                      — Same triconsonantal root across lemmas
  ├── morphology.py                     — Same rare morphological form (morph codes)
  ├── structural.py                     — Chiastic A↔A', B↔B' pairs
  ├── parallelism.py                    — 10 parallelism types (synonymous, antithetic, step, etc.)
  ├── formula_markers.py                — Structural formula same-position links
  ├── semuchin.py                       — Adjacent verses sharing rare lemmas
  ├── intertextual.py                   — Shared rare-word clusters (direct_quotation, allusion, echo)
  ├── numerical_full.py                 — Gematria value matches + sacred numbers + verse totals
  ├── ordinal_reduced_gematria.py       — Ordinal + reduced gematria (incl. divine-name reduced)
  ├── gematria_factor.py                — Word values as multiples of sacred numbers / divine names
  ├── gematria_sum.py                   — Within-verse gematria sum relationships (A + B = C)
  ├── frequency.py                      — Sacred-number word frequencies (7, 10, 12, 40)
  ├── hapax_dislegomenon.py             — Rare lemmas (2-5 verses) frequency connections
  ├── geographic.py                     — Place name matching
  ├── geographic_subtypes.py            — 7 geographic themes (journey, wilderness, exile, etc.)
  ├── chronological.py                  — Time period / timeline / dispensation connections
  ├── chronological_marker.py           — Time formula markers (regnal years, prophetic formulas)
  ├── feast_connection.py               — Biblical feast/holy day connections
  ├── genealogical.py                   — Person entities + genealogical formulas + NT↔OT links
  ├── cyclical_time.py                  — Sabbatical + jubilee cycle connections
  ├── acrostic.py                       — Hebrew alphabetic acrostic detection + symmetric pairs
  ├── refrain.py                        — Repeated structural formula refrains within books
  ├── chiasm_detector.py                — Algorithmic chiastic candidate detection via word-count mirroring
  ├── interpretive.py                   — Interpretive tradition connections (hardcoded)
  ├── spiritual_levels.py               — Giliadi's 7 spiritual levels of humanity
  ├── isaiah_keywords.py                — Hebrew linking keywords in Giliadi's parallel structure
  ├── isaiah_advanced.py                — 11 advanced Giliadi techniques
  ├── isaiah_pseudonyms.py              — Giliadi pseudonym twin-pair system
  ├── cross_canon_pseudonyms.py         — Pseudonym detection applied to non-Isaiah books
  ├── cross_canon_chaos.py              — Chaos/de-creation motifs in non-Isaiah books
  ├── experiment_cross_canon.py         — All Isaiah methods × all canonical books (experimental)
  ├── hendiadys.py                      — Known hendiadys pairs (X and Y)
  #
  # External data — ingested, then compared
  ├── morphology.py                     — WLC/Treebank morph codes
```

```
  #
  # Textual variant ingestion (generates connections)
  ├── scripts/ingest_vulgate.py         → textual_variants table → vulgate_variant connections
  #
  # Self-referencing cross-canon quotation generator
  ├── scripts/generate_self_references.py  → direct_quotation for BoM→Isaiah, D&C→OT, etc.
```

## Agent-Driven Connection Types (no generator module needed)

For 13 connection types, connections are authored directly by the agent reading the text (no API, no external cost):

```
data/agent_connections/
  ├── prophetic_fulfillment_judgments.json    — OT→NT fulfillment pairs
  ├── type_antitype_judgments.json            — Typological patterns
  ├── modified_quotation_judgments.json       — Intentional NT quote changes
  ├── wordplay_judgments.json                 — Hebrew paronomasia
  ├── nomen_est_omen_judgments.json           — Name meanings in narrative
  ├── midrashic_connection_judgments.json     — NT rabbinic hermeneutics
  ├── summarized_judgments.json               — OT summarized in later texts
  ├── apocalyptic_time_judgments.json         — Time symbols (3.5 years, "in that day")
  ├── cognate_judgments.json                  — Hebrew↔Aramaic cognates
  ├── semantic_domain_judgments.json          — Conceptual domains
  ├── prophetic_quote_judgments.json          — Modern prophetic use of scripture
  ├── lectio_divina_judgments.json            — Monastic reading tradition
  ├── inspired_revision_judgments.json        — JST expansions
  └── apocalyptic_symbology_judgments.json    — Cross-vision symbol reuse (Tier 1+3 only)
```

Each contains judgments with source/target verses, confidence scores, and human-readable reasoning.

## Generator Count

As of 2026-06-17: **35 generators** registered (33 algorithmic `automatic=True`, 2 needing curation `automatic=False`). Plus 13 agent-judged connection types supplementing with reasoned connections.

## Generator Contract

Every generator exports:
```python
def run(conn, book_ids=None) -> int:  # Returns connection count
```

Registered in `generators/__init__.py`:
```python
GENERATOR_DEFS = [
    {
        "name": "Linguistic — Same Lemma",
        "module_path": ".linguistic",
        "layers": ["linguistic"],
        "automatic": True,        # Can run without AI review
        "requires": "gematria table",
        "description": "...",
    },
    # ...
]
```

## Running Generators

```bash
# Run all automatic generators
python3 scripts/generate_connections.py

# Run specific generator
python3 scripts/generate_connections.py --name "Linguistic — Same Lemma"

# Run with book filter
python3 scripts/generate_connections.py --name "Intertextual" --books gen,exo,lev

# List available generators
python3 scripts/generate_connections.py --list

# Specialized scripts — external data ingestion:
python3 scripts/generate_self_references.py    # BoM→Isaiah, D&C↔OT cross-canon quotes
python3 scripts/generate_vulgate_connections.py # Latin Vulgate textual variants
python3 scripts/generate_jst_connections.py     # Joseph Smith Translation connections
python3 scripts/seed_symbols.py                 # Symbol reference data
python3 scripts/seed_known_patterns.py          # Human-curated patterns
python3 scripts/seed_giliadi.py                 # Giliadi 7-part structure
python3 scripts/seed_isaiah_domino.py           # 30 domino events (AJRS cycles)
python3 scripts/seed_domino_30.py               # Full domino chain
python3 scripts/seed_pickering.py               # Pickering's chiasmus data
python3 scripts/seed_barker.py                  # Barker's temple typology
python3 scripts/seed_bom_crossrefs.py           # Book of Mormon cross-references
python3 scripts/spread_pseudonyms.py            # Spread pseudonyms across canon
python3 scripts/build_lexicon.py                # Build lexicon table from gematria

# Post-processing (run after generators)
python3 scripts/precompute_guides.py            # Rebuild passage guide cache
python3 scripts/cleanup_connections.py          # Agent review & quality cleanup
python3 scripts/validate_connections.py         # Integrity checks
```

## Current Generators

| Generator | Layers | Automatic |
|-----------|--------|-----------|
| Linguistic — Same Lemma | linguistic | Yes |
| Linguistic — Same Root | linguistic | Yes |
| Linguistic — Same Morphology | linguistic | Yes |
| Linguistic — Hendiadys | linguistic | Yes |
| Structural — Chiastic Pairs | structural | Yes |
| Structural — Parallelism Detection | structural | Yes |
| Structural — Formula Markers | structural | Yes |
| Structural — Semuchin | structural | Yes |
| Structural — Acrostic Detection | structural | Yes |
| Structural — Refrain Detection | structural | Yes |
| Structural — Chiasm Detector (algorithmic) | structural | Yes |
| Intertextual — Quotation Detection | intertextual | Yes |
| Frequency — Distribution | frequency | Yes |
| Frequency — Hapax/Dislegomenon | frequency | Yes |
| Numerical — Full Gematria | numerical | Yes |
| Numerical — Ordinal & Reduced Gematria | numerical | Yes |
| Numerical — Gematria Factor | numerical | Yes |
| Numerical — Gematria Sum Relationship | numerical | Yes |
| Geographic — Location | geographic | No |
| Geographic — Subtypes (journey, wilderness, exile, etc.) | geographic | Yes |
| Chronological — Time Periods | chronological | Yes |
| Chronological — Time Markers | chronological | Yes |
| Chronological — Feast Connections | chronological | Yes |
| Chronological — Genealogical | chronological | Yes |
| Chronological — Sabbatical & Jubilee Cycles | chronological | Yes |
| Isaiah — Hebrew Keyword Discovery | linguistic | Yes |
| Isaiah — Seven Spiritual Levels | interpretive | Yes |
| Isaiah — Advanced Giliadi Techniques | structural, chronological, symbolic | Yes |
| Isaiah — Pseudonym Twin-Pair System | symbolic | Yes |
| Cross-Canon — Pseudonym Detection | symbolic | Yes |
| Cross-Canon — Chaos Motifs | linguistic | Yes |
| Experimental — All Isaiah Methods Cross-Canon | interpretive, linguistic | Yes |
| Interpretive — Tradition Connections | interpretive | No |
| Rabbinic — Kal v'Chomer (Light/Heavy) | interpretive | Yes |
| Rabbinic — Mukdam u'Meuchar (Non-Chronological) | interpretive | Yes |

## Adding a New Generator

1. Create `generators/my_generator.py` with a `run(conn, book_ids=None) -> int` function
2. Add entry to `GENERATOR_DEFS` in `generators/__init__.py`
3. Use `add_connection()` from `lib/db.py` to insert connections
4. Run via `scripts/generate_connections.py --name "My Generator"`
5. After generation, rebuild passage guides: `scripts/precompute_guides.py`

## Path Scope

- `generators/__init__.py` — registry
- `generators/*.py` — individual generators
- `scripts/generate_connections.py` — CLI runner
- `scripts/precompute_guides.py` — rebuilds materialized cache
