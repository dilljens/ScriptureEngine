# Trigram FTS5: Typo-Tolerant Full-Text Search

## Goal

Replace the current `porter unicode61` FTS5 index (which requires exact word boundaries and `*` suffixes) with a **trigram tokenizer** FTS5 index that supports typo-tolerant, substring-match search across English, Hebrew, and Greek verse text. Eliminate the `LIKE '%...%'` fallback path.

## Current State

| Aspect | Current | Problem |
|--------|---------|---------|
| Tokenizer | `porter unicode61` | Requires word boundaries, no typo tolerance, `*` prefix needed |
| Hebrew search | `LIKE` on `gematria.word_hebrew` | Slow, no ranking, no substring matching |
| Greek search | `LIKE` on `gematria_greek.word_greek` | Same problems |
| Fallback | `LIKE '%q%'` on `verses.text_english` | Slow table scan, no relevance ranking |
| FTS5 data source | `verses_fts` exists but no Python code populates it | Not reproducible, unknown if in sync |
| Search endpoints | 3 different search flows (web xlingual, lib/api, semantic) | Inconsistent behavior |

## Pre-resolved Decisions

- **Approach:** Add a new `verses_fts_trigram` FTS5 table alongside the existing one (don't break the old one). Create a migration script `scripts/build_fts_index.py` to create and populate it.
- **Contents:** Single `search_text` column combining English + Hebrew + Greek text (same approach as `scripts/embed_verses.py` uses for vector embeddings). This enables single-query cross-lingual search.
- **Tokenizer:** `tokenize='trigram'` — best for typo-tolerant substring matching across all scripts.
- **Existing search code:** Update `_keyword_search` in `web/server.py`, `search_text` in `lib/api/search.py`, and the xlingual search endpoint to use the new trigram table, falling back to the current LIKE only if the trigram table doesn't exist (graceful degradation).
- **No new dependencies:** Trigram is built into SQLite FTS5.
- **Table is a build artifact:** Created by `scripts/build_fts_index.py`, not part of the core schema. Same pattern as `vec_verses` (managed by `scripts/embed_verses.py`).

## Tracks

### Track A: Database — Trigram FTS5 Table `[ ]`

**Description:** Create and populate the trigram FTS5 index.
**Scope:** ~1 file, ~60 lines

#### Phase A1: Create index script `[ ]`
- [ ] Create `scripts/build_fts_index.py`
  - Creates `verses_fts_trigram` virtual table:
    ```sql
    CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts_trigram USING fts5(
        verse_id UNINDEXED,
        book_id UNINDEXED,
        search_text,
        tokenize='trigram'
    );
    ```
  - Populates from all verses with text:
    ```sql
    INSERT INTO verses_fts_trigram (verse_id, book_id, search_text)
    SELECT v.id, v.book_id,
           CASE
               WHEN v.text_hebrew != '' AND v.text_greek != '' AND v.text_english != ''
                   THEN 'hebrew: ' || v.text_hebrew || '  greek: ' || v.text_greek || '  english: ' || v.text_english
               WHEN v.text_hebrew != '' AND v.text_english != ''
                   THEN 'hebrew: ' || v.text_hebrew || '  english: ' || v.text_english
               WHEN v.text_greek != '' AND v.text_english != ''
                   THEN 'greek: ' || v.text_greek || '  english: ' || v.text_english
               WHEN v.text_english != ''
                   THEN 'english: ' || v.text_english
               WHEN v.text_hebrew != ''
                   THEN 'hebrew: ' || v.text_hebrew
               WHEN v.text_greek != ''
                   THEN 'greek: ' || v.text_greek
           END
    FROM verses v
    WHERE v.text_english != '' OR v.text_hebrew != '' OR v.text_greek != '';
    ```
  - Supports `--reset` and `--dry-run` flags (same pattern as `embed_verses.py`)
  - Reports total indexed + elapsed time
- ✅ **Checkpoint:** `python3 scripts/build_fts_index.py` exits cleanly, reports verse count
- ⚙ **Fallback:** Run manually, not part of automated pipeline

#### Phase A2: Integrate into build pipeline `[ ]`
- [ ] Add `build_fts_index` step to `scripts/precompute_guides.py` or a dedicated make target
- [ ] Note in docs that this script should be re-run after data changes
- ✅ **Checkpoint:** FTS table exists with expected row count
- ⚙ **Fallback:** Manual invocation

---

### Track B: Search Code — Use Trigram FTS5 `[ ]`

**Description:** Update all search functions to query the trigram FTS5 table.
**Scope:** ~2 files, ~80 lines changed

#### Phase B1: Update `_keyword_search` in `web/server.py` `[ ]`
- [ ] Add a helper `_trigram_search(conn, query, limit)` function:
  ```python
  def _trigram_search(conn, query, limit):
      """Search using trigram FTS5 — typo-tolerant, substring matching."""
      # Escape FTS5 special chars, avoid trigram explosion for very short queries
      query = _sanitize_fts_query(query)
      if len(query) < 2:
          return _keyword_search_fallback(conn, query, limit)
      try:
          rows = conn.execute("""
              SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                     b.title as book_title, v.chapter, v.verse
              FROM verses_fts_trigram f
              JOIN verses v ON v.id = f.verse_id
              JOIN books b ON b.id = v.book_id
              WHERE verses_fts_trigram MATCH ?
              ORDER BY rank
              LIMIT ?
          """, (query, limit)).fetchall()
          return [_format_verse_result(r, 0.5) for r in rows]
      except Exception:
          return _keyword_search_fallback(conn, query, limit)
  ```
- [ ] Simplify the `except` path in `_keyword_search` — try trigram first, fall back to LIKE only if trigram table is missing
- [ ] Add `_sanitize_fts_query` to handle FTS5 special characters:
  - Escape `"` → `""`
  - Strip `^`, `*`, `-` operators (not needed with trigram)
  - Handle very short queries (< 2 chars → fallback to LIKE)
- ✅ **Checkpoint:** `GET /api/v1/semantic-search?q=genis` returns Genesis verses
- ⚙ **Fallback:** LIKE path still works if trigram table is absent

#### Phase B2: Update xlingual search in `web/server.py` `[ ]`
- [ ] The xlingual search endpoint (line 600+) currently has separate English/Hebrew/Greek branches
- [ ] Replace the English FTS5 branch (lines 605-671) with a single trigram search over `search_text`
- [ ] Keep the Hebrew/Greek branches for explicit language-specific searches, but note they could be merged
- ✅ **Checkpoint:** `GET /api/v1/search?q=ברית&lang=all` returns Hebrew matches
- ⚙ **Fallback:** Keep Hebrew/Greek LIKE branches as-is for now

#### Phase B3: Update `lib/api/search.py` `[ ]`
- [ ] Update `search_text()` to try trigram FTS5 before LIKE
- [ ] Update `search_xlingual()` to use trigram for the English branch
- [ ] Keep backward compatibility — fall back to LIKE if trigram table missing
- ✅ **Checkpoint:** `python3 tools/search.py '{"query": "covenant"}'` works
- ⚙ **Fallback:** LIKE fallback preserved

---

### Track C: Hebrew/Greek Integration `[ ]`

**Description:** Leverage trigram for Hebrew and Greek text search — no more separate LIKE queries on gematria tables for basic substring matching.
**Scope:** ~1 file, ~30 lines changed

#### Phase C1: Unified Hebrew search through trigram `[ ]`
- [ ] The `search_text` column already includes `hebrew: ...` prefix for verses with Hebrew text
- [ ] A trigram search for `ברית` will match `hebrew: ...ברית...` naturally
- [ ] Update `_search_hebrew` in `web/server.py` (line 1013) to try trigram first:
  ```python
  def _search_hebrew(conn, query, limit):
      # Try trigram first for typo-tolerant Hebrew search
      trigram_results = _trigram_search(conn, query, limit)
      if trigram_results:
          return trigram_results
      # Fallback: gematria LIKE
      ...
  ```
- ✅ **Checkpoint:** `GET /api/v1/semantic-search?q=ברית` finds verses with Hebrew text
- ⚙ **Fallback:** Old gematria LIKE path

#### Phase C2: Unified Greek search through trigram `[ ]`
- [ ] Same approach for `_search_greek` — try trigram first
- ✅ **Checkpoint:** `GET /api/v1/semantic-search?q=λόγος` finds Greek matches
- ⚙ **Fallback:** Old gematria_greek LIKE path

---

## Usage After Implementation

```bash
# Typo-tolerant search — works with trigram
python3 tools/search.py '{"query": "genis"}'           # → gen.1.1 (was 0 results before)
python3 tools/search.py '{"query": "covenent"}'         # → covenant verses (lower rank)
python3 tools/search.py '{"query": "brith"}'             # → covenant/ברית verses (transliteration)
python3 tools/search.py '{"query": "יהוה"}'              # → all verses with YHWH in Hebrew

# Substring matching — no * needed
python3 tools/search.py '{"query": "gene"}'              # → genesis, generations (was 0 before)

# Cross-lingual (single field search)
GET /api/v1/search?q=ברית&lang=all                       # → Hebrew matches AND English "covenant" matches
```

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `scripts/build_fts_index.py` | **New** — create & populate trigram FTS5 table | ~80 |
| `web/server.py` | Update `_keyword_search`, add `_trigram_search`, `_sanitize_fts_query` | ~50 |
| `lib/api/search.py` | Update `search_text`, `search_xlingual` to prefer trigram | ~30 |
| `docs/wiki/features/lib-core.md` or deployment notes | Add build step note | ~5 |

**Total:** ~165 lines added/changed

## Acceptance Criteria

1. `python3 scripts/build_fts_index.py` creates and populates `verses_fts_trigram` with 40K+ rows
2. Search for `"genis"` returns `gen.1.1` as top result
3. Search for `"covenent"` returns all covenant verses (ranked lower than exact matches)
4. Search for `"יהוה"` via cross-lingual endpoint returns results
5. All existing search tools (`search.py`, `semantic_search`, xlingual) still work
6. `LIKE '%...%'` fallback still works if trigram table is absent
