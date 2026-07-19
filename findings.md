# Findings: Scripture Engine — Implementation Planning

> Collected 2026-07-19 from source files: MASTER_PLAN.md, trigram-fts-plan.md,
> hebrew-enhancement-plan.md, knowledge-assessment-plan.md, rabbinic-kabbalistic-tools.md,
> llm-lexicon-plan.md, macro-analysis-plan.md, math-academy-way-reference.md,
> truth-seeking-framework.md, progress.md, SESSION.md, schedule.yaml

---

## 1. Current Project State

| Area | State |
|------|-------|
| **Connection Graph** | 1.77M connections, 11 layers, 100+ types, 53 generators |
| **Database** | SQLite, 1.2GB, WAL mode, 71+ tables |
| **Backend** | FastAPI + Uvicorn (port 8002), 146 endpoints, 12 route modules |
| **Frontend** | React 19 + Vite 6 + Tailwind 3, 56 components |
| **Go SRS** | Port 8090, FSRS-5, FIRe, 30 tests |
| **MCP** | 52 tools via JSON-RPC stdio server |
| **CI** | GitHub Actions: ruff + pytest |
| **Deploy** | nginx + Let's Encrypt + systemd, 40.160.241.74 |
| **Tests** | 38 pytest tests + 829 API smoke tests + Playwright E2E |
| **Conventions** | 0 violations (down from 129 after audit) |
| **Ruff** | 2023 style-only errors (down from 5969 after audit) |

### Complete Items
- ✅ 1.77M connections across 11 layers
- ✅ FSRS-5 (Go, Rust-verified), FIRe credit flow, palaces, hints, audio
- ✅ Hebrew: 102-node curriculum, diagnostic, quiz, verb drills, passage reader
- ✅ Study guides: full CRUD + publish/fork/export + viewer + editor
- ✅ Card system: CardQueue + CardRenderer (9 types) + interleaving
- ✅ Wiki: Wikipedia-style layout, 20+ articles
- ✅ Search: FTS5 + vector (sqlite-vec) + graph-enhanced (3-way RRF) + reranker
- ✅ Truth-seeking: null-text validation, disagreements (20 seeds), hermeneutic badges, ecumenical consensus
- ✅ Language tools: Greek transliteration, morphology parser (+417 lines), Strong's lexicon, interlinear
- ✅ JST: 8,895 diff connections, 31,262 verses
- ✅ Codebase audit: 129 convention violations fixed, Ruff 5969 → 2023
- ✅ CI pipeline: ruff + pytest on every push
- ✅ Passage-level: schema + density cluster + chiastic promoter + book coherence generators

### In Progress
| Item | Status |
|------|--------|
| Chat response quality | Active (last commit 2026-07-19) |
| Mobile sign-in | Active |
| Tool progress display | Active |
| Passage-level connections (generators) | Building — genre tagger, theme tracer |

### Remaining (~40h total)
| Phase | Effort | Components |
|-------|--------|------------|
| **Phase 5: Polish** | ~5h | ntfy.sh, sefirotic mapping, FIRe penalty flow |
| **Phase 6: Hebrew** | ~15h | 7 features: cloze, freq vocab, passage study mode, 2-way translation, daily verse, audio mode, Hebrew-only |
| **Phase 7: Assessment** | ~20h | Domain def, prerequisites, adaptive engine, item gen, IRT, FSRS, tracking, recommendations |
| **Track 0: Trigram** | ~2h | FTS5 trigram index + search integration |

---

## 2. Pre-resolved Decisions

### Plan Structure
- **Decision:** Multi-track within sequential phases (3 phases × multiple tracks each)
- **Rationale:** Phase 5 (quick wins) has no dependencies on Phase 6 (Hebrew) or Phase 7 (assessment). Phase 6 has some infrastructure dependencies on Phase 5. Phase 7 assessment is largest and builds on existing connection/data infrastructure.
- **Track 0 (Trigram):** Standalone — zero dependencies, can interleave with any phase.

