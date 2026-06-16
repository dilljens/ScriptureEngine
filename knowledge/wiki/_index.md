# Scripture Knowledge Engine — Architecture Overview

**Build**: `python3 scripts/ingest.py`  **Serve**: `./run.sh web`  **API**: `http://localhost:8000/docs`
**Database**: `data/processed/scripture.db` (218,292 connections, 41,126 passage guides, 42,054 vector embeddings)

## Quick Reference

### Key files
| Purpose | File |
|---------|------|
| HTTP API server (FastAPI) | `web/server.py` |
| MCP server (local AI, project-scoped) | `mcp_server.py` |
| Pre-computed passage guides | `scripts/precompute_guides.py` |
| Vector embeddings (semantic search) | `scripts/embed_verses.py` |
| Connection graph cleanup (AI review) | `scripts/cleanup_connections.py` |
| Database schema & operations | `lib/db.py` |
| Gematria calculator | `lib/gematria.py` |
| Connection types (10 layers) | `lib/connections/types.py` |
| PaRDeS levels | `lib/connections/pardes.py` |
| Hidden patterns (Sod engine) | `lib/sod/` |
| Anti-hallucination quality controls | `lib/controls/` |
| Connection generators (6 automated) | `generators/` |
| Project-scoped MCP config | `.opencode/opencode.jsonc` |
| External data sources | `data/raw/` (scriptures-json, morphhb, sblgnt, etc.) |

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/verses/{ref}` | Verse text + RAM-cached passage guide |
| GET | `/api/v1/verses/{ref}/connections` | Filtered by layer, quality, PaRDeS |
| GET | `/api/v1/verses/{ref}/guide` | Instant passage guide (sub-ms) |
| GET | `/api/v1/search?q=&lang=` | Cross-lingual (English + Hebrew + Greek) |
| GET | `/api/v1/semantic-search?q=` | Vector semantic search (42K embedded) |
| GET | `/api/v1/gematria?word= | ?value=` | Gematria lookup |
| GET | `/api/v1/sod` | Hidden patterns — atbash, acrostics, gematria |
| GET | `/api/v1/pardes/{ref}` | PaRDeS interpretation levels |
| POST | `/api/v1/tabs` | Create/manage UI tab state |
| GET | `/api/v1/info` | Database statistics |

### MCP Tools (10, project-scoped)
`scripture_verse`, `scripture_search`, `scripture_gematria`, `scripture_connections`,
`scripture_intertext`, `scripture_search_xlingual`, `scripture_sod`,
`scripture_passage_guide`, `scripture_pardes`, `scripture_info`

## System State
- **42,054 verses** across OT, NT, BoM, D&C, PGP
- **23,213 OT verses with Hebrew** (WLC 4.20 + morphology)
- **7,925 NT verses with Greek** (SBLGNT + isopsephy)
- **305,507 Hebrew gematria** entries
- **137,536 Greek isopsephy** entries
- **42,054 vector embeddings** (semantic search via sqlite-vec)
- **218,292 connections** across all 10 layers
- **41,126 pre-computed passage guides** (RAM-cached at startup)
- **10 connection layers** — linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic
- **4 PaRDeS levels** — P'shat (122K), Remez (44K), Drash (16K), Sod (2.5K)
- **Quality calibration** — probable (124K), suggested (61K)
- **87 entity links** — Hebrew ↔ Greek ↔ English name alignment
- **27 known chiasms** — Gileadi, Welch, and classic patterns
- **15 parallelism types** — synonymous, antithetic, synthetic, emblematic, step, numerical, merismus, rhetorical, linked-words, keyword-linking, chiasms, acrostic, inclusio, etc.
- **3 guided studies** — Torah in All Scripture, Covenants and Their Fulfillments, The Angel of the Lord
- **8 data sources integrated** — WLC, SBLGNT, LXX, STEPBible, JST, Gileadi's patterns, Barker's Temple Theology, Pickering's Daniel numbers

## Quick Commands
```bash
./run.sh info          # Database stats
./run.sh test          # Smoke tests
./run.sh web           # Start HTTP API + OpenAPI docs at /docs
./run.sh cleanup       # Connection graph cleanup
./run.sh cleanup --ai-review  # AI reviews before deprecating
./run.sh embed         # Generate vector embeddings
./run.sh verse '{"book":"isa","chapter":6,"verse":1}'
./run.sh gematria '{"word":"יהוה"}'
./run.sh layers '{"verse":"isa.6.1"}'
```

## Sources
| Source | Content | Status |
|--------|---------|--------|
| Westminster Leningrad Codex | Hebrew OT + morphology | ✅ |
| SBLGNT (morphgnt) | Greek NT + isopsephy | ✅ |
| LXX (GreekResources) | Septuagint lemma data | ✅ |
| STEPBible (TAGNT + TAHOT) | NT/OT manuscript variants | ✅ |
| JST (joseph-smith-translation) | 403 textual changes | ✅ |
| Gileadi (IsaiahExplained.com) | 70+ pseudonyms, 7-part structure, 30 domino events | ✅ |
| Margaret Barker | Temple theology — 25 interpretive connections | ✅ |
| Pickering (propheticappointments.com) | Daniel numbers, moedim timeline | ✅ |
| Ethiopian Bible (Ge'ez) | 83-book canon, text available at tau.ac.il | 📦 Deferred |

## Name Brainstorm: "Feasting Upon the Word"
Thematic direction: feasting — not skimming — on scripture. Depth over breadth. Connection over collection.
