"""Search backend helpers — extracted from web/server.py to break the
lib/api/search.py → web/server → web/routes/admin → lib/api/search.py
import cycle. These are pure search primitives; both web/server.py routes
and lib/api/search.py tools consume them from here.
"""

import json
import logging
import re
import sqlite3
import struct
from pathlib import Path

log = logging.getLogger(__name__)

_EMBED_MODEL = None

def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                max_length=512,
                cache_dir=str(Path.home() / ".cache" / "fastembed"),
            )
        except Exception as e:
            import logging
            logging.warning(f"Failed to load embedding model: {e}")
            return None
    return _EMBED_MODEL


def _classify_query(q):
    """Classify a search query to route to the best backend."""
    qs = q.strip()

    # Verse reference: gen.1.1, Genesis 1:1
    if re.match(r'^[a-z]{2,6}\.\d+\.\d+$', qs, re.IGNORECASE):
        return "verse_ref"
    if re.match(r'^[A-Za-z]+\s+\d+:\d+$', qs):
        return "verse_ref"

    # Hebrew word (contains Hebrew Unicode)
    if re.search(r'[\u0590-\u05FF]', qs):
        return "hebrew_word"

    # Greek word
    if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', qs):
        return "greek_word"

    # Exact phrase query
    if qs.startswith('"') and qs.endswith('"'):
        return "exact_phrase"

    # Default: natural language
    return "natural"


def _vector_search(conn, model, query, limit, mode):
    """Search using transformer embeddings."""
    import struct
    import_array = "query"
    if mode in ("hybrid", "keyword"):
        batch_size_k = limit
    else:
        batch_size_k = limit

    # Embed query directly (paraphrase model doesn't need 'query:' prefix like E5)
    query_text = query
    query_vec = list(model.embed([query_text]))[0]
    vec_bytes = struct.pack(f'{len(query_vec)}f', *query_vec)

    rows = conn.execute("""
        SELECT verse_id, distance FROM vec_verses
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (vec_bytes, batch_size_k * 2)).fetchall()

    results = []
    for r in rows:
        v = conn.execute("""
            SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                   b.title as book_title, v.chapter, v.verse
            FROM verses v JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (r["verse_id"],)).fetchone()
        if v:
            score = 1.0 - r["distance"]
            if score > 0.15:  # Relevance threshold
                r2 = _format_verse_result(v, round(score, 4))
                r2["_score_vec"] = score
                r2["_score_bm25"] = 0.0
                results.append(r2)

    return results


def _sanitize_fts_query(query):
    """Sanitize a query string for FTS5 trigram search.

    Trigrams handle substring matching natively, so we don't need
    the `*` prefix wildcards or special operators that the porter
    tokenizer required.

    FTS5 interprets these characters as operators or syntax:
      ? - / ( ) "  * ^ ~ + .
    Unicity benchmarks found 83% of BEIR queries crashed FTS5
    because of `?` at end of questions — strip them all.
    """
    query = query.replace('"', '""')
    # Strip FTS5 special characters that cause syntax errors
    for c in '?/()*^~+':
        query = query.replace(c, ' ')
    # Hyphen: FTS5 NOT operator — replace standalone hyphens with space
    query = query.replace(' - ', '   ')
    # Dot: FTS5 column reference separator
    query = query.replace('.', ' ')
    import re
    query = re.sub(r'\s+', ' ', query)
    return query.strip()


def _ngrams(text, n=3):
    """Generate n-gram tokens from text."""
    text = text.strip()
    if len(text) < n:
        return [text] if text else []
    return [text[i:i+n] for i in range(len(text) - n + 1)]


def _trigram_search(conn, query, limit):
    """Search using trigram FTS5 — substring matching, cross-lingual, typo-tolerant.

    Strategy:
      1. AND query — matches ALL trigrams (best ranking for exact substrings)
      2. OR query — matches ANY trigram (typo-tolerant fallback)
      3. Empty — caller falls back to LIKE

    The trigram tokenizer indexes every 3-char substring, so a typo like
    'genis' still shares some trigrams with 'genesis' ('gen'), and the
    BM25 rank pushes the best match to the top.
    """
    if len(query) < 2:
        return []

    sanitized = _sanitize_fts_query(query)

    # 1. Try AND query first (exact trigram overlap — best ranking)
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
        """, (sanitized, limit)).fetchall()
        if rows:
            return [_format_verse_result(v, 0.5) for v in rows]
    except Exception:
        log.warning("silent_exception", exc_info=True)
        pass

    # 2. Try OR query (typo-tolerant — match any trigram)
    ngrams = _ngrams(sanitized, 3)
    if len(ngrams) >= 2:
        try:
            or_query = " OR ".join(f'"{g}"' for g in ngrams if len(g) == 3)
            if or_query:
                rows = conn.execute("""
                    SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                           b.title as book_title, v.chapter, v.verse
                    FROM verses_fts_trigram f
                    JOIN verses v ON v.id = f.verse_id
                    JOIN books b ON b.id = v.book_id
                    WHERE verses_fts_trigram MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (or_query, limit)).fetchall()
                if rows:
                    return [_format_verse_result(v, 0.4) for v in rows]
        except Exception:
            log.warning("silent_exception", exc_info=True)
            pass

    return []