### Trigram FTS5
- **Decision:** New `verses_fts_trigram` table, single `search_text` column combining all languages, `tokenize='trigram'`
- **Rationale:** Built into SQLite FTS5, zero new dependencies. Typo-tolerant substring matching across all scripts. Same pattern as `embed_verses.py` for `vec_verses` (build artifact, managed by script).
- **Key design:** Keep existing `verses_fts` for backward compatibility. Trigram is preferred path; LIKE is always fallback.

### Assessment Engine
- **Decision:** API-first, anonymous-first (localStorage), auto-generated items
- **Rationale:** Avoid auth dependency for initial build. React frontend can consume later. Auto-generation from connections is faster and adequate for low-stakes practice.
- **Model:** BKT + KST hybrid — BKT for per-item mastery, KST for prerequisite structure and outer fringe computation.
- **IRT parameters:** Assigned from connection quality score (higher quality = lower difficulty). Online calibration from response data.

### Hebrew Features
- **Decision:** No new backend endpoints where possible. CardRenderer/CardQueue absorb most features.
- **Rationale:** Existing card infrastructure (9 types already built) minimizes new code. Only passage study mode needs a substantial new component.
- **Passage study mode:** Extend existing HebrewPassageReader rather than building from scratch. WordPopup.jsx already exists and can be extended with frequency data.

### Sefirotic Mapping
- **Decision:** Keyword-based algorithmic seeding first, then agent refinement
- **Rationale:** Fast to build the seed table (~100 lines). Agent refinement in later sessions can improve accuracy. Same pattern as existing agent-connection workflow.

### FIRe Penalty Flow
- **Decision:** Penalty flows from simpler → more complex (failing Gen 1:1 penalizes John 1:1, not reverse)
- **Rationale:** Math Academy Way reference (Ch 29) makes clear that failing a prerequisite should penalize the downstream topic. Our existing FIRe credit flow already handles the positive direction; penalty is the mirror.

### Entity Links Expansion
- **Decision:** Algorithmic extraction from verse text using name lists + pattern matching
- **Rationale:** 559 entities is sparse for 70K+ verses. Automated extraction reaches 2,000+ quickly. Pattern: named entity recognition via proper noun detection + lexicon cross-reference.

---

## 3. Architecture Notes

### Track 0 — Trigram FTS5
```
Flow: query → _sanitize_fts_query() → verses_fts_trigram MATCH ?
       ↓ on exception or <2 chars
       _keyword_search_fallback() (LIKE)
```

Build script pattern:
- `scripts/build_fts_index.py` same pattern as `scripts/embed_verses.py`
- Supports `--reset` and `--dry-run` flags
- Prints elapsed time + row count

### Phase 5 — Quick Wins

**ntfy.sh:**
```python
# In health check failure handler
import os
import requests
ntfy_topic = os.environ.get("NTFY_TOPIC", "")
ntfy_server = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
if ntfy_topic:
    requests.post(f"{ntfy_server}/{ntfy_topic}",
                  json={"title": "Scripture Engine Health Failure", ...})
```

**Sefirot table schema:**
```sql
CREATE TABLE sefirah_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sefirah TEXT NOT NULL,  -- keter, chokhmah, binah, chesed, gevurah, tiferet, netzach, hod, yesod, malkhut
    keyword TEXT NOT NULL,
    language TEXT DEFAULT 'hebrew',
    UNIQUE(sefirah, keyword)
);
```

**FIRe penalty flow:**
```python
# When rating < 3 (Again/Hard)
for each connected verse:
    penalty = conn_strength * (1.0 if rating == 1 else 0.3)
    # Only penalize if connected verse is MORE complex (higher stability/difficulty)
    if connected_stability > current_stability:
        new_stability = stability / (1 + penalty)
        fi_re_credit = max(0, fi_re_credit - penalty)
```

### Phase 6 — Hebrew Features

