"""
Shared tool: cross-lingual search.

Used by MCP (scripture_search, scripture_search_xlingual),
HTTP API (/api/v1/search),
and CLI (tools/search.py, tools/search_xlingual.py).
"""

from lib.hebrew_util import clean_hebrew as ch
from lib.hebrew_util import rtl_mark, transliterate


def _sanitize_fts_query(query):
    """Sanitize a query string for FTS5 trigram search.

    FTS5 interprets these characters as operators or syntax:
      ? - / ( ) "  * ^ ~ + .
    Strip them to prevent FTS5 syntax errors (unicity found 83% of
    queries crashed because of `?` at end of questions).
    """
    query = query.replace('"', '""')
    for c in '?/()*^~+':
        query = query.replace(c, ' ')
    # Hyphen: FTS5 NOT operator
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


def _query_words(query):
    """Extract lowercase word tokens usable for FTS word-level matching.

    Trigram-tokenized FTS can only match substrings of 3+ characters, so
    shorter words are dropped (they carry no indexable trigrams).
    """
    import re
    words = re.findall(r"[a-z][a-z']{2,}", query.lower())
    seen, out = set(), []
    for w in words:
        w = w.strip("'")
        if len(w) >= 3 and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:6]  # cap — more terms is a natural-language question, not a search


def _fuzzy_score(text, qgrams, query_len):
    """Word-level similarity between a verse and a (possibly mistyped) query.

    For each real word in the verse, compute trigram overlap with the query;
    score = best word similarity, tie-broken by how many words come close.
    Word-level scoring ignores incidental gram matches scattered across
    function words ('seven'/'whenever' vs 'covenent').
    """
    import re
    if not text:
        return 0.0, 0
    words = set(re.findall(r"[a-z]+", text[:2000].lower()))
    best, near = 0.0, 0
    for w in words:
        if abs(len(w) - query_len) > 4:
            continue  # cheap length prune — typos stay near the target length
        wg = {w[i:i + 3] for i in range(len(w) - 2)}
        if not wg:
            continue
        sim = len(wg & qgrams) / len(qgrams)
        if sim > best:
            best = sim
        if sim >= 0.5:
            near += 1
    return best, near