def _keyword_search(conn, query, limit):
    """Search using trigram FTS5 + LIKE fallback for typo tolerance."""
    # 1. Try trigram FTS5 first (substring matching, BM25 ranked)
    results = _trigram_search(conn, query, limit)
    if results:
        for r in results:
            r["_score_vec"] = 0.0
            r["_score_bm25"] = 0.5
        return results

    # 2. Fallback to LIKE for typo tolerance and very short queries
    try:
        rows = conn.execute("""
            SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                   b.title as book_title, v.chapter, v.verse
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.text_english LIKE ?
            LIMIT ?
        """, (f"%{query}%", limit)).fetchall()
    except Exception:
        return []

    results = []
    for v in rows:
        r = _format_verse_result(v, 0.5)
        r["_score_vec"] = 0.0
        r["_score_bm25"] = 0.5
        results.append(r)
    return results


def _search_hebrew(conn, query, limit):
    """Search for a Hebrew word — trigram first, then gematria table for gematria data."""
    # 1. Try trigram FTS5 first (works for any Hebrew substring)
    trigram_hits = _trigram_search(conn, query, limit)
    if trigram_hits:
        return trigram_hits

    # 2. Fallback: search gematria table (niqqud-stripped matching, word-level)
    cons = "".join(c for c in query if '\u05D0' <= c <= '\u05EA' or '\u05EF' <= c <= '\u05F2')
    like = f"%{cons}%" if cons else f"%{query}%"

    rows = conn.execute("""
        SELECT DISTINCT v.id, v.text_english, v.text_hebrew, v.text_greek,
               b.title as book_title, v.chapter, v.verse,
               g.value_standard, g.word_hebrew
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.word_hebrew LIKE ?
        LIMIT ?
    """, (like, limit)).fetchall()

    results = []
    for v in rows:
        r = _format_verse_result(v, 0.8)
        r["gematria"] = v["value_standard"]
        r["word_hebrew"] = v["word_hebrew"]
        results.append(r)
    return results


