# Search Enhancement Plan

Goal: Apply lessons from unicity-ai's benchmarking to scriptureengine — better search quality, typo tolerance, query caching, graph-enhanced retrieval.

## Current Architecture
- FTS5 trigram (`verses_fts_trigram`) — 3-phase fallback (AND→OR→LIKE)
- Vector search via sqlite-vec (paraphrase-multilingual-MiniLM-L12-v2)
- Hybrid RRF fusion (k=60), basic vec+bm25 blend
- Hebrew/Greek: gematria table LIKE fallback
- No Qdrant, no query cache, no reranker, no graph-enhanced search

## Pre-resolved Decisions
- **No new dependencies** (unless unavoidable) — use SQLite, existing infrastructure
- **Graceful degradation** — improvements silently fall back if unavailable
- **Backward compatible** — all existing API shapes preserved
- **Incremental** — each track is independent, deployable separately

## Track A: Query Sanitization `[ ]`
Fix FTS5 crashes from special characters. Unicity found 83% of BEIR queries crashed.

### Phase A1: Fix `_sanitize_fts_query` in web/server.py `[ ]`
- Strip `?`, `/`, `(`, `)`, `+`, `-`, `.` characters that FTS5 interprets as operators
- Same fix in `lib/api/search.py`

### Phase A2: Add tests `[ ]`
- Test that `?` queries don't crash
- Test that `-` queries don't crash

## Track B: Query Cache `[ ]`
SQLite-backed TTL cache eliminates repeated searches (<10ms vs 18-118ms).

### Phase B1: Cache table + core logic `[ ]`
- Shared `query_cache` table in `lib/api/search.py`
- SHA256 key of (query, mode, limit)
- TTL default 300s, configurable

### Phase B2: Wire into search endpoints `[ ]`
- Check cache before executing search
- Store after successful search
- Invalidate on re-index

## Track C: Graph-Enhanced Search `[ ]`
Fuse knowledge graph traversal as 3rd RRF signal. Leverages scriptureengine's 1.3M+ connections at query time.

### Phase C1: Query-time graph search `[ ]`
- Extract entity candidates from query (people, places, concepts)
- Find verses connected to those entities via the connection graph
- Score by proximity + connection strength/confidence
- Return scored verse IDs with explanation paths

### Phase C2: 3-way RRF fusion `[ ]`
- Extend `_merge_results` to accept 3rd signal
- DAT-inspired alpha allocation: entity-heavy → favor graph, question → favor vector, keyword → favor BM25

## Track D: Scalar Quantization `[ ]`
Enable sqlite-vec scalar quantization for 4× memory reduction.

## Track E: Cross-Encoder Reranker `[ ]`
Optional reranker for semantic search results, graceful degradation.