def _trigram_search(conn, query, limit):
    """Search using trigram FTS5 — substring matching, cross-lingual, typo-tolerant.

    Strategy:
      1. AND query — matches ALL trigrams (best ranking for exact phrases)
      2. word-AND — every WORD present anywhere in the verse (multi-word
         topical queries like "redeemed blood" must not degrade to one-word hits)
      3. OR query — matches ANY trigram, re-ranked by trigram-overlap ratio
         against the query so typo variants ("covenent") float above noise
    """
    if len(query) < 2:
        return []
    sanitized = _sanitize_fts_query(query)

    def _rows(match_expr, row_limit):
        return conn.execute("""
            SELECT v.id, v.book_id, v.text_english, v.text_hebrew, v.text_greek,
                   b.title, b.work_id
            FROM verses_fts_trigram f
            JOIN verses v ON v.id = f.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE verses_fts_trigram MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (match_expr, row_limit)).fetchall()

    def _shape(rows):
        return [
            {
                "verse": r["id"],
                "text": r["text_english"][:200] if r["text_english"] else "",
                "book": r["title"],
                "book_id": r["book_id"],
                "work_id": r["work_id"],
            }
            for r in rows
        ]

    # 1. AND query (exact phrase / exact substring)
    try:
        rows = _rows(sanitized, limit)
        if rows:
            return _shape(rows)
    except Exception:
        pass

    # 2. word-AND — all query words present, any position
    words = _query_words(sanitized)
    if len(words) > 1:
        try:
            and_expr = " AND ".join(f'"{w}"' for w in words)
            rows = _rows(and_expr, limit)
            if rows:
                return _shape(rows)
        except Exception:
            pass

    # 3. OR query (typo-tolerant), re-ranked by word-level fuzzy similarity
    ngrams = _ngrams(sanitized, 3)
    if len(ngrams) >= 2:
        try:
            or_query = " OR ".join(f'"{g}"' for g in ngrams if len(g) == 3)
            if or_query:
                rows = _rows(or_query, limit * 4)
                if rows:
                    qgrams = {g for g in ngrams if len(g) == 3}

                    def sort_key(idx_row):
                        idx, r = idx_row
                        best, near = _fuzzy_score(
                            r["text_english"] or "", qgrams, len(sanitized)
                        )
                        return (-best, -near, idx)

                    ranked = sorted(enumerate(rows), key=sort_key)
                    return _shape([r for _, r in ranked[:limit]])
        except Exception:
            pass

    return []


def search_text(conn, query, book=None, works=None, limit=25):
    """Search verses by English text.

    Uses trigram FTS5 for substring matching with BM25 ranking.
    Falls back to LIKE for typo tolerance.

    Args:
        query: Search term
        book: Optional book ID filter (e.g., 'gen', 'isa', '1QS', 'dc' for D&C)
        works: Optional list of work IDs to filter (e.g., ['ot','nt','dss','bom','dc','pgp','apoc','pseu','expanded'])
        limit: Max results (default 25, max 50)

    Returns: dict with query, count, results list (each with verse, text, book, book_id, work_id)
    """
    limit = min(limit, 50)

    # 1. Try trigram FTS5 first
    results = _trigram_search(conn, query, limit)
    if results:
        return {"query": query, "count": len(results), "results": results}

    # 2. Fallback to LIKE for typo tolerance
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


def _xlingual_trigram_search(conn, query, limit):
    """Search English via trigram FTS5 for xlingual endpoint format."""
    if len(query) < 2:
        return []
    sanitized = _sanitize_fts_query(query)

    # 1. Try AND query (exact trigram overlap — best ranking)
    try:
        rows = conn.execute("""
            SELECT verse_id, search_text
            FROM verses_fts_trigram
            WHERE verses_fts_trigram MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (sanitized, limit)).fetchall()
        if rows:
            return rows
    except Exception:
        pass

    # 2. Try OR query (typo-tolerant — match any trigram)
    ngrams = _ngrams(sanitized, 3)
    if len(ngrams) >= 2:
        try:
            or_query = " OR ".join(f'"{g}"' for g in ngrams if len(g) == 3)
            if or_query:
                rows = conn.execute("""
                    SELECT verse_id, search_text
                    FROM verses_fts_trigram
                    WHERE verses_fts_trigram MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (or_query, limit)).fetchall()
                if rows:
                    return rows
        except Exception:
            pass

    return []


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
        # 1. Try trigram FTS5 first (substring matching, BM25 ranked)
        trigram_hits = _xlingual_trigram_search(conn, query, limit)
        if trigram_hits:
            results.extend(
                {"verse": r["verse_id"], "text": r["search_text"][:120], "language": "english"}
                for r in trigram_hits
            )
        else:
            # 2. Fallback to LIKE for typo tolerance / very short queries
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
        from lib.api.search_backend import _classify_query, _vector_search, _keyword_search, _merge_results, _search_hebrew, _search_greek
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
                            from lib.api.refs import format_reference
                            results.append({
                                "verse": vid,
                                "reference": format_reference(v['book_title'], vid, v['chapter'], v['verse']),
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
            # Run graph search as 3rd signal
            graph_results = []
            try:
                from lib.api.graph_search import graph_search as _gs
                graph_results = _gs(conn, query, top_k=limit)
            except Exception:
                pass

            try:
                from lib.api.search_backend import _get_embed_model
                model = _get_embed_model()
                if model is not None:
                    vec_results = _vector_search(conn, model, query, limit, mode)
                    results = _merge_results(results, vec_results, mode, list_c=graph_results)
                else:
                    kw_results = _keyword_search(conn, query, limit)
                    results = _merge_results(results, kw_results, "keyword", list_c=graph_results)
            except Exception:
                kw_results = _keyword_search(conn, query, limit)
                results = _merge_results(results, kw_results, "keyword", list_c=graph_results)

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


# ─── Section search: group verse hits into topical sections ───


def _parse_vid(verse_id):
    """Parse a verse id into (chapter_key, verse_int, chapter_int_or_None).

      isa.52.13    -> ('52', 13, 52)
      dc104.104.51 -> ('104', 51, 104)
      dss.1QHa.5   -> ('1QHa', 5, None)   (scroll hymn numbers)
    """
    parts = verse_id.split(".")
    if len(parts) >= 3 and parts[-1].isdigit():
        ch, vs = parts[-2], int(parts[-1])
        return ch, vs, (int(ch) if ch.isdigit() else None)
    return verse_id, -1, None


def _cluster_hits(hits, gap=3, min_hits=2):
    """Cluster verse hits into near-contiguous sections.

    Hits are grouped per book and sorted canonically. A hit joins the current
    cluster when it is within `gap` verses of the previous hit — including
    across a chapter boundary (the last verses of chapter N connect to the
    first `gap` verses of chapter N+1, so passages like Isa 52:13–53:12 stay
    in one section). Clusters with fewer than `min_hits` verses are dropped —
    singletons are already served by plain scripture_search.
    """
    by_book = {}
    meta = {}
    for h in hits:
        by_book.setdefault(h["book_id"], []).append(h)
        meta[h["book_id"]] = h.get("book") or h["book_id"]

    def adjacent(cur, prv):
        if prv is None:
            return True
        if cur[2] is not None and prv[2] is not None:
            if cur[2] == prv[2]:
                return cur[1] - prv[1] <= gap
            # Next chapter's opening verses continue the passage.
            return cur[2] == prv[2] + 1 and cur[1] <= gap
        # Non-numeric chapters (scroll units): same unit only.
        return cur[0] == prv[0] and 0 <= cur[1] - prv[1] <= gap

    sections = []
    for book_id, book_hits in by_book.items():
        parsed = sorted(
            ((_parse_vid(h["verse"]), h) for h in book_hits),
            key=lambda p: (p[0][2] if p[0][2] is not None else -1, p[0][1]),
        )
        cluster = []
        prev = None

        def flush():
            if len(cluster) >= min_hits:
                sections.append((book_id, list(cluster)))

        for key, h in parsed + [(None, None)]:  # sentinel flushes the last cluster
            if h is not None:
                if not adjacent(key, prev):
                    flush()
                    cluster.clear()
                cluster.append(h)
                prev = key
            else:
                flush()

    out = []
    for book_id, cluster in sections:
        verses = [h["verse"] for h in cluster]
        s_ch, s_vs, s_chi = _parse_vid(verses[0])
        e_ch, e_vs, e_chi = _parse_vid(verses[-1])
        start, end = verses[0], verses[-1]
        if s_chi is not None and s_chi == e_chi:
            span = e_vs - s_vs + 1
        else:
            span = len(verses)
        out.append({
            "section": start if start == end else f"{start}-{end}",
            "range": {"start": start, "end": end},
            "book_id": book_id,
            "book": meta.get(book_id, book_id),
            "hits": len(cluster),
            "span_verses": span,
            "verses": verses,
            "preview": cluster[0].get("text", ""),
        })
    # Densest sections first, then tightest span.
    out.sort(key=lambda s: (-s["hits"], s["span_verses"]))
    return out


def search_sections(conn, query, book=None, works=None, limit=10,
                    min_hits=2, gap=3):
    """Search for TOPIC SECTIONS rather than isolated verses.

    Runs the same trigram text search as scripture_search with a wide net,
    then clusters hits that sit close together in the same book into
    contiguous sections (e.g. isa.52.13-53.12). Surfaces passages where a
    topic is treated at length instead of a flat list of single verses.

    Args:
        query: Search term
        book: Optional book ID filter
        works: Optional list of work IDs to filter
        limit: Max sections returned (default 10)
        min_hits: Verses a section must contain (default 2)
        gap: Max verse distance between hits in one section (default 3)

    Returns: dict with query, count, sections list. Each section carries
    section label, range, hit count, span, member verses, and a preview.
    """
    limit = max(1, min(limit, 25))
    # Wide net: clustering needs all nearby hits, not just the top-ranked ones.
    hits = _trigram_search(conn, query, 400)
    if not hits:
        # LIKE fallback mirrors search_text's typo-tolerance path.
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
        sql += " ORDER BY b.work_id, v.book_id, v.chapter, v.verse LIMIT 400"
        rows = conn.execute(sql, params).fetchall()
        hits = [
            {
                "verse": r["id"],
                "text": r["text_english"][:200] if r["text_english"] else "",
                "book": r["title"],
                "book_id": r["book_id"],
                "work_id": r["work_id"],
            }
            for r in rows
        ]

    if book and book != "dc":
        hits = [h for h in hits if h["book_id"] == book]
    if works:
        hits = [h for h in hits if h.get("work_id") in works]

    # Phase 1: word-recurrence clusters (contiguous blocks repeating the term).
    word_sections = _cluster_hits(hits, gap=gap, min_hits=min_hits)
    consumed = {v for c in word_sections for v in c["verses"]}

    # Phase 2: graph-bridged thematic sections for scattered hits — passages
    # that TREAT the topic without repeating the noun contiguously (e.g. the
    # servant songs of Isaiah bridge via direct_quotation / allusion edges).
    graph_sections = _graph_sections(conn, hits, consumed, min_hits=min_hits)

    sections = [{**c, "basis": "word"} for c in word_sections]
    sections.extend(graph_sections)
    sections.sort(key=lambda s: (
        0 if s.get("basis") == "word" else 1,
        -s["hits"],
        s["span_verses"] if s["span_verses"] is not None else 10_000,
    ))
    sections = sections[:limit]
    return {"query": query, "count": len(sections), "sections": sections}


def _merge_graph_anchors(anchor_ids, direct_edges, shared_neighbors):
    """Group anchor verse ids into thematic clusters (pure — no DB).

    Args:
        anchor_ids: list of verse ids
        direct_edges: iterable of (a, b) pairs — anchors connected by an edge
        shared_neighbors: dict neighbor -> list of anchors touching it

    Returns: list of groups (each a sorted list of anchor ids), largest first.
    """
    parent = {a: a for a in anchor_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in direct_edges:
        if a in parent and b in parent:
            union(a, b)
    for aset in shared_neighbors.values():
        members = [a for a in aset if a in parent]
        for i in range(len(members) - 1):
            union(members[i], members[i + 1])

    groups = {}
    for a in anchor_ids:
        groups.setdefault(find(a), []).append(a)
    return sorted(
        (sorted(g) for g in groups.values()),
        key=lambda g: -len(g),
    )


def _graph_sections(conn, hits, exclude_ids, min_hits=2, max_chapters=12,
                    max_evidence=6, min_strength=0.35):
    """Graph-bridged thematic sections from scattered verse hits.

    Anchors are the search hits not already consumed by word clusters. Two
    anchors join a section when a verse-level connection links them directly
    or they share a same-book connected neighbor. Sections spanning more than
    `max_chapters` are dropped (whole-testament blobs are not sections).
    Each section carries `basis: "graph"` plus its strongest evidence edges.
    """
    by_book = {}
    meta = {}
    text_of = {}
    for h in hits:
        if h["verse"] in exclude_ids:
            continue
        by_book.setdefault(h["book_id"], []).append(h["verse"])
        meta[h["book_id"]] = h.get("book") or h["book_id"]
        text_of[h["verse"]] = h.get("text", "")

    out = []
    for book_id, anchor_ids in by_book.items():
        if len(anchor_ids) < min_hits:
            continue
        ph = ",".join("?" for _ in anchor_ids)
        like = f"{book_id}.%"
        try:
            rows = conn.execute(f"""
                SELECT source_verse, target_verse, type, strength FROM connections
                WHERE ((source_verse IN ({ph}) AND target_verse LIKE ?)
                    OR (target_verse IN ({ph}) AND source_verse LIKE ?))
                  AND strength >= ?
                  AND layer IN ('intertextual', 'linguistic')
            """, [*anchor_ids, like, *anchor_ids, like, min_strength]).fetchall()
        except Exception:
            continue

        anchor_set = set(anchor_ids)
        direct_edges = []
        shared = {}
        edge_meta = {}
        for r in rows:
            s, t = r["source_verse"], r["target_verse"]
            s_is, t_is = s in anchor_set, t in anchor_set
            if s == t:
                continue
            if s_is and t_is:
                direct_edges.append((s, t))
                edge_meta[frozenset((s, t))] = (r["type"], r["strength"])
            elif s_is:
                shared.setdefault(t, set()).add(s)
            elif t_is:
                shared.setdefault(s, set()).add(t)

        for group in _merge_graph_anchors(anchor_ids, direct_edges, shared):
            if len(group) < min_hits:
                continue
            ordered = sorted(group, key=lambda v: (_parse_vid(v)[2] if _parse_vid(v)[2] is not None else -1, _parse_vid(v)[1]))
            start, end = ordered[0], ordered[-1]
            s_ch, s_vs, s_chi = _parse_vid(start)
            e_ch, e_vs, e_chi = _parse_vid(end)
            chapters_spanned = (e_chi - s_chi + 1) if (s_chi is not None and e_chi is not None) else 1
            if chapters_spanned > max_chapters:
                continue
            evidence = [
                {"source": s, "target": t, "type": ty, "strength": st}
                for fs, (ty, st) in sorted(
                    edge_meta.items(), key=lambda kv: -kv[1][1]
                )
                for s, t in [tuple(sorted(fs))]
                if s in group and t in group
            ][:max_evidence]
            out.append({
                "section": start if start == end else f"{start}-{end}",
                "range": {"start": start, "end": end},
                "book_id": book_id,
                "book": meta.get(book_id, book_id),
                "hits": len(group),
                "span_verses": (e_vs - s_vs + 1) if (s_chi is not None and s_chi == e_chi) else None,
                "chapters_spanned": chapters_spanned,
                "verses": ordered,
                "preview": text_of.get(ordered[0], ""),
                "basis": "graph",
                "evidence": evidence,
            })
    return out
