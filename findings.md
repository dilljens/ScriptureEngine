# Findings: Phase 2 — Knowledge Consolidation

## Pre-resolved Decisions
- **Sefaria data:** Bulk export CSV from GCS, not live API — faster, no rate limits
- **Assessment:** New `/api/v1/quiz` endpoint, not modifying the old BLIM engine
- **Hebrew attestations:** Already in DB (152 across 33 nodes), just need frontend
- **Tradition labels:** Already in graph API (tradition/hermeneutic fields), just need frontend display

## Existing Assets
- 200 deep questions in assessment_items with tier labels
- 14 hub notes with 88 steps in DB
- 41 thematic clusters with 366 member references
- 1.4M connections with tradition labels
- 152 Hebrew attestations
- LLM grading endpoint (`POST /api/v1/assess/grade`)
- Provenance endpoint (`GET /api/v1/provenance/{verse_id}`)
- 9 tradition labels defined

## Sefaria Architecture Note
- Sefaria Export CSVs from GCS bucket `gs://sefaria-export/links/`
- CSV format: `refs[0], refs[1], type, auto, generated_by`
- Link types: commentary, quotation, reference, midrash, ein_mishpat, mesorat_hasash
- Need to handle commentary refs (they include commentator name — strip it)
- Book name mapping is the key challenge

## Hebrew Node Traditions
- `tiberian` — Standard Tiberian Masoretic (most letter/vowel nodes)
- `standard` — Standard Biblical Hebrew grammar (verb binyanim, noun patterns)
- `multiple` — Multiple tradition sources