def _search_greek(conn, query, limit):
    """Search for a Greek word — trigram first, then gematria_greek table."""
    # 1. Try trigram FTS5 first (works for any Greek substring)
    trigram_hits = _trigram_search(conn, query, limit)
    if trigram_hits:
        return trigram_hits

    # 2. Fallback: search gematria_greek table (word-level with gematria data)
    rows = conn.execute("""
        SELECT DISTINCT v.id, v.text_english, v.text_hebrew, v.text_greek,
               b.title as book_title, v.chapter, v.verse,
               g.value_standard as gematria, g.word_greek
        FROM gematria_greek g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.word_greek LIKE ?
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()

    results = []
    for v in rows:
        r = _format_verse_result(v, 0.8)
        r["gematria"] = v["gematria"]
        r["word_greek"] = v["word_greek"]
        results.append(r)
    return results


def _format_verse_result(v, score):
    """Format a verse result dict."""
    from lib.api.refs import format_reference
    return {
        "verse": v["id"],
        "reference": format_reference(v["book_title"], v["id"], v["chapter"], v["verse"]),
        "text": (v["text_english"] or "")[:300],
        "text_hebrew": (v["text_hebrew"] or "")[:150],
        "text_greek": (v["text_greek"] or "")[:150],
        "similarity": score,
    }


def _get_dat_alphas(query: str, entity_ratio: float = 0.0) -> tuple[float, float, float]:
    """Compute query-adaptive 3D alpha weights for hybrid search fusion.

    Uses DAT (Dynamic Alpha Tuning, arXiv 2503.23013) heuristics:
    - Long queries → favor semantic (vector)
    - Question structure → favor semantic
    - Entity mentions → favor graph
    - Hebrew/Greek Unicode → favor exact BM25
    - Verse reference → favor BM25 + graph

    Returns (alpha_vec, alpha_bm25, alpha_graph) summing to 1.0.
    """
    alpha_vec, alpha_bm25, alpha_graph = 0.40, 0.45, 0.15
    q = query.strip()

    # Length signal: long queries are more semantic
    words = q.split()
    if len(words) > 5:
        alpha_vec += 0.10
        alpha_bm25 -= 0.05

    # Question signal
    if q.lower().startswith(("what", "how", "why", "when", "where", "which", "who", "is", "are", "can", "does", "did", "was")):
        alpha_vec += 0.10
        alpha_bm25 -= 0.05

    # Entity mention signal
    if entity_ratio > 0.3:
        alpha_graph += 0.10
        alpha_bm25 -= 0.05
    elif entity_ratio > 0.15:
        alpha_graph += 0.05
        alpha_bm25 -= 0.03

    # Hebrew/Greek Unicode → exact-match heavy
    if any(ord(c) > 0x05D0 for c in q):
        alpha_bm25 += 0.20
        alpha_vec -= 0.10

    # Verse reference pattern (book.chapter.verse or chapter:verse)
    if re.search(r'\b[a-z]{2,5}\.\d+\.\d+\b|\b\d+:\d+\b', q):
        alpha_bm25 += 0.15
        alpha_graph += 0.10
        alpha_vec -= 0.10

    # Short query (≤3 words) → favor BM25
    if len(words) <= 3:
        alpha_bm25 += 0.05
        alpha_graph -= 0.03

    # Normalize to sum = 1.0
    total = alpha_vec + alpha_bm25 + alpha_graph
    return (alpha_vec / total, alpha_bm25 / total, alpha_graph / total)


def _merge_results(list_a, list_b, mode, list_c=None, query=""):
    """Merge result lists using RRF (Reciprocal Rank Fusion).

    Supports 2-way (vector + BM25) and 3-way (vector + BM25 + graph)
    fusion. Uses DAT 3D alphas for query-adaptive weighting.

    Args:
        list_a: Primary results (BM25/keyword).
        list_b: Secondary results (vector/semantic).
        mode: 'vector', 'keyword', or 'hybrid'.
        list_c: Optional 3rd signal (graph-search results).
        query: Original search query (for DAT alphas).
    """
    if mode == "vector":
        return list_b
    if mode == "keyword":
        return list_a if list_a else list_b

    # Hybrid RRF merge
    K = 60

    # Compute DAT 3D alphas
    has_graph_data = list_c is not None and len(list_c) > 0
    entity_ratio = 0.0
    if has_graph_data:
        entity_count = sum(1 for r in list_c if r.get("entity_match", False))
        total_graph = len(list_c)
        entity_ratio = entity_count / max(total_graph, 1)

    alpha_vec, alpha_bm25, alpha_graph = _get_dat_alphas(query, entity_ratio)

    # Graph is only used when data exists
    if not has_graph_data:
        alpha_graph = 0.0
        # Redistribute graph weight to vec + bm25 proportionally
        total = alpha_vec + alpha_bm25
        alpha_vec /= total
        alpha_bm25 /= total

    seen = {}
    all_lists = [list_a, list_b]
    if has_graph_data:
        all_lists.append(list_c)
    alphas = [alpha_bm25, alpha_vec]
    if has_graph_data:
        alphas.append(alpha_graph)

    for lst, alpha in zip(all_lists, alphas):
        for rank, r in enumerate(lst):
            vid = r["verse"]
            if vid not in seen:
                seen[vid] = {**r, "_rrf_score": 0.0, "_ranks": []}
            seen[vid]["_rrf_score"] += alpha * (1.0 / (K + rank))
            seen[vid]["_ranks"].append(rank + 1)
            # Preserve graph explanation if present
            if "explanation" in r:
                seen[vid]["graph_explanation"] = r["explanation"]

    # Sort by RRF score descending
    sorted_results = sorted(seen.values(), key=lambda x: -x["_rrf_score"])
    # Clean up internal fields
    for r in sorted_results:
        r.pop("_ranks", None)
        r.pop("_score_vec", None)
        r.pop("_score_bm25", None)
        # Keep _rrf_score as similarity for sorting
        r["similarity"] = round(r.pop("_rrf_score", 0), 4)
    return sorted_results