**Passage study mode architecture:**
```
HebrewLearnView
  └── PassageReader.jsx
        ├── Verse text rendered word-by-word
        ├── WordPopup.jsx (existing, extended)
        │     └── Lemma, Strong's, root, frequency, "Add cards" button
        └── CardQueue (generates vocab cards from clicked words)
```

**Daily verse endpoint:**
```
GET /api/v1/hebrew/verse-of-day → {
  ref: "gen.1.1",
  hebrew: "...",
  transliteration: "...",
  words: [{word, lemma, strongs, gloss, root, frequency}],
  english: "..."
}
```

**Audio review:**
- New `AudioReviewSession.jsx` — minimal visual, wave/play/pause UI
- Reuses existing TTS infrastructure
- CardQueue integration with FSRS-5 tracking
- Audio controls: play Hebrew → think → play answer

### Phase 7 — Assessment Engine

**Knowledge item schema:**
```sql
CREATE TABLE knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    connection_type TEXT NOT NULL,
    layer TEXT NOT NULL,
    pardes_level TEXT,                -- pshat, remez, drash, sod
    quality_score REAL,               -- from calibration
    item_text TEXT,                   -- Natural language: "The connection between Gen 1:1 and John 1:1"
    UNIQUE(source_verse, target_verse, connection_type)
);
```

**Prerequisite graph (DAG) rules:**
```
Layer hierarchy (P'shat → Remez → Drash → Sod):
  linguistic/same_lemma → linguistic/same_root → linguistic/same_morphology
  numerical/gematria_sum → numerical/gematria_factor
  intertextual/phrase_match → intertextual/direct_quotation → intertextual/allusion
  structural/parallelism → structural/chiasm
  P'shat items → Remez items → Drash items → Sod items
```

**BLIM model:**
```
P(correct) = (1 - slip) * knowledge + guess * (1 - knowledge)
State update: P(knowledge | response) via Bayes' rule
Item selection: argmax information_gain(item, current_state)
Termination: max 20 items OR entropy < 0.1
```

---

## 4. Open Questions → Resolved

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| Q: Assessment scope — all 10 layers or subset? | Start with all layers, filter to >=3★ connections | Existing quality filtering handles this; no need to scope down |
| Q: User identity for progress tracking? | Anonymous-first (localStorage) | Avoids auth dependency; optional auth migration later |
| Q: Item generation — auto or hand-curated? | Auto-generated from connections | 1,000+ items in hours vs. weeks; adequate for low-stakes practice |
| Q: Minimum connection quality for items? | >=3★ (from 5-signal calibration) | 3★ = "probable" balance of quality vs. quantity |
| Q: PaRDeS depth — all four from start? | Yes, all four levels | Classification already exists in connection metadata |
| Q: Macro-analysis features in scope? | Deferred to after Phase 7 | Genre clusters, thematic trajectories are ~2,700 lines; ~40h backlog doesn't include them |
| Q: Truth-seeking remaining work? | Already substantially complete | B1-B4 all ✅; neural chiastic detection and JS discourses are separate research tracks |
| Q: Multi-mode FIRe — what's left? | Penalty flow only | Credit flow, repetition compression, palace-guided, decay model, macro-interleaving, student-topic calibration all ✅ |
| Q: API test coverage? | Deferred to after Phase 7 | 8h effort, not blocking feature work; existing 829 smoke tests + 38 pytest tests provide baseline |

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Assessment engine too complex | Medium | High (20h investment) | Start with simple item selection; BLIM can be simplified to additive model |
| Hebrew passage study mode scope creep | Medium | Medium | Use existing components; limit to MVP: word-by-word + popup |
| Entity extraction yields noise | Medium | Low | Manual review of first batch; confidence threshold |
| Trigram FTS5 performance on 40K+ rows | Low | Medium | SQLite FTS5 trigram handles millions; benchmark at 40K |
| FIRe penalty flow direction wrong | Low | Medium | Code review + verify direction (simpler→more complex) |
| Sefirot mapping too vague | Medium | Low | Keyword seeding is intentionally broad; agent refinement improves |
