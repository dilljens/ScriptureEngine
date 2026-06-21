# Agent-Driven Connection Expansion

## Method

**The agent reads the text directly.** No API, no key, no cost. The agent reads candidate verse pairs from the database, uses its own reasoning to judge whether a genuine connection exists, writes judgment JSON files, and applies them to the database.

### Workflow per round

```
1. Query DB for candidates     ─→ SQL query pre-filters candidates
2. Read verse texts            ─→ examine source + target texts with Read tool
3. Use reasoning to judge      ─→ is this connection real? why?
4. Write judgment JSON file    ─→ data/agent_connections/{type}_judgments.json
5. Apply to DB                 ─→ INSERT INTO connections (discovered_by='ai')
6. Verify counts               ─→ check DB counts
```

Every connection includes a `reasoning` field in metadata — this is the product: users see why the connection exists.

### Candidate Pre-filtering

For each type, algorithmic pre-filtering reduces the candidate space before the agent's judgment:

| Type | Pre-filter |
|------|-----------|
| `prophetic_fulfillment` | NT quotes/references to OT prophecies |
| `type_antitype` | Shared entities + thematic keyword overlap |
| `wordplay` | Hebrew homophones or 1-consonant differences within verse |
| `nomen_est_omen` | Verses containing name origins, renamings, blessings |
| `modified_quotation` | Direct quotations where source ≠ target text |
| `midrashic_connection` | NT passages that interpretively reuse OT |
| `summarized` | OT passage + NT passage, high semantic but low lexical overlap |
| `cognate` | Hebrew/Aramaic lemmas with known cognate relationships |
| `semantic_domain` | Lemmas grouped by root, co-occurrence, or conceptual domain |
| `apocalyptic_time` | Time expressions (1260 days, 42 months, etc.) in Daniel/Revelation |
| `prophetic_quote` | Modern prophetic statements citing scripture |
| `lectio_divina` | Classic patristic/monastic passage pairings |

### Quality

| confidence | quality_level | Meaning |
|-----------|--------------|---------|
| > 0.8 | verified | Almost certain — well-known, textually explicit |
| > 0.6 | strong | Highly likely — clear thematic or textual connection |
| > 0.4 | probable | Reasonable — connection has scholarly support |
| ≤ 0.4 | speculative | Possible but uncertain |

---

## Current State (17 Jun 2026)

- **Phase 0** (algorithmic quick wins) — ✅ Done
- **Phase 1** (lib/llm/ architecture) — ❌ Not needed. No API. Agent reads directly.
- **Phases 2-5** (13 connection types) — ✅ First pass done (376 agent judgments)
- **Vulgate ingestion** — ✅ Done (31,077 verses, 33,082 connections)
- **Passage guides** — ✅ Rebuilt (~41K guides)
- **Total connections** — **1,028,133**
- **Types populated** — **88/93** (5 types have 0 connections)
- **Generators registered** — **35** (33 auto + 2 manual)
- **Kal v'Chomer** — ✅ Algorithmic (43 connections)
- **Semantic domains** — ✅ 15 seeded algorithmically (372 members)
- **Mukdam u'Meuchar** — ✅ Algorithmic (9 cases)
- **Wiki articles** — ✅ 20 articles with API endpoints
- **Thematic connections** — ✅ 50+ across 3 themes (covenant, exodus, temple)
- **Connection explanations** — ✅ 360+ with reasoning
- **Lexicon definitions** — ✅ 411 content words defined

### Remaining Expansion Rounds

| Round | Types | Goal |
|-------|-------|------|
| **1** | 11 types | ✅ All complete (566 agent connections) |
| **2** | Cross-canon typology | ✅ DONE (75 type_antitype pairs) |
| **3** | Connection explanations | ⚠️ PARTIAL (360/500+ explanations) |
| **4** | Lexicon definitions | ⚠️ PARTIAL (411 content lemmas defined) |
| **5** | Thematic connections | ✅ 50+ created (covenant, exodus, temple) |
| **6** | Wiki articles | ✅ 20 articles + 3 API endpoints |
| **7** | Wrong worship connections | ✅ 15 connections (golden calf, strange fire, etc.) |

## New: Multi-Signal Rating System

Every connection is now rated on multiple independent axes. See `lib/controls/calibration.py`.

### Input Signals

- **discovery_method**: Where the connection came from — `text`, `tsk`, `llm`, `algorithm`
- **connection_type**: What kind of connection — `direct_quotation`, `same_gematria`, etc.
- **has_reasoning**: Whether human-readable explanation text exists
- **confidence**: The existing 0.0–1.0 statistical confidence
- **confirmation_count**: How many users have confirmed this connection

### Output Tiers (Star Ratings)

Every connection gets a 1-5 star rating:

| Stars | Tier | Threshold | Meaning |
|-------|------|-----------|---------|
| ★★★★★ | Verified / Text-Explicit | ≥0.90 | The text itself says so |
| ★★★★☆ | Well-Established | ≥0.75 | Strong scholarly or human consensus |
| ★★★☆☆ | Probable | ≥0.55 | Reasonable connection with support |
| ★★☆☆☆ | Suggested | ≥0.30 | Algorithmic, not verified |
| ★☆☆☆☆ | Pattern Only | <0.30 | Statistical artifact |

### API Filtering

```
GET /api/v1/verses/{ref}/connections
  ?discovered_by=tsk       # only historical cross-references
  &min_confidence=0.7       # only confident connections
  &min_quality=strong       # only well-established ones
  &show_signals=true         # include full signal breakdown
```

### User Feedback

```
POST /api/v1/connections/feedback
  {"connection_id": 123, "action": "confirm"}
```

Users can confirm, reject, or mark a connection unclear. This updates confirmation_count, which feeds back into the rating system over time.

---

## Implementation Order

```
Round 1a ──→ Expand prophetic_fulfillment  (9 → 50+)
Round 1b ──→ Expand midrashic_connection    (8 → 30+)
Round 1c ──→ Expand summarized              (8 → 30+)
Round 1d ──→ Expand apocalyptic_time        (8 → 20+)
Round 1e ──→ Expand nomen_est_omen          (10 → 30+)
Round 1f ──→ Expand modified_quotation      (15 → 40+)
Round 1g ──→ Expand lectio_divina           (5 → 15+)
Round 2  ──→ Cross-canon typology           (28 → 60+)
Round 3  ──→ Connection explanations        (~500 existing connections)
Round 4  ──→ Lexicon definitions            (11,515 lemmas)
Round 5  ──→ Thematic connections           (10 themes → 50+ connections each)
Round 6  ──→ Wiki articles                  (87 entities + 10+ concepts)
```
