"""
Shared tool: cross-lingual search.

Used by MCP (scripture_search, scripture_search_xlingual),
HTTP API (/api/v1/search),
and CLI (tools/search.py, tools/search_xlingual.py).
"""

from lib.hebrew_util import clean_hebrew as ch
from lib.hebrew_util import rtl_mark, transliterate


def search_text(conn, query, book=None, works=None, limit=25):
    """Search verses by English text.

    Args:
        query: Search term
        book: Optional book ID filter (e.g., 'gen', 'isa', '1QS', 'dc' for D&C)
        works: Optional list of work IDs to filter (e.g., ['ot','nt','dss','bom','dc','pgp','apoc','pseu','expanded'])
        limit: Max results (default 25, max 50)

    Returns: dict with query, count, results list (each with verse, text, book, book_id, work_id)
    """
    sql = """
        SELECT v.id, v.book_id, v.text_english, b.title, b.work_id
        FROM verses v
        JOIN books b ON b.id = v.book_id
        WHERE v.text_english LIKE ?
    """
    params = [f"%{query}%"]

    if book:
        if book == "dc":
            sql += " AND (v.book_id LIKE 'dc%' OR b.work_id = 'dc')"
        else:
            sql += " AND v.book_id = ?"
            params.append(book)

    if works:
        placeholders = ",".join("?" for _ in works)
        sql += f" AND b.work_id IN ({placeholders})"
        params.extend(works)

    limit = min(limit, 50)
    sql += " ORDER BY b.work_id, v.book_id, v.chapter, v.verse LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return {
        "query": query,
        "count": len(rows),
        "results": [
            {
                "verse": r["id"],
                "text": r["text_english"][:200] if r["text_english"] else "",
                "book": r["title"],
                "book_id": r["book_id"],
                "work_id": r["work_id"],
            }
            for r in rows
        ],
    }


def search_xlingual(conn, query, language="all"):
    """Search across English, Hebrew, and Greek simultaneously.

    Args:
        query: Word to search for
        language: 'all', 'english', 'hebrew', or 'greek'

    Returns: dict with query, total, results list (each with language tag)
    """
    results = []
    limit = 20

    if language in ("all", "english"):
        rows = conn.execute(
            "SELECT id, text_english FROM verses WHERE text_english LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        results.extend(
            {"verse": r["id"], "text": r["text_english"][:120], "language": "english"}
            for r in rows
        )

    if language in ("all", "hebrew"):
        rows = conn.execute(
            """
            SELECT v.id, v.text_hebrew, v.text_english
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            WHERE g.word_hebrew LIKE ? LIMIT ?
        """,
            (f"%{query}%", limit),
        ).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                raw_heb = r["text_hebrew"] or ""
                heb_disp = None
                if raw_heb:
                    ct = ch(raw_heb)
                    heb_disp = {"text": rtl_mark(ct), "transliteration": transliterate(raw_heb)}
                results.append({
                    "verse": r["id"],
                    "text": raw_heb[:120],
                    "english": r["text_english"][:60],
                    "language": "hebrew",
                    "hebrew_display": heb_disp,
                })

    if language in ("all", "greek"):
        rows = conn.execute(
            """
            SELECT DISTINCT v.id, v.text_greek, v.text_english
            FROM gematria_greek g
            JOIN verses v ON v.id = g.verse_id
            WHERE g.word_greek LIKE ? OR g.lemma LIKE ? LIMIT ?
        """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append({
                    "verse": r["id"],
                    "text": (r["text_greek"] or "")[:120],
                    "english": r["text_english"][:60],
                    "language": "greek",
                })

    return {"query": query, "total": len(results), "results": results}


def semantic_search_text(conn, query, limit=20, mode="hybrid"):
    """Hybrid semantic search using transformer embeddings + BM25 RRF fusion.

    Requires pre-computed vectors from:
        .venv/bin/python3 scripts/embed_verses.py

    Args:
        query: Search query (auto-classified: verse ref, Hebrew, Greek, or natural language)
        limit: Max results
        mode: 'hybrid' (RRF fusion), 'vector' (pure semantic), 'keyword' (pure BM25)

    Returns: dict with query, query_type, mode, total, results
    """
    try:
        from web.server import _classify_query, _vector_search, _keyword_search, _merge_results, _search_hebrew, _search_greek
        from pathlib import Path
        import re

        qtype = _classify_query(query)
        results = []

        if qtype == "verse_ref":
            try:
                parts = query.replace(":", ".").split()
                if len(parts) == 1 and parts[0].count(".") >= 2:
                    b, ch, vs = parts[0].split(".")[:3]
                    from lib.db import resolve_verse_id
                    vid, _ = resolve_verse_id(conn, b, int(ch), int(vs))
                    if vid:
                        v = conn.execute("""
                            SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                                   b.title as book_title, v.chapter, v.verse
                            FROM verses v JOIN books b ON b.id = v.book_id WHERE v.id = ?
                        """, (vid,)).fetchone()
                        if v:
                            results.append({
                                "verse": vid,
                                "reference": f"{v['book_title']} {v['chapter']}:{v['verse']}",
                                "text": (v["text_english"] or "")[:300],
                                "text_hebrew": (v["text_hebrew"] or "")[:150],
                                "text_greek": (v["text_greek"] or "")[:150],
                                "similarity": 1.0,
                            })
            except Exception:
                pass

        if qtype in ("hebrew_word",):
            heb_results = _search_hebrew(conn, query, limit)

        if qtype in ("greek_word",):
            gr_results = _search_greek(conn, query, limit)

        if qtype in ("natural", "hebrew_word", "greek_word") or not results:
            try:
                from fastembed import TextEmbedding
                model = TextEmbedding(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2",
                    max_length=512,
                    cache_dir=str(Path(__file__).resolve().parent.parent.parent / ".cache" / "fastembed"),
                )
                vec_results = _vector_search(conn, model, query, limit, mode)
                results = _merge_results(results, vec_results, mode)
            except Exception:
                kw_results = _keyword_search(conn, query, limit)
                results = _merge_results(results, kw_results, "keyword")

        return {
            "query": query,
            "query_type": qtype,
            "mode": mode,
            "total": len(results),
            "results": results[:limit],
        }
    except ImportError:
        # Fallback: plain text search
        return search_text(conn, query, limit=limit)
    except Exception as e:
        return {"query": query, "error": str(e), "total": 0, "results": []}
