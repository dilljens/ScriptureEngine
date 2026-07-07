#!/usr/bin/env python3
"""Scripture Knowledge Engine — HTTP API Server.

FastAPI app that wraps lib/ modules as HTTP endpoints.
Loads all connection data into RAM at startup for sub-ms responses.
Auto-generates OpenAPI docs at /docs.

Usage:
  cd web && uvicorn server:app --reload --port 8000
  # Open http://localhost:8000/docs for interactive API browser
"""

import sys, os, json, sqlite3, time, asyncio
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from lib.db import get_db, get_db_vec, DEFAULT_DB_PATH
from lib.gematria import compute_all, find_divine_name_matches
from lib.connections.pardes import get_pardes_level, LEVELS as PARDES_LEVELS
from lib.sod import atbash as atb, acrostic, gematria_advanced, hidden_names
from lib.controls.calibration import QUALITY_LEVELS, get_quality_stars, rate_connection_row, enrich_connection
from lib.api import TOOL_REGISTRY, call_tool
from lib.api.conversations import (
    create_session, get_session, list_sessions, update_session, delete_session,
    add_message, list_connections, add_connection, promote_connection,
)
from lib.api.study import (
    create_guide, get_guide, list_guides, update_guide as study_update,
    add_step as study_add_step, remove_step as study_remove_step,
    reorder_steps as study_reorder, bulk_update_steps as study_bulk_update,
    export_json as study_export_json,
    export_html as study_export_html, import_json as study_import_json,
    publish_study as study_publish, get_published as study_get_published,
    list_published as study_list_published, fork_published as study_fork,
)
from lib.lexicon import search_lexicon, get_lexicon_entry, get_root_family, get_concordance, get_domain_members
from lib.patterns.intra_verse import detect_intra_verse

app = FastAPI(
    title="Scripture Knowledge Engine",
    description="API for the scripture connection graph — 826K connections across 93 types in 10 layers, Hebrew + Greek + Vulgate, PaRDeS levels, hidden patterns, lexicon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# ─── RAM Cache (loaded at startup, zero disk reads after) ───
GUIDE_CACHE = {}          # verse_id → {connections_json, gematria_json, quality_summary, ...}
VERSE_CACHE = {}          # verse_id → {id, text_english, text_hebrew, text_greek, book_id, chapter, verse, book_title}
ENTITY_CACHE = []         # all entity links
LEXICON_CACHE = {}        # lemma → lexicon entry (loaded at startup)
VEC_CACHE = {"available": False}  # vector search — populated by embed script


@app.on_event("startup")
def load_ram_cache():
    """Load all passage guides + verse data into RAM at startup.
    
    Eliminates disk reads for all verse and connection lookups.
    ~41K guides, ~42K verses, ~500MB total RAM.
    Automatically skips when running multi-worker (each worker loads its own).
    
    Set SCRIPTURE_WORKERS=1 to force RAM cache, SCRIPTURE_WORKERS=0 to skip.
    """
    workers = int(os.environ.get("SCRIPTURE_WORKERS", "1"))
    if workers != 1:
        print(f"  Skipping RAM cache (multi-worker: {workers} workers). Using direct SQLite.", flush=True)
        return

    print("Loading passage guides into RAM...", flush=True)
    db_path = DEFAULT_DB_PATH
    if not os.path.exists(db_path):
        print(f"  DB not found: {db_path}", flush=True)
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Load verses
    rows = conn.execute("""
        SELECT v.*, b.title as book_title
        FROM verses v JOIN books b ON b.id = v.book_id
    """).fetchall()
    for r in rows:
        d = dict(r)
        VERSE_CACHE[d["id"]] = d
    print(f"  {len(VERSE_CACHE)} verses loaded", flush=True)

    # Load passage guides
    rows = conn.execute("""
        SELECT verse_id, connections_json, gematria_json, quality_summary,
               layer_count, total_connections
        FROM passage_guides
    """).fetchall()
    for r in rows:
        d = dict(r)
        GUIDE_CACHE[d["verse_id"]] = d
    print(f"  {len(GUIDE_CACHE)} passage guides loaded", flush=True)

    # Load entity links
    rows = conn.execute("SELECT * FROM entity_links").fetchall()
    for r in rows:
        ENTITY_CACHE.append(dict(r))
    print(f"  {len(ENTITY_CACHE)} entity links loaded", flush=True)

    # Load lexicon
    lex_rows = conn.execute("SELECT * FROM lexicon").fetchall()
    for r in lex_rows:
        LEXICON_CACHE[r["lemma"]] = dict(r)
    print(f"  {len(LEXICON_CACHE)} lexicon entries loaded", flush=True)

    # Check vector availability — without loading vec0 module
    vec_table = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='vec_verses'
    """).fetchone()
    if vec_table:
        VEC_CACHE["available"] = True
        VEC_CACHE["count"] = "check via vec queries"
        print(f"  Vectors available (verify via semantic-search endpoint)", flush=True)
    else:
        print("  Vectors not found — run: .venv/bin/python3 scripts/embed_verses.py", flush=True)

    conn.close()
    print(f"  Total RAM cache: {len(VERSE_CACHE) + len(GUIDE_CACHE) + len(ENTITY_CACHE)} items", flush=True)

CONNECTION_TYPE_MAP = {
    "linguistic": "Linguistic", "numerical": "Numerical",
    "structural": "Structural", "intertextual": "Intertextual",
    "textual": "Textual", "geographic": "Geographic",
    "chronological": "Chronological", "interpretive": "Interpretive",
    "frequency": "Frequency", "symbolic": "Symbolic",
}


# ─── Verse & Passage Guide ───

@app.get("/api/v1/verses/{ref:path}")
def get_verse(ref: str, show_signals: Optional[bool] = Query(False, description="Enrich connections with quality signal breakdown"), context: Optional[int] = Query(0, description="Number of surrounding verses to include for context window (e.g. context=3 gives ±3 verses)")):
    """Get verse text with connections — served from RAM cache or SQLite."""
    ref = ref.replace(":", ".").replace(" ", ".")
    import re

    # Try RAM cache first, fall back to SQLite for multi-worker mode
    r = VERSE_CACHE.get(ref) if VERSE_CACHE else None
    if not r:
        conn = get_db()
        # Try exact match first (preserves case for 1QS, 1QHa, etc.)
        row = conn.execute("SELECT v.*, b.title as book_title FROM verses v JOIN books b ON b.id=v.book_id WHERE v.id=?", (ref,)).fetchone()
        # Try case-insensitive (some clients lowercase the path)
        if not row:
            row = conn.execute("SELECT v.*, b.title as book_title FROM verses v JOIN books b ON b.id=v.book_id WHERE LOWER(v.id)=?", (ref.lower(),)).fetchone()
        # Try regex-parsed: book.chapter.verse
        if not row:
            m = re.match(r'([a-zA-Z0-9_]+)\.(\d+)\.(\d+)', ref)
            if m:
                book_str = m.group(1)
                ch = int(m.group(2))
                vs = int(m.group(3))
                # Try as-is
                row = conn.execute("""SELECT v.*, b.title as book_title FROM verses v
                    JOIN books b ON b.id=v.book_id WHERE v.id=?""", (f"{book_str}.{ch}.{vs}",)).fetchone()
                # Try DSS prefixed
                if not row:
                    row = conn.execute("""SELECT v.*, b.title as book_title FROM verses v
                        JOIN books b ON b.id=v.book_id WHERE v.id=?""", (f"dss.{book_str}.{ch}.{vs}",)).fetchone()
                # Try DSS no-chapter
                if not row:
                    row = conn.execute("""SELECT v.*, b.title as book_title FROM verses v
                        JOIN books b ON b.id=v.book_id WHERE v.id=?""", (f"dss.{book_str}.{vs}",)).fetchone()
        conn.close()
        if row:
            r = dict(row)  # Convert Row to dict for consistent access
    if not r:
        raise HTTPException(status_code=404, detail=f"Verse not found: {ref}")

    vid = r["id"]

    # Track hit — increment verse hit count in background
    try:
        conn2 = get_db()
        conn2.execute("UPDATE verses SET hit_count = COALESCE(hit_count, 0) + 1 WHERE id = ?", (vid,))
        # Also increment hit_count on related connections (first 500)
        conn2.execute("""
            UPDATE connections SET hit_count = COALESCE(hit_count, 0) + 1
            WHERE (source_verse = ? OR target_verse = ?) AND hit_count < 99999
        """, (vid, vid))
        conn2.commit()
        conn2.close()
    except Exception:
        pass  # Non-critical — don't fail the response if tracking fails

    # Guide from RAM cache or SQLite
    guide = GUIDE_CACHE.get(vid) if GUIDE_CACHE else None
    if not guide:
        conn = get_db()
        row = conn.execute("SELECT * FROM passage_guides WHERE verse_id=?", (vid,)).fetchone()
        conn.close()
        guide = dict(row) if row else None

    resp = {
        "verse_id": vid,
        "reference": f"{r.get('book_title', '')} {r.get('chapter','')}:{r.get('verse','')}",
        "text_english": r["text_english"],
        "text_hebrew": r.get("text_hebrew") or None,
        "text_greek": r.get("text_greek") or None,
        "has_hebrew": bool(r.get("has_hebrew")),
        "has_greek": bool(r.get("has_greek")),
        "cached": bool(VERSE_CACHE),
    }

    if guide:
        resp["connections"] = json.loads(guide["connections_json"])
        resp["total_connections"] = guide["total_connections"]
        resp["layer_count"] = guide["layer_count"]
        
        # Enrich with signals if requested
        if show_signals:
            enriched = {}
            for layer, items in resp["connections"].items():
                enriched[layer] = [enrich_connection(item) for item in items]
            resp["connections"] = enriched
        if guide.get("gematria_json") and guide["gematria_json"] != "null":
            resp["gematria"] = json.loads(guide["gematria_json"])
        if guide.get("quality_summary"):
            resp["quality_summary"] = json.loads(guide["quality_summary"])
        # PaRDeS distribution from RAM
        pardes = {}
        for layer, items in resp.get("connections", {}).items():
            for item in items:
                lvl = get_pardes_level(layer, item["type"])
                pardes[lvl] = pardes.get(lvl, 0) + 1
        resp["pardes"] = pardes

    # Context window — surrounding verses for inline preview
    if context > 0:
        parts = vid.split(".")
        if len(parts) >= 3:
            try:
                bk = parts[0]
                ch = int(parts[1])
                vs = int(parts[2])
                start_vs = max(1, vs - context)
                end_vs = vs + context
                conn_ctx = get_db()
                ctx_rows = conn_ctx.execute("""
                    SELECT id, book_id, chapter, verse, text_english, text_hebrew
                    FROM verses WHERE book_id = ? AND chapter = ? AND verse BETWEEN ? AND ?
                    ORDER BY verse
                """, (bk, ch, start_vs, end_vs)).fetchall()
                conn_ctx.close()
                context_verses = []
                for row in ctx_rows:
                    d = dict(row)
                    d["is_target"] = (d["verse"] == vs)
                    context_verses.append(d)
                resp["context_verses"] = context_verses
            except (ValueError, IndexError):
                pass

    return {"ok": True, "data": resp}


@app.get("/api/v1/verses/{ref:path}/connections")
def get_verse_connections(ref: str, layer: Optional[str] = None, min_quality: Optional[str] = None, discovered_by: Optional[str] = None, min_confidence: Optional[float] = None, show_signals: Optional[bool] = False):
    """Get filtered connections for a verse.
    
    Filters:
      layer: only show this layer
      min_quality: minimum quality tier (verified, strong, probable, suggested)
      discovered_by: only show connections found by this method (text, tsk, llm, algorithm)
      min_confidence: minimum overall confidence (0.0-1.0)
      show_signals: if true, enrich each connection with the full signal breakdown
    """
    resp = get_verse(ref)
    if not resp["ok"]:
        return resp
    data = resp["data"]
    conns = data.get("connections", {})

    # Filter by layer
    if layer and layer in conns:
        conns = {layer: conns[layer]}
    elif layer:
        conns = {}

    # Filter by quality, discovered_by, and min_confidence
    if min_quality or discovered_by or min_confidence or show_signals:
        filtered = {}
        for lyr, items in conns.items():
            filtered_items = []
            for item in items:
                # Get signals
                sigs = rate_connection_row({
                    "discovered_by": item.get("discovered_by", "algorithm"),
                    "type": item.get("type", ""),
                    "confidence": item.get("confidence", 0.5),
                    "confirmation_count": item.get("confirmation_count", 0),
                    "metadata": item.get("metadata", "{}"),
                })
                
                # Apply filters
                if min_quality:
                    star_order = {"verified": 5, "strong": 4, "probable": 3, "suggested": 2, "pattern": 1}
                    if sigs["stars"] < star_order.get(min_quality, 1):
                        continue
                
                if discovered_by:
                    if sigs["signals"]["discovery_method"] != discovered_by:
                        continue
                
                if min_confidence is not None:
                    if sigs["overall_confidence"] < min_confidence:
                        continue
                
                if show_signals:
                    item["signals"] = sigs
                
                filtered_items.append(item)
            
            if filtered_items:
                filtered[lyr] = filtered_items
        
        conns = filtered

    return {"ok": True, "data": {"verse": ref, "layers": list(conns.keys()), "connections": conns}}


# ─── Search ───

@app.get("/api/v1/search")
def search(
    q: str = Query(..., description="Search term"),
    lang: str = "all",
    limit: int = 20,
    offset: int = 0,
    book: str = "",
):
    """Search across English, Hebrew, and Greek simultaneously.

    Supports query syntax:
      "exact phrase"  — exact phrase match
      -word           — exclude verses containing word
      book:gen        — scope to a specific book ID
      work:ot         — scope to an entire work

    English uses FTS5 full-text search (50-100x faster than LIKE).
    Hebrew searches against niqqud-stripped words (hebrew_plain).
    """
    conn = get_db()
    results = []

    # Parse query syntax: extract book/work filter, exclude terms, phrase terms
    filter_book = book  # explicit ?book= param
    exclude_terms = []
    phrase_terms = []
    fuzzy_terms = []
    for token in q.strip().split():
        if token.startswith("book:") or token.startswith("b:"):
            filter_book = token.split(":", 1)[1].lower()
        elif token.startswith("work:") or token.startswith("w:"):
            filter_book = token.split(":", 1)[1].lower()
        elif token.startswith("-"):
            exclude_terms.append(token[1:].lower())
        elif token.startswith('"') and token.endswith('"'):
            phrase_terms.append(token[1:-1])
        else:
            fuzzy_terms.append(token.lower())

    search_query = " ".join(fuzzy_terms) if fuzzy_terms else q.strip()
    limit_plus_one = limit + 1  # fetch one extra to detect has_more

    if not search_query and not phrase_terms:
        conn.close()
        return {"ok": True, "data": {"query": q, "total": 0, "results": [], "has_more": False}}

    if lang in ("all", "english"):
        if search_query:
            fts_query = search_query.replace('"', '""')
            terms = [t.strip() for t in fts_query.split() if t.strip()]
            if terms:
                # Build FTS5 match expression
                match_parts = []
                for t in terms:
                    if t.startswith("-"):
                        match_parts.append(f'NOT ("{t[1:]}"*)')
                    else:
                        match_parts.append(f'"{t}"*')
                for pt in phrase_terms:
                    match_parts.append(f'"{pt}"')
                fts_match = " AND ".join(match_parts)

                # Base query
                base_sql = """
                    FROM verses_fts f
                    JOIN verses v ON v.id = f.verse_id
                    JOIN books b ON b.id = v.book_id
                    WHERE verses_fts MATCH ?
                """
                params = [fts_match]

                # Apply book filter
                if filter_book:
                    # Support both work-level (ot, nt) and book-level (gen, isa) filters
                    base_sql += " AND (b.id = ? OR b.id LIKE ?)"
                    params.extend([filter_book, f"{filter_book}%"])

                try:
                    # Get total count
                    total_row = conn.execute(f"SELECT COUNT(*) as cnt {base_sql}", params).fetchone()
                    total_matches = total_row["cnt"] if total_row else 0

                    # Get paginated results with highlighted offsets
                    rows = conn.execute(f"""
                        SELECT v.id, v.text_english, b.title,
                               offsets(verses_fts) as match_offsets
                        {base_sql}
                        ORDER BY rank
                        LIMIT ? OFFSET ?
                    """, params + [limit_plus_one, offset]).fetchall()
                except Exception:
                    # Fallback to LIKE
                    like_q = f"%{search_query}%"
                    like_sql = "SELECT v.id, v.text_english, b.title FROM verses v JOIN books b ON b.id=v.book_id WHERE v.text_english LIKE ?"
                    like_params = [like_q]
                    if filter_book:
                        like_sql += " AND (b.id = ? OR b.id LIKE ?)"
                        like_params.extend([filter_book, f"{filter_book}%"])
                    total_row = conn.execute(f"SELECT COUNT(*) as cnt {like_sql.replace('SELECT v.id, v.text_english, b.title', '')}", like_params).fetchone()
                    total_matches = total_row["cnt"] if total_row else 0
                    rows = conn.execute(f"{like_sql} LIMIT ? OFFSET ?", like_params + [limit_plus_one, offset]).fetchall()

                for r in rows:
                    item = {"verse": r["id"], "text": r["text_english"][:200], "book": r["title"], "language": "english"}
                    if "match_offsets" in r.keys():
                        offsets = []
                        parts = r["match_offsets"].split()
                        for i in range(0, len(parts), 4):
                            if i + 3 < len(parts):
                                try:
                                    offsets.append({"pos": int(parts[i + 2]), "len": int(parts[i + 3])})
                                except (ValueError, IndexError):
                                    pass
                        if offsets:
                            item["highlights"] = offsets
                    results.append(item)

    if lang in ("all", "hebrew") and search_query:
        hebrew_sql = """
            SELECT DISTINCT v.id, v.text_hebrew, v.text_english, b.title
            FROM gematria g
            JOIN verses v ON v.id=g.verse_id
            JOIN books b ON b.id=v.book_id
            WHERE (g.hebrew_plain LIKE ? OR g.word_hebrew LIKE ?)
        """
        hebrew_params = [f"%{search_query}%", f"%{search_query}%"]
        if filter_book:
            hebrew_sql += " AND (b.id = ? OR b.id LIKE ?)"
            hebrew_params.extend([filter_book, f"{filter_book}%"])
        rows = conn.execute(f"{hebrew_sql} LIMIT ? OFFSET ?", hebrew_params + [limit_plus_one, offset]).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append({"verse": r["id"], "text": (r["text_hebrew"] or "")[:120], "english": (r["text_english"] or "")[:60], "book": r["title"], "language": "hebrew"})

    if lang in ("all", "greek") and search_query:
        greek_sql = """
            SELECT DISTINCT v.id, v.text_greek, v.text_english, b.title
            FROM gematria_greek g
            JOIN verses v ON v.id=g.verse_id
            JOIN books b ON b.id=v.book_id
            WHERE g.word_greek LIKE ? OR g.lemma LIKE ?
        """
        greek_params = [f"%{search_query}%", f"%{search_query}%"]
        if filter_book:
            greek_sql += " AND (b.id = ? OR b.id LIKE ?)"
            greek_params.extend([filter_book, f"{filter_book}%"])
        rows = conn.execute(f"{greek_sql} LIMIT ? OFFSET ?", greek_params + [limit_plus_one, offset]).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append({"verse": r["id"], "text": (r["text_greek"] or "")[:120], "english": (r["text_english"] or "")[:60], "book": r["title"], "language": "greek"})

    conn.close()
    has_more = len(results) > limit
    return {
        "ok": True,
        "data": {
            "query": q,
            "total": len(results[:limit]),
            "results": results[:limit],
            "has_more": has_more,
            "total_estimate": len(results),
        },
    }


# ─── Gematria ───

@app.get("/api/v1/gematria")
def gematria(word: Optional[str] = None, value: Optional[int] = None, system: str = "standard"):
    """Look up gematria values. Provide a Hebrew word or a numerical value."""
    conn = get_db()

    if word:
        vals = compute_all(word)
        matches = find_divine_name_matches(vals["standard"])
        conn.close()
        return {"ok": True, "data": {"word": word, "gematria": vals, "divine_name_matches": matches}}

    if value is not None:
        col = {"standard": "value_standard", "ordinal": "value_ordinal", "reduced": "value_reduced"}.get(system, "value_standard")
        rows = conn.execute(f"SELECT DISTINCT g.verse_id, g.word_hebrew, g.{col} FROM gematria g WHERE g.{col}=? LIMIT 30", (value,)).fetchall()
        matches = find_divine_name_matches(value)
        conn.close()
        return {"ok": True, "data": {"value": value, "system": system, "total": len(rows), "divine_name_matches": matches, "results": [{"verse": r["verse_id"], "word": r["word_hebrew"]} for r in rows]}}

    conn.close()
    return {"ok": False, "error": "Provide word or value"}


# ─── Hidden Patterns (Sod) ───

@app.get("/api/v1/sod")
def sod(verse: Optional[str] = None, atbash_word: Optional[str] = None, acrostic_book: Optional[str] = None):
    """Explore hidden patterns — Atbash, acrostics, advanced gematria."""
    conn = get_db()
    result = {}

    if atbash_word:
        result["atbash"] = {"input": atbash_word, "decoded": atb.decode_atbash(atbash_word)}

    if acrostic_book:
        acro = acrostic.scan_book_for_acrostics(conn, acrostic_book)
        result["acrostic"] = acro if acro else {"note": "No acrostic found"}

    if verse:
        vid = verse
        row = conn.execute("SELECT v.text_hebrew, v.text_english FROM verses v WHERE v.id=?", (vid,)).fetchone()
        if row and row["text_hebrew"]:
            result["gematria"] = gematria_advanced.analyze_verse_gematria(row["text_hebrew"])
            result["hidden_names"] = hidden_names.find_divine_name_gematria_matches(conn, vid)

        # Notarikon
        if row and row["text_hebrew"]:
            from lib.sod.notarikon import first_letters, last_letters, first_and_last
            result["notarikon"] = {
                "first_letters": first_letters(row["text_hebrew"]),
                "last_letters": last_letters(row["text_hebrew"]),
            }

    conn.close()
    return {"ok": True, "data": result}


# ─── PaRDeS ───

@app.get("/api/v1/verses/{ref:path}/guide")
def get_passage_guide(ref: str):
    """Instant passage guide from RAM cache — sub-ms, zero disk."""
    ref = ref.replace(":", ".").replace(" ", ".").lower()
    import re
    r = VERSE_CACHE.get(ref)
    if not r:
        m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', ref)
        if m:
            vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"
            r = VERSE_CACHE.get(vid)
    if not r:
        raise HTTPException(status_code=404, detail=f"Verse not found: {ref}")
    guide = GUIDE_CACHE.get(r["id"])
    if not guide:
        return {"ok": True, "data": {"verse": r["id"], "note": "No connections"}}
    return {
        "ok": True,
        "data": {
            "verse": r["id"],
            "connections": json.loads(guide["connections_json"]),
            "total_connections": guide["total_connections"],
            "layer_count": guide["layer_count"],
            "gematria": json.loads(guide["gematria_json"]) if guide.get("gematria_json") and guide["gematria_json"] != "null" else None,
            "quality_summary": json.loads(guide["quality_summary"]) if guide.get("quality_summary") else None,
        }
    }

@app.get("/api/v1/semantic-search")
def semantic_search(q: str = Query(..., description="Query text"), limit: int = 20):
    """Semantic search — find verses by meaning, not keywords.
    
    Uses sqlite-vec vectors pre-computed by scripts/embed_verses.py.
    Returns verses ranked by cosine similarity to the query.
    """
    if not VEC_CACHE.get("available"):
        return {"ok": False, "error": "Vectors not available. Run: python3 scripts/embed_verses.py"}
    
    import struct, hashlib, re
    
    def ngram_hash(text, n=3, dim=384):
        vec = [0.0] * dim
        text = re.sub(r'[^a-zA-Z\u0590-\u05FF\s]', '', text.lower())
        for i in range(len(text) - n + 1):
            h = hashlib.md5(text[i:i + n].encode('utf-8')).digest()
            vec[struct.unpack_from('<I', h, 0)[0] % dim] += 1.0
        mag = sum(v * v for v in vec) ** 0.5
        return [v / mag for v in vec] if mag > 0 else vec
    
    conn = get_db_vec()
    vec = ngram_hash(q)
    vec_bytes = struct.pack(f'{len(vec)}f', *vec)
    
    rows = conn.execute("""
        SELECT verse_id, distance FROM vec_verses
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (vec_bytes, limit)).fetchall()
    
    results = []
    for r in rows:
        v = conn.execute("""
            SELECT text_english, b.title as book_title, chapter, verse
            FROM verses v JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (r["verse_id"],)).fetchone()
        if v:
            results.append({
                "verse": r["verse_id"],
                "reference": f"{v['book_title']} {v['chapter']}:{v['verse']}",
                "text": v["text_english"][:200],
                "similarity": round(1.0 - r["distance"], 3),
            })
    
    conn.close()
    return {"ok": True, "data": {"query": q, "total": len(results), "results": results}}


@app.get("/api/v1/pardes/{ref:path}")
def get_pardes(ref: str, level: Optional[str] = None):
    """Get connections grouped by PaRDeS interpretation level."""
    resp = get_verse(ref)
    if not resp["ok"]:
        return resp
    data = resp["data"]
    conns = data.get("connections", {})

    by_level = {}
    for layer, items in conns.items():
        for item in items:
            lvl = get_pardes_level(layer, item["type"])
            if level and lvl != level:
                continue
            if lvl not in by_level:
                info = PARDES_LEVELS.get(lvl, {})
                by_level[lvl] = {"name": info.get("name", lvl), "hebrew": info.get("hebrew", ""), "color": info.get("color", "#999"), "connections": []}
            by_level[lvl]["connections"].append({**item, "layer": layer})

    return {"ok": True, "data": {"verse": ref, "levels": by_level}}


# ─── Info ───

@app.get("/api/v1/info")
def get_info():
    """Get database and system statistics."""
    conn = get_db()
    layers = conn.execute("SELECT layer, COUNT(*) as c FROM connections GROUP BY layer ORDER BY layer").fetchall()
    quality = conn.execute("SELECT quality_level, COUNT(*) as c FROM connections GROUP BY quality_level").fetchall()
    pg = conn.execute("SELECT COUNT(*) as c FROM passage_guides").fetchone()["c"]
    conn.close()

    return {
        "ok": True,
        "data": {
            "total_connections": sum(r["c"] for r in layers),
            "total_verses": 42054,
            "hebrew_gematria": 305507,
            "greek_isopsephy": 137536,
            "passage_guides": pg,
            "layers": {r["layer"]: r["c"] for r in layers},
            "quality": {r["quality_level"]: r["c"] for r in quality},
            "tools_available": len(TOOL_REGISTRY),
        }
    }
    conn.close()


# ─── Lexicon (Word Dictionary) ───

@app.get("/api/v1/lexicon/search")
def lexicon_search(q: str = Query("", description="Search term — lemma, Hebrew, or English"), limit: int = Query(20, description="Max results")):
    """Search the scripture lexicon by lemma number, Hebrew word, or English translation."""
    conn = get_db()
    results = search_lexicon(conn, q, limit)
    conn.close()
    return {"ok": True, "data": {"query": q, "results": results, "total": len(results)}}


@app.get("/api/v1/lexicon/lemma/{lemma}")
def lexicon_lemma(lemma: str):
    """Get full lexicon entry for a lemma (Strong's number)."""
    conn = get_db()
    entry = get_lexicon_entry(conn, lemma)
    conn.close()
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Lemma not found: {lemma}")
    return {"ok": True, "data": entry}


@app.get("/api/v1/lexicon/root/{root_letters}")
def lexicon_root(root_letters: str):
    """Get all lemmas sharing a triconsonantal root."""
    conn = get_db()
    members = get_root_family(conn, root_letters)
    conn.close()
    return {"ok": True, "data": {"root": root_letters, "members": members, "total": len(members)}}


@app.get("/api/v1/lexicon/domain/{domain_name}")
def lexicon_domain(domain_name: str):
    """Browse all lemmas in a semantic domain."""
    conn = get_db()
    members = get_domain_members(conn, domain_name)
    conn.close()
    return {"ok": True, "data": {"domain": domain_name, "members": members, "total": len(members)}}


@app.get("/api/v1/lexicon/domains")
def lexicon_domains():
    """List all semantic domains."""
    conn = get_db()
    rows = conn.execute("SELECT name, description, ai_generated FROM semantic_domains ORDER BY name").fetchall()
    conn.close()
    return {"ok": True, "data": {"domains": [dict(r) for r in rows]}}


@app.get("/api/v1/lexicon/concordance/{lemma}")
def lexicon_concordance(lemma: str, limit: int = Query(50, description="Max verses to return")):
    """Get all verses containing a lemma (Strong's number)."""
    conn = get_db()
    verses = get_concordance(conn, lemma, limit)
    conn.close()
    return {"ok": True, "data": {"lemma": lemma, "verses": verses, "total": len(verses)}}


# ─── Grammar Coloring (Morphology) ───

MORPH_COLORS = {
    'HV': '#d4a574',  # Verb — tan
    'HN': '#74a8d4',  # Noun — blue
    'HA': '#a8d474',  # Adjective — green
    'HR': '#d4d474',  # Preposition — yellow
    'HC': '#d474a8',  # Conjunction — pink
    'HT': '#a8a8a8',  # Particle — gray
    'HP': '#74d4d4',  # Pronoun — cyan
    'HD': '#d4a8d4',  # Adverb — purple
    'AN': '#74d4a8',  # Aramaic Noun
    'AV': '#d4a874',  # Aramaic Verb
    'AA': '#a8d4a8',  # Aramaic Adjective
    'AR': '#d4d4a8',  # Aramaic Preposition
}

MORPH_POS = {
    'HV': 'verb',
    'HN': 'noun',
    'HA': 'adjective',
    'HR': 'preposition',
    'HC': 'conjunction',
    'HT': 'particle',
    'HP': 'pronoun',
    'HD': 'adverb',
    'AN': 'aramaic_noun',
    'AV': 'aramaic_verb',
    'AA': 'aramaic_adjective',
    'AR': 'aramaic_preposition',
}

@app.get("/api/v1/verses/{ref:path}/grammar")
def get_grammar(ref: str):
    """Get a verse with morphologically-tagged words — grammar coloring data."""
    ref = ref.replace(":", ".").replace(" ", ".").lower()
    vid = ref
    import re
    m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', ref)
    if m:
        vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"
    
    conn = get_db()
    words = conn.execute("""
        SELECT g.word_hebrew, g.word_english, g.morph, g.lemma, g.word_index,
               g.value_standard, g.value_ordinal, g.value_reduced
        FROM gematria g
        WHERE g.verse_id = ?
        ORDER BY g.word_index
    """, (vid,)).fetchall()
    
    result = []
    for w in words:
        morph = w['morph'] or ''
        prefix = morph[:2] if len(morph) >= 2 else ''
        cat = 'unknown'
        pos = 'unknown'
        color = '#cccccc'
        for pfx, c in MORPH_COLORS.items():
            if morph.startswith(pfx):
                color = c
                cat = pfx
                pos = MORPH_POS.get(pfx, 'unknown')
                break
        
        result.append({
            'hebrew': w['word_hebrew'] or '',
            'english': w['word_english'] or '',
            'morph': morph,
            'lemma': w['lemma'] or '',
            'pos': pos,
            'category': cat,
            'color': color,
            'gematria': {
                'standard': w['value_standard'],
                'ordinal': w['value_ordinal'],
                'reduced': w['value_reduced'],
            },
        })
    
    conn.close()
    return {"ok": True, "data": {"verse_id": vid, "words": result}}


@app.get("/api/v1/grammar/{ref:path}")
def get_chapter_grammar(ref: str):
    """Get word-level grammar/gematria data for all verses in a chapter.
    
    /api/v1/grammar/isa.55  → Word data for all verses in Isaiah 55
    """
    ref_clean = ref.strip("/")
    parts = ref_clean.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Use format: book.chapter (e.g., isa.55)")
    book_id = parts[0]
    chapter_num = int(parts[1])

    conn = get_db()
    verse_prefix = f"{book_id}.{chapter_num}."

    # Check if Greek NT data is available
    nt_books = ['matt','mark','luke','john','acts','rom','1cor','2cor','gal','eph','phil','col','1thes','2thes','1tim','2tim','titus','philem','heb','james','1pet','2pet','1john','2john','3john','jude','rev']
    is_greek = book_id in nt_books

    if is_greek:
        rows = conn.execute("""
            SELECT g.verse_id, g.word_greek as word_hebrew, '' as word_english,
                   g.morph, g.lemma, g.word_index,
                   g.value_standard, g.value_ordinal, g.value_reduced,
                   COALESCE(l.definition, '') as gloss
            FROM gematria_greek g
            LEFT JOIN lexicon l ON l.hebrew = g.lemma
            WHERE g.verse_id LIKE ?
            ORDER BY g.verse_id, g.word_index
        """, (f"{verse_prefix}%",)).fetchall()
    else:
        rows = conn.execute("""
            SELECT g.verse_id, g.word_hebrew, g.word_english, g.morph, g.lemma, g.word_index,
                   g.value_standard, g.value_ordinal, g.value_reduced,
                   COALESCE(lg.english_gloss, g.word_english, '') as gloss
            FROM gematria g
            LEFT JOIN lemma_gloss lg ON g.lemma = lg.lemma
            WHERE g.verse_id LIKE ?
            ORDER BY g.verse_id, g.word_index
        """, (f"{verse_prefix}%",)).fetchall()

    # Group by verse
    verses = {}
    for w in rows:
        vid = w["verse_id"]
        if vid not in verses:
            verses[vid] = []
        morph = w["morph"] or ""
        prefix = morph[:2] if len(morph) >= 2 else ""
        color = "#cccccc"
        for pfx, c in MORPH_COLORS.items():
            if morph.startswith(pfx):
                color = c
                break
        verses[vid].append({
            "hebrew": w["word_hebrew"] or "",
            "english": w["gloss"] or "",
            "morph": morph,
            "lemma": w["lemma"] or "",
            "word_index": w["word_index"],
            "color": color,
            "gematria": {"standard": w["value_standard"], "ordinal": w["value_ordinal"], "reduced": w["value_reduced"]},
        })

    conn.close()
    return {"ok": True, "data": {"ref": ref_clean, "total_verses": len(verses), "verses": verses}}


@app.get("/api/v1/connections/chapter/{ref:path}")
def get_chapter_connections(ref: str):
    """Get all non-structural connections for a chapter (intertextual, geographic, etc.).
    
    /api/v1/connections/chapter/isa.55
    """
    ref_clean = ref.strip("/")
    parts = ref_clean.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Use book.chapter")
    book_id = parts[0]
    chapter_num = int(parts[1])
    prefix = f"{book_id}.{chapter_num}.%"

    conn = get_db()
    rows = conn.execute("""
        SELECT c.source_verse, c.target_verse, c.type, c.subtype, c.layer, c.confidence, c.metadata
        FROM connections c
        WHERE c.source_verse LIKE ?
        AND c.layer NOT IN ('structural', 'linguistic')
        ORDER BY c.source_verse, c.type
    """, (prefix,)).fetchall()

    by_verse = {}
    for r in rows:
        vnum = r["source_verse"].split(".")[-1]
        if vnum not in by_verse:
            by_verse[vnum] = []
        by_verse[vnum].append({
            "type": r["type"],
            "layer": r["layer"],
            "target": r["target_verse"],
            "subtype": r["subtype"],
            "confidence": r["confidence"],
        })

    conn.close()
    return {"ok": True, "data": {"ref": ref_clean, "verses": by_verse}}


# ─── Footnotes (from LDS Church API) ───


@app.get("/api/v1/footnotes/{ref:path}")
def get_footnotes(ref: str):
    """Get footnotes for a verse or chapter.

    /api/v1/footnotes/isa.55.6     → Footnotes for Isa 55:6
    /api/v1/footnotes/isa.55       → All footnotes in Isa 55
    """
    import json as _json
    ref_clean = ref.strip("/")
    conn = get_db()

    # Determine match pattern
    parts = ref_clean.split(".")
    if len(parts) >= 3:
        match = ref_clean  # exact verse match: isa.55.6
        where_clause = "verse_id = ?"
    else:
        match = f"{ref_clean}.%"  # chapter match: isa.55.%
        where_clause = "verse_id LIKE ?"

    rows = conn.execute(f"""
        SELECT id, verse_id, marker, word_index, context_word, category, body_html, reference_data
        FROM footnotes
        WHERE {where_clause}
        ORDER BY verse_id, word_index
    """, (match,)).fetchall()

    if not rows:
        conn.close()
        return {"ok": True, "data": {"ref": ref_clean, "footnotes": [], "total": 0}}

    footnotes = []
    for r in rows:
        ref_data = {}
        try:
            ref_data = _json.loads(r["reference_data"]) if r["reference_data"] else {}
        except (_json.JSONDecodeError, TypeError):
            pass
        fn = {
            "id": r["id"],
            "verse_id": r["verse_id"],
            "marker": r["marker"],
            "word_index": r["word_index"],
            "context_word": r["context_word"],
            "category": r["category"],
            "body_html": r["body_html"],
            "references": ref_data if isinstance(ref_data, list) else [],
        }
        footnotes.append(fn)

    conn.close()
    return {"ok": True, "data": {
        "ref": ref_clean,
        "footnotes": footnotes,
        "total": len(footnotes),
    }}


# ─── TSK Cross-References (Treasury of Scripture Knowledge) ───


@app.get("/api/v1/tsk-crossrefs/{ref:path}")
def get_tsk_crossrefs(ref: str):
    """Get Treasury of Scripture Knowledge cross-references for a verse or chapter.

    /api/v1/tsk-crossrefs/isa.55.6     → TSK refs for Isa 55:6
    /api/v1/tsk-crossrefs/isa.55       → All TSK refs in Isa 55
    """
    ref_clean = ref.strip("/")
    conn = get_db()

    if ref_clean.count(".") >= 2:
        # Verse-level: isa.55.6
        rows = conn.execute("""
            SELECT c.target_verse, c.type, c.confidence
            FROM connections c
            WHERE c.source_verse = ? AND c.discovered_by = 'tsk'
            ORDER BY c.confidence DESC
        """, (ref_clean,)).fetchall()
        refs = [{
            "source_verse": ref_clean,
            "target_verse": r["target_verse"],
            "type": r["type"],
            "confidence": r["confidence"],
        } for r in rows]
    else:
        # Chapter-level: isa.55
        prefix = f"{ref_clean}.%"
        rows = conn.execute("""
            SELECT c.source_verse, c.target_verse, c.type, c.confidence
            FROM connections c
            WHERE c.source_verse LIKE ? AND c.discovered_by = 'tsk'
            ORDER BY c.source_verse, c.confidence DESC
        """, (prefix,)).fetchall()
        refs = [{
            "source_verse": r["source_verse"],
            "target_verse": r["target_verse"],
            "type": r["type"],
            "confidence": r["confidence"],
        } for r in rows]

    conn.close()
    return {"ok": True, "data": {
        "ref": ref_clean,
        "cross_references": refs,
        "total": len(refs),
    }}


# ─── Genealogy ───

@app.get("/api/v1/genealogy/{person}")
def genealogy(person: str):
    """Get genealogical connections for a person entity."""
    conn = get_db()
    
    # Find verse IDs for this person
    verses = conn.execute("""
        SELECT ve.verse_id
        FROM verse_entities ve
        JOIN entity_links e ON e.entity_id = ve.entity_id
        WHERE e.english_name LIKE ? AND ve.relationship_type = 'mentions'
        ORDER BY ve.verse_id
    """, (f'%{person}%',)).fetchall()
    
    if not verses:
        # Try searching by entity_id directly
        verses = conn.execute("""
            SELECT ve.verse_id
            FROM verse_entities ve
            WHERE ve.entity_id LIKE ? AND ve.relationship_type = 'mentions'
            ORDER BY ve.verse_id
        """, (f'%{person}%',)).fetchall()
    
    verse_ids = [v[0] for v in verses]
    
    # Get connections between these verses
    connections = []
    if len(verse_ids) >= 2:
        for i in range(len(verse_ids)):
            for j in range(i + 1, len(verse_ids)):
                row = conn.execute("""
                    SELECT c.source_verse, c.target_verse, c.type, c.subtype
                    FROM connections c 
                    WHERE c.source_verse=? AND c.target_verse=?
                       OR c.source_verse=? AND c.target_verse=?
                """, (verse_ids[i], verse_ids[j], verse_ids[j], verse_ids[i])).fetchall()
                for r in row:
                    connections.append(dict(r))
    
    conn.close()
    return {
        "ok": True,
        "data": {
            "person": person,
            "verses": verse_ids[:50],
            "connections": connections[:100],
            "total_verses": len(verse_ids),
        }
    }


# ─── OT-in-NT Catalog ───

@app.get("/api/v1/ot-in-nt")
def ot_in_nt(book: str = Query("", description="Filter by NT book (e.g., 'matt', 'rom')")):
    """Get all Old Testament quotations used in the New Testament.
    
    Aggregates direct_quotation, allusion, prophetic_fulfillment, 
    and modified_quotation connections from OT→NT.
    """
    conn = get_db()
    
    query = """
        SELECT c.source_verse, c.target_verse, c.type, c.strength,
               c.confidence, c.subtype, vs.text_english as source_text,
               vt.text_english as target_text, vs.book_id as ot_book,
               vt.book_id as nt_book
        FROM connections c
        JOIN verses vs ON vs.id = c.source_verse
        JOIN verses vt ON vt.id = c.target_verse
        WHERE (c.type = 'direct_quotation' OR c.type = 'allusion'
            OR c.type = 'prophetic_fulfillment' OR c.type = 'modified_quotation')
          AND vs.has_hebrew = 1
          AND vs.has_hebrew IS NOT NULL
    """
    
    # OT books (those with Hebrew)
    ot_books_query = """
        AND vs.book_id IN ('gen','exo','lev','num','deu','josh','judg','ruth','1sam','2sam','1kgs','2kgs',
                           '1chr','2chr','ezra','neh','esth','job','psa','prov','eccl','song','isa',
                           'jer','lam','ezek','dan','hos','joel','amos','obad','jonah','mic','nah',
                           'hab','zeph','hag','zech','mal')
    """
    query += ot_books_query
    
    # Filter by NT book
    if book:
        query += " AND vt.book_id = ?"
        rows = conn.execute(query, (book,)).fetchall()
    else:
        rows = conn.execute(query).fetchall()
    
    # Group by NT book
    by_nt_book = {}
    for r in rows:
        nt = r['nt_book']
        if nt not in by_nt_book:
            by_nt_book[nt] = []
        by_nt_book[nt].append({
            'ot_verse': r['source_verse'],
            'nt_verse': r['target_verse'],
            'type': r['type'],
            'strength': r['strength'],
            'confidence': r['confidence'],
            'ot_text': (r['source_text'] or '')[:150],
            'nt_text': (r['target_text'] or '')[:150],
        })
    
    # Sort each NT book's entries by OT verse
    for nt in by_nt_book:
        by_nt_book[nt].sort(key=lambda x: x['ot_verse'])
    
    conn.close()
    return {
        "ok": True,
        "data": {
            "total": sum(len(v) for v in by_nt_book.values()),
            "by_nt_book": by_nt_book,
        }
    }


# ─── Connection Feedback ───

class ConnectionFeedback(BaseModel):
    connection_id: Optional[int] = None
    source_verse: Optional[str] = None
    target_verse: Optional[str] = None
    action: str = "confirm"  # 'confirm', 'reject', 'unclear'

@app.post("/api/v1/connections/feedback")
def connection_feedback(fb: ConnectionFeedback):
    """Submit user feedback on a connection.
    
    Confirming a connection increments its confirmation_count.
    Users can confirm, reject, or mark a connection as unclear.
    This feedback improves the quality signal over time.
    """
    conn = get_db()
    
    if fb.connection_id:
        row = conn.execute("SELECT * FROM connections WHERE id = ?", (fb.connection_id,)).fetchone()
    elif fb.source_verse and fb.target_verse:
        row = conn.execute("""
            SELECT * FROM connections 
            WHERE source_verse = ? AND target_verse = ?
            LIMIT 1
        """, (fb.source_verse, fb.target_verse)).fetchone()
    else:
        conn.close()
        return {"ok": False, "error": "Provide connection_id or source_verse+target_verse"}
    
    if not row:
        conn.close()
        return {"ok": False, "error": "Connection not found"}
    
    cid = row["id"]
    
    if fb.action == "confirm":
        conn.execute("UPDATE connections SET confirmation_count = COALESCE(confirmation_count, 0) + 1 WHERE id = ?", (cid,))
        msg = "Confirmed"
    elif fb.action == "reject":
        conn.execute("UPDATE connections SET deprecated = 1, deprecation_reason = 'user_reported', confirmation_count = COALESCE(confirmation_count, 0) - 1 WHERE id = ?", (cid,))
        msg = "Rejected"
    elif fb.action == "unclear":
        conn.execute("UPDATE connections SET quality_level = 'speculative', confirmation_count = COALESCE(confirmation_count, 0) - 1 WHERE id = ?", (cid,))
        msg = "Marked unclear"
    else:
        conn.close()
        return {"ok": False, "error": f"Unknown action: {fb.action}"}
    
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"connection_id": cid, "action": fb.action, "message": msg}}


@app.get("/api/v1/connections/{connection_id}/status")
def get_connection_status(connection_id: int):
    """Get the current status and signals for a specific connection."""
    conn = get_db()
    row = conn.execute("SELECT * FROM connections WHERE id = ?", (connection_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    result = dict(row)
    signals = rate_connection_row(result)
    result["signals"] = signals
    return {"ok": True, "data": result}


# ─── Tab State ───

UI_TABS = {}  # In-memory, resets with server. For persistence use DB.

class TabCreate(BaseModel):
    type: str = "verse"
    title: str = ""
    ref: str = ""
    query: str = ""
    parent: Optional[str] = None

@app.get("/api/v1/tabs")
def list_tabs():
    return {"ok": True, "data": {"tabs": list(UI_TABS.values())}}

@app.post("/api/v1/tabs")
def create_tab(tab: TabCreate):
    import uuid
    tid = f"tab_{uuid.uuid4().hex[:8]}"
    UI_TABS[tid] = {"id": tid, "type": tab.type, "title": tab.title, "ref": tab.ref, "query": tab.query, "parent": tab.parent}
    return {"ok": True, "data": UI_TABS[tid]}

@app.delete("/api/v1/tabs/{tab_id}")
def delete_tab(tab_id: str):
    if tab_id in UI_TABS:
        del UI_TABS[tab_id]
    return {"ok": True, "data": {"deleted": tab_id}}

@app.patch("/api/v1/tabs/{tab_id}")
def update_tab(tab_id: str, body: dict):
    if tab_id in UI_TABS:
        UI_TABS[tab_id].update(body)
    return {"ok": True, "data": UI_TABS.get(tab_id, {})}


# ─── Generic Tool Endpoint (auto-generated from TOOL_REGISTRY) ───
# Every tool registered in lib/api/__init__.py is available here.
# GET for simple args, POST for complex args (body JSON).

@app.get("/api/v1/tools/{tool_name:path}")
def call_tool_get(tool_name: str, request: Request):
    """Call any registered tool by name — auto-generated from the shared tool registry.

    Query params are passed as tool arguments. For complex tools, use POST.
    See /docs for schema-per-tool documentation (coming in next iteration).
    """
    # Strip leading/trailing slashes
    tool_name = tool_name.strip("/")
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    fn, schema, desc = TOOL_REGISTRY[tool_name]
    args = dict(request.query_params)

    # Parse types per schema
    props = schema.get("properties", {})
    typed_args = {}
    for key, val in args.items():
        if key in props:
            ptype = props[key].get("type", "string")
            try:
                if ptype == "integer":
                    typed_args[key] = int(val)
                elif ptype == "number":
                    typed_args[key] = float(val)
                elif ptype == "boolean":
                    typed_args[key] = val.lower() in ("true", "1", "yes")
                elif ptype == "array":
                    # Arrays can be passed as comma-separated or repeated params
                    if val.startswith("[") and val.endswith("]"):
                        typed_args[key] = json.loads(val)
                    else:
                        typed_args[key] = [
                            v.strip() for v in val.split(",") if v.strip()
                        ]
                else:
                    typed_args[key] = val
            except (ValueError, json.JSONDecodeError):
                typed_args[key] = val

    conn = get_db()
    try:
        result = call_tool(tool_name, conn, **typed_args)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/api/v1/tools/{tool_name:path}")
def call_tool_post(tool_name: str, body: dict):
    """Call any registered tool by name with JSON body arguments."""
    tool_name = tool_name.strip("/")
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    conn = get_db()
    try:
        result = call_tool(tool_name, conn, **body)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ─── List Available Tools ───

@app.get("/api/v1/tools")
def list_api_tools():
    """List all available tools with their schemas."""
    from lib.api import list_tools as registry_list
    return {"ok": True, "data": {"tools": registry_list(), "total": len(TOOL_REGISTRY)}}


# ─── Lexicon Endpoints ───

LEXICON_CACHE_BY_HEBREW = {}  # hebrew text → lemma, filled at startup

def _build_lexicon_cache_index():
    """Build Hebrew-text lookup from RAM cache."""
    for lemma, entry in LEXICON_CACHE.items():
        heb = entry.get("hebrew", "")
        if heb:
            LEXICON_CACHE_BY_HEBREW[heb] = lemma


@app.on_event("startup")
def _load_lexicon_cache():
    _build_lexicon_cache_index()


# ─── Wiki Endpoints ───

WIKI_CACHE = {}  # entity/id → article, loaded at startup

@app.on_event("startup")
def _load_wiki_cache():
    conn = get_db()
    rows = conn.execute("SELECT * FROM wiki_articles").fetchall()
    for r in rows:
        WIKI_CACHE[r["id"]] = dict(r)
    conn.close()
    if WIKI_CACHE:
        print(f"  {len(WIKI_CACHE)} wiki articles loaded", flush=True)


@app.get("/api/v1/wiki/{entity_id:path}")
def get_wiki_article(entity_id: str):
    """Get a wiki article about a biblical entity or concept."""
    eid = entity_id.strip("/").lower().replace(" ", "_")
    article = WIKI_CACHE.get(eid)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article not found: {eid}")
    import json
    result = dict(article)
    try:
        result["key_verses"] = json.loads(result.get("key_verses", "[]"))
    except (json.JSONDecodeError, TypeError):
        result["key_verses"] = []
    try:
        result["cross_references"] = json.loads(result.get("cross_references", "[]"))
    except (json.JSONDecodeError, TypeError):
        result["cross_references"] = []
    return {"ok": True, "data": result}


@app.get("/api/v1/wiki/browse/{type_name:path}")
def browse_wiki(type_name: str = "entity"):
    """Browse wiki articles by type (entity, concept, etc.)."""
    t = type_name.strip("/").lower()
    results = [
        {"id": a["id"], "title": a["title"], "summary": a["summary"][:100]}
        for a in WIKI_CACHE.values()
        if a["article_type"] == t
    ]
    return {"ok": True, "data": {"type": t, "articles": results, "total": len(results)}}


@app.get("/api/v1/wiki/concordance/{entity_id:path}")
def wiki_concordance(entity_id: str):
    """Get key verses for an entity from its wiki article."""
    eid = entity_id.strip("/").lower().replace(" ", "_")
    article = WIKI_CACHE.get(eid)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article not found: {eid}")
    import json
    try:
        verses = json.loads(article.get("key_verses", "[]"))
    except (json.JSONDecodeError, TypeError):
        verses = []
    return {"ok": True, "data": {"entity": eid, "verses": verses, "total": len(verses)}}


# ─── Isaiah Parallel Reader ───

# Chapter mapping: Isaiah N -> 2 Nephi N+10 for chapters 2-14
# Also: Isaiah 48-49 -> 1 Nephi 20-21
#       Isaiah 53 -> Mosiah 14-15
ISAIAH_PARALLEL_MAP = {
    # 2 Nephi 12-24 = Isaiah 2-14  (offset of +10 chapters)
    **{str(i): f"2ne.{i+10}" for i in range(2, 15)},
    # Other cross-canon Isaiah parallels
    "48": "1ne.20",
    "49": "1ne.21",
    "50": "2ne.7",
    "51": "2ne.8",
    "52": "mosiah.12",
    "53": "mosiah.14",
    # Full chapters in 2 Ne
    "2": "2ne.12", "3": "2ne.13", "4": "2ne.14", "5": "2ne.15",
    "6": "2ne.16", "7": "2ne.17", "8": "2ne.18", "9": "2ne.19",
    "10": "2ne.20", "11": "2ne.21", "12": "2ne.22", "13": "2ne.23",
    "14": "2ne.24",
}


@app.get("/api/v1/parallel/isaiah/{chapter:path}")
def isaiah_parallel(chapter: str):
    """Get Isaiah side-by-side with its Book of Mormon parallel.

    Isaiah chapter N maps to:
      2-14 -> 2 Nephi N+10
      48-49 -> 1 Nephi 20-21
      50-53 -> Mosiah/2 Nephi parallels
    """
    chap = chapter.strip("/")
    parallel_book_chapter = ISAIAH_PARALLEL_MAP.get(chap)

    conn = get_db()

    # Get OT Isaiah verses
    ot_rows = conn.execute("""
        SELECT id, chapter, verse, text_english, text_hebrew
        FROM verses
        WHERE book_id = 'isa' AND chapter = ?
        ORDER BY verse
    """, (int(chap),)).fetchall()

    # Get parallel BoM verses
    bom_rows = []
    if parallel_book_chapter:
        parts = parallel_book_chapter.split(".")
        bom_book = parts[0]
        bom_ch = int(parts[1])
        bom_rows = conn.execute("""
            SELECT id, chapter, verse, text_english
            FROM verses
            WHERE book_id = ? AND chapter = ?
            ORDER BY verse
        """, (bom_book, bom_ch)).fetchall()

    # Build verse-by-verse alignment
    parallel_verses = []
    ot_by_verse = {}
    for r in ot_rows:
        ot_by_verse[r["verse"]] = {
            "reference": f"Isaiah {chap}:{r['verse']}",
            "text": r["text_english"],
            "hebrew": r["text_hebrew"],
        }

    bom_by_verse = {}
    for r in bom_rows:
        bom_by_verse[r["verse"]] = {
            "reference": f"{bom_book}.{bom_ch}:{r['verse']}",
            "text": r["text_english"],
        }

    # Align by verse number
    all_verses = sorted(set(list(ot_by_verse.keys()) + list(bom_by_verse.keys())))
    for v in all_verses:
        entry = {"verse": v, "ot": ot_by_verse.get(v), "bom": bom_by_verse.get(v)}
        parallel_verses.append(entry)

    conn.close()
    return {"ok": True, "data": {
        "chapter": int(chap),
        "parallel": parallel_book_chapter or "no_direct_parallel",
        "total_verses": len(parallel_verses),
        "verses": parallel_verses,
    }}


# ─── Isaiah Parallelism Visualization ───


@app.get("/api/v1/parallelism/isaiah/{chapter:path}")
def isaiah_parallelism(chapter: str):
    """Get parallelism data for an Isaiah chapter.

    Returns verses with their parallelism relationships (synonymous, antithetic,
    synthetic, staircase chains) and chiastic structures for the chapter.
    """
    import json as _json

    chap = chapter.strip("/")
    conn = get_db()

    # 1. Get verses in the chapter
    verse_rows = conn.execute("""
        SELECT id, book_id, chapter, verse, text_english, text_hebrew
        FROM verses
        WHERE book_id = 'isa' AND chapter = ?
        ORDER BY verse
    """, (int(chap),)).fetchall()

    if not verse_rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Chapter not found: Isaiah {chap}")

    verse_list = [dict(r) for r in verse_rows]
    verse_ids = [v["id"] for v in verse_list]
    verse_num_to_id = {v["verse"]: v["id"] for v in verse_list}
    id_to_verse_num = {v["id"]: v["verse"] for v in verse_list}
    id_to_ref = {v["id"]: f"isa.{chap}.{v['verse']}" for v in verse_list}

    # 2. Get parallelism connections for verses in this chapter
    placeholders = ",".join("?" for _ in verse_ids)
    conn_rows = conn.execute(f"""
        SELECT c.type, c.subtype, c.confidence, c.metadata,
               c.source_verse, c.target_verse
        FROM connections c
        WHERE c.layer = 'structural'
        AND (c.type LIKE 'parallel_%' OR c.type = 'chiastic')
        AND (c.source_verse IN ({placeholders}) OR c.target_verse IN ({placeholders}))
        ORDER BY c.source_verse
    """, verse_ids + verse_ids).fetchall()

    # Build parallelism map per verse
    verse_parallelisms = {v: [] for v in verse_ids}
    for r in conn_rows:
        src = r["source_verse"]
        tgt = r["target_verse"]

        def _role(vid, paired_vid):
            return "source" if vid == src else "target"

        # Add to source verse
        if src in verse_parallelisms:
            paired_v = tgt if src == src else tgt  # always tgt
            ptype = r["type"]
            # Skip chiastic in regular parallelism list
            if ptype != "chiastic":
                verse_parallelisms[src].append({
                    "type": ptype,
                    "paired_verse": id_to_verse_num.get(tgt, 0),
                    "paired_ref": id_to_ref.get(tgt, ""),
                    "role": "source",
                    "confidence": round(r["confidence"], 2),
                    "metadata": r["metadata"],
                })

        # Add to target verse
        if tgt in verse_parallelisms and r["type"] != "chiastic":
            verse_parallelisms[tgt].append({
                "type": r["type"],
                "paired_verse": id_to_verse_num.get(src, 0),
                "paired_ref": id_to_ref.get(src, ""),
                "role": "target",
                "confidence": round(r["confidence"], 2),
                "metadata": r["metadata"],
            })

    # 3. Get staircase chains overlapping this chapter
    staircase_chains = []
    chain_rows = conn.execute("""
        SELECT p.id, p.start_verse, p.end_verse, p.confidence, p.metadata
        FROM patterns p
        WHERE p.pattern_type = 'staircase_chain'
        AND p.book_id = 'isa'
    """).fetchall()

    for r in chain_rows:
        meta = _json.loads(r["metadata"]) if r["metadata"] else {}
        chain_refs = meta.get("verse_refs", [])
        # Check if any verse in the chain is in this chapter
        chapter_refs = [ref for ref in chain_refs if ref.startswith(f"isa.{chap}.")]
        if chapter_refs:
            verse_nums = []
            for ref in chapter_refs:
                parts = ref.split(".")
                if len(parts) == 3:
                    try:
                        verse_nums.append(int(parts[2]))
                    except ValueError:
                        pass
            staircase_chains.append({
                "pattern_id": r["id"],
                "start_verse": r["start_verse"],
                "end_verse": r["end_verse"],
                "verses": verse_nums or meta.get("verse_numbers", []),
                "repeated_words": meta.get("repeated_words", []),
                "chain_length": meta.get("chain_length", 0),
                "confidence": round(r["confidence"], 2),
            })

    # 4. Get chiasms (known_chiasms) that overlap this chapter
    kc_rows = conn.execute("""
        SELECT kc.* FROM known_chiasms kc
        WHERE kc.book_id = 'isa'
    """).fetchall()

    chiasms = []
    for r in kc_rows:
        kc = dict(r)
        # Parse start/end verse to check chapter overlap
        start_ref = kc.get("start_verse", "")
        end_ref = kc.get("end_verse", "")
        start_ch = 1
        end_ch = 66
        for ref in [start_ref, end_ref]:
            if ref:
                parts = ref.split(".")
                if len(parts) >= 2:
                    try:
                        ch = int(parts[1])
                        if ref == start_ref:
                            start_ch = ch
                        if ref == end_ref:
                            end_ch = ch
                    except ValueError:
                        pass

        # Does this chiasm overlap our chapter?
        if int(chap) < start_ch or int(chap) > end_ch:
            continue

        # Parse layers_json for element labels (supporting range-based elements)
        elements = []
        chapter_section = None  # Which section this chapter falls into
        layers_raw = kc.get("layers_json")
        if layers_raw:
            try:
                layers = _json.loads(layers_raw)
                for layer in layers:
                    lv_start = layer.get("start", "") or layer.get("verse", "")
                    lv_end = layer.get("end", "") or lv_start
                    label = layer.get("letter", "?")
                    lv_info = layer.get("label", "")
                    if lv_start:
                        lv_parts = lv_start.split(".")
                        lv_end_parts = lv_end.split(".")
                        if len(lv_parts) >= 2:
                            try:
                                lch_start = int(lv_parts[1])
                                lch_end = int(lv_end_parts[1]) if len(lv_end_parts) >= 2 else lch_start
                                lvs_start = int(lv_parts[2]) if len(lv_parts) >= 3 else 1
                                lvs_end = int(lv_end_parts[2]) if len(lv_end_parts) >= 3 else 99

                                # Check if this range overlaps the current chapter
                                if lch_start <= int(chap) <= lch_end:
                                    chapter_section = {
                                        "label": label,
                                        "name": lv_info,
                                        "chapter_start": lch_start,
                                        "chapter_end": lch_end,
                                    }

                                # Add individual verse-level elements for this chapter
                                if lch_start == int(chap) == lch_end:
                                    # Single-chapter range — add as element
                                    elements.append({
                                        "label": label,
                                        "verse": lvs_start,
                                        "text_snippet": lv_info,
                                    })
                                elif lch_start == int(chap):
                                    # Start of range in this chapter
                                    elements.append({
                                        "label": label,
                                        "verse": lvs_start,
                                        "text_snippet": lv_info,
                                    })
                                elif lch_end == int(chap):
                                    # End of range in this chapter
                                    elements.append({
                                        "label": label,
                                        "verse": lvs_end,
                                        "text_snippet": lv_info,
                                    })
                                elif lch_start < int(chap) < lch_end:
                                    # Chapter is in the middle of a range
                                    elements.append({
                                        "label": label,
                                        "verse": 0,
                                        "text_snippet": lv_info or f"Section {label}",
                                    })
                            except ValueError:
                                pass
            except (_json.JSONDecodeError, TypeError):
                pass

        pivot_ref = kc.get("pivot_verse", "")
        pivot_ch = 0
        pivot_vs = 0
        if pivot_ref:
            p_parts = pivot_ref.split(".")
            if len(p_parts) >= 3:
                try:
                    pivot_ch = int(p_parts[1])
                    pivot_vs = int(p_parts[2])
                except ValueError:
                    pass
            elif len(p_parts) >= 2:
                try:
                    pivot_ch = int(p_parts[1])
                except ValueError:
                    pass

        chiasms.append({
            "chiasm_id": kc["id"],
            "scholar": kc.get("scholar", ""),
            "confidence": round(kc.get("confidence", 0.5), 2),
            "chiasm_type": kc.get("chiasm_type", ""),
            "notes": kc.get("notes", ""),
            "start_verse": start_ref,
            "end_verse": end_ref,
            "pivot_verse": pivot_ref,
            "pivot_in_chapter": pivot_ch == int(chap),
            "pivot_verse_num": pivot_vs if pivot_ch == int(chap) else None,
            "chapter_section": chapter_section,
            "elements": elements,
        })

    # 5. Build verse annotations (which chiasms each verse belongs to)
    verse_in_chiasms = {v: [] for v in verse_ids}
    for ch in chiasms:
        for el in ch["elements"]:
            vid = verse_num_to_id.get(el["verse"])
            if vid and vid in verse_in_chiasms:
                verse_in_chiasms[vid].append({
                    "chiasm_id": ch["chiasm_id"],
                    "scholar": ch["scholar"],
                    "label": el["label"],
                })

    # 6. Build response verses and unique statistics
    response_verses = []
    stats_by_type = {}
    seen_parallels = set()  # Track unique connection pairs to avoid double-counting

    for v in verse_list:
        vid = v["id"]
        parallels = verse_parallelisms.get(vid, [])
        chiasm_roles = verse_in_chiasms.get(vid, [])

        for p in parallels:
            # Deduplicate parallel pairs for statistics (type + pair key)
            pair_key = (p["type"], min(v["verse"], p["paired_verse"]),
                        max(v["verse"], p["paired_verse"]))
            if pair_key not in seen_parallels:
                seen_parallels.add(pair_key)
                stats_by_type[p["type"]] = stats_by_type.get(p["type"], 0) + 1

        # Detect intra-verse poetic lines and parallelism
        intra = detect_intra_verse(v["text_english"], v["text_hebrew"] or "")

        response_verses.append({
            "verse": v["verse"],
            "text_english": v["text_english"],
            "text_hebrew": v["text_hebrew"],
            "lines": intra["lines"],
            "intra_parallelisms": intra["parallelisms"],
            "parallelisms": parallels,
            "in_chiasms": chiasm_roles,
        })

    # Add chiasmus count to stats
    if chiasms:
        stats_by_type["chiastic"] = len(chiasms)

    total_parallels = sum(stats_by_type.values())

    conn.close()
    return {"ok": True, "data": {
        "book": "isa",
        "chapter": int(chap),
        "verses": response_verses,
        "staircase_chains": staircase_chains,
        "chiasms": chiasms,
        "statistics": {
            "total_verses": len(response_verses),
            "total_parallelisms": total_parallels,
            "total_chiasms": len(chiasms),
            "by_type": stats_by_type,
        },
    }}


@app.get("/api/v1/parallelism/isaiah/structure")
def isaiah_structure():
    """Get book-wide chiastic structure overview for Isaiah.

    Returns all known chiasms with their section ranges, labels,
    and scholar info, suitable for rendering a structure diagram.
    """
    import json as _json
    conn = get_db()

    kc_rows = conn.execute("""
        SELECT * FROM known_chiasms WHERE book_id = 'isa' ORDER BY confidence DESC
    """).fetchall()

    structures = []
    for r in kc_rows:
        kc = dict(r)
        sections = []
        layers_raw = kc.get("layers_json")
        if layers_raw:
            try:
                layers = _json.loads(layers_raw)
                for layer in layers:
                    sections.append({
                        "label": layer.get("letter", "?"),
                        "name": layer.get("label", ""),
                        "start": layer.get("start", ""),
                        "end": layer.get("end", ""),
                    })
            except (_json.JSONDecodeError, TypeError):
                pass

        structures.append({
            "id": kc["id"],
            "scholar": kc.get("scholar", ""),
            "chiasm_type": kc.get("chiasm_type", ""),
            "confidence": round(kc.get("confidence", 0.5), 2),
            "start_verse": kc.get("start_verse", ""),
            "end_verse": kc.get("end_verse", ""),
            "pivot_verse": kc.get("pivot_verse", ""),
            "notes": kc.get("notes", ""),
            "sections": sections,
        })

    conn.close()
    return {"ok": True, "data": {"structures": structures, "total": len(structures)}}


# ─── Generic Chapter Connections (any book) ───


@app.get("/api/v1/chapter/{ref:path}")
def get_chapter(ref: str):
    """Get a full chapter with connections, lines, and intra-verse parallelism.

    /api/v1/chapter/isa.55      → All data for Isaiah 55
    /api/v1/chapter/matt.5      → All data for Matthew 5
    /api/v1/chapter/gen.1       → All data for Genesis 1
    """
    import json as _json
    ref_clean = ref.strip("/")
    parts = ref_clean.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Use format: book.chapter (e.g., isa.55)")
    book_id = parts[0]
    chapter_num = int(parts[1])

    from lib.patterns.intra_verse import detect_intra_verse
    conn = get_db()

    # 1. Get verses
    verse_rows = conn.execute("""
        SELECT id, book_id, chapter, verse, text_english, text_hebrew, text_greek
        FROM verses WHERE book_id = ? AND chapter = ?
        ORDER BY verse
    """, (book_id, chapter_num)).fetchall()

    if not verse_rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Chapter not found: {ref_clean}")

    verse_list = [dict(r) for r in verse_rows]
    verse_ids = [v["id"] for v in verse_list]
    id_to_verse_num = {v["id"]: v["verse"] for v in verse_list}
    id_to_ref = {v["id"]: f"{book_id}.{chapter_num}.{v['verse']}" for v in verse_list}
    verse_num_to_id = {v["verse"]: v["id"] for v in verse_list}

    # 2. Get structural connections for verses in this chapter
    placeholders = ",".join("?" for _ in verse_ids)
    conn_rows = conn.execute(f"""
        SELECT c.type, c.subtype, c.confidence, c.metadata, c.source_verse, c.target_verse
        FROM connections c
        WHERE c.layer = 'structural'
        AND (c.type LIKE 'parallel_%' OR c.type = 'chiastic')
        AND (c.source_verse IN ({placeholders}) OR c.target_verse IN ({placeholders}))
        ORDER BY c.source_verse
    """, verse_ids + verse_ids).fetchall()

    # 3. Build parallelism map per verse
    verse_parallelisms = {v["id"]: [] for v in verse_list}
    for r in conn_rows:
        for vid in [r["source_verse"], r["target_verse"]]:
            if vid in verse_parallelisms and r["type"] != "chiastic":
                paired = r["target_verse"] if vid == r["source_verse"] else r["source_verse"]
                verse_parallelisms[vid].append({
                    "type": r["type"],
                    "paired_verse": id_to_verse_num.get(paired, 0),
                    "paired_ref": id_to_ref.get(paired, ""),
                    "role": "source" if vid == r["source_verse"] else "target",
                    "confidence": round(r["confidence"], 2),
                })

    # 4. Build response verses with intra-verse lines + parallelism
    response_verses = []
    stats_by_type = {}
    seen_parallels = set()

    for v in verse_list:
        vid = v["id"]
        parallels = verse_parallelisms.get(vid, [])

        # Intra-verse detection
        intra = detect_intra_verse(v["text_english"], v["text_hebrew"] or "")

        for p in parallels:
            pair = (p["type"], min(v["verse"], p["paired_verse"]), max(v["verse"], p["paired_verse"]))
            if pair not in seen_parallels:
                seen_parallels.add(pair)
                stats_by_type[p["type"]] = stats_by_type.get(p["type"], 0) + 1

        response_verses.append({
            "verse": v["verse"],
            "text_english": v["text_english"],
            "text_hebrew": v["text_hebrew"],
            "text_greek": v["text_greek"],
            "lines": intra["lines"],
            "intra_parallelisms": intra["parallelisms"],
            "parallelisms": parallels,
            "in_chiasms": [],
        })

    # 5. Chiastic connections (count)
    chiastic_count = sum(1 for r in conn_rows if r["type"] == "chiastic")
    if chiastic_count:
        stats_by_type["chiastic"] = chiastic_count

    conn.close()
    return {"ok": True, "data": {
        "book": book_id,
        "chapter": chapter_num,
        "verses": response_verses,
        "staircase_chains": [],
        "chiasms": [],
        "statistics": {
            "total_verses": len(response_verses),
            "total_parallelisms": sum(stats_by_type.values()),
            "total_chiasms": chiastic_count,
            "by_type": stats_by_type,
        },
    }}


# ─── Thematic Study Guides ───

THEMATIC_GUIDES = {
    "covenant": {
        "title": "Covenant Thread",
        "description": "God's covenant relationship with His people from Noah through the New Covenant",
        "connections": [
            ("gen.9.9", "Noahic Covenant — God promises never to flood the earth again"),
            ("gen.15.18", "Abrahamic Covenant — land and seed promised"),
            ("gen.17.10", "Circumcision as the sign of the covenant"),
            ("exo.19.5", "Sinai Covenant — Israel as a kingdom of priests"),
            ("exo.24.8", "Blood of the covenant ratifies the relationship"),
            ("deu.29.1", "Covenant renewal in Moab"),
            ("2sam.7.12", "Davidic Covenant — an eternal throne"),
            ("jer.31.31", "New Covenant promised — law written on the heart"),
            ("ezek.36.26", "A new heart and a new spirit"),
            ("luke.22.20", "New Covenant in Christ's blood"),
            ("heb.8.8", "The New Covenant makes the first obsolete"),
        ],
    },
    "exodus": {
        "title": "Exodus Pattern",
        "description": "The Exodus as the template for God's deliverance — repeated throughout scripture",
        "connections": [
            ("gen.12.1", "Abraham's call begins the journey pattern"),
            ("exo.3.1", "Moses called at the burning bush"),
            ("exo.12.1", "Passover — the lamb's blood delivers from death"),
            ("exo.14.21", "Red Sea crossing — deliverance through waters"),
            ("exo.16.4", "Manna — bread from heaven"),
            ("exo.17.6", "Water from the rock"),
            ("isa.43.16", "A new exodus promised"),
            ("hos.11.1", "Out of Egypt I called my son"),
            ("matt.2.15", "Jesus recapitulates the Exodus"),
            ("john.6.31", "Jesus as the true bread from heaven"),
            ("1ne.17.26", "Lehi's exodus to the promised land"),
        ],
    },
    "temple": {
        "title": "Temple / Presence of God",
        "description": "The dwelling of God with humanity — from Eden to the New Jerusalem",
        "connections": [
            ("gen.2.8", "Eden as God's garden-temple"),
            ("gen.28.17", "Bethel — the gate of heaven"),
            ("exo.25.8", "The Tabernacle — God dwells among His people"),
            ("exo.40.34", "The glory of the LORD fills the Tabernacle"),
            ("1kgs.8.10", "The glory fills Solomon's Temple"),
            ("isa.6.1", "Isaiah's vision of the LORD in the Temple"),
            ("ezek.47.1", "Water flows from the Temple"),
            ("1cor.3.16", "Believers as the temple of God"),
            ("rev.21.22", "The Lord God Almighty is the Temple"),
        ],
    },
    "temple_symbolism": {
        "title": "Temple Symbolism Deep Dive",
        "description": "Every element of the Tabernacle/Temple as a symbol of Christ, creation, and the covenant path",
        "connections": [
            ("exo.25.10", "Ark of the Covenant — the throne of God (Christ as King)"),
            ("exo.25.17", "Mercy Seat (kapporet) — the place of atonement (Christ as High Priest)"),
            ("exo.25.18", "Cherubim — guardians of God's throne (heavenly attendants)"),
            ("exo.25.23", "Table of Showbread — bread of God's presence (Christ as Bread of Life)"),
            ("exo.25.31", "Golden Lampstand (menorah) — light of God's presence (Christ as Light)"),
            ("exo.26.1", "Tabernacle curtains — the heavens stretched out (cosmic symbolism)"),
            ("exo.26.31", "The Veil — separation between God and humanity (rent in Christ)"),
            ("exo.27.1", "Bronze Altar — judgment and sacrifice (the cross)"),
            ("exo.30.1", "Altar of Incense — prayers ascending to God"),
            ("exo.30.17", "Laver — cleansing and baptism"),
            ("exo.28.15", "High Priest's breastplate — bearing the tribes before God"),
            ("lev.16.15", "Day of Atonement — the scapegoat and the sin offering"),
            ("heb.9.11", "Christ as the High Priest entering the heavenly Holy of Holies"),
            ("rev.21.22", "No temple — God's presence is everywhere"),
        ],
    },
    "shepherd": {
        "title": "Shepherd / Flock",
        "description": "The shepherd metaphor — God as Shepherd, Israel as flock, Christ as Good Shepherd",
        "connections": [
            ("psa.23.1", "The LORD is my Shepherd"),
            ("psa.80.1", "Shepherd of Israel"),
            ("isa.40.11", "He shall feed His flock like a shepherd"),
            ("jer.23.1", "Woe to the shepherds who scatter the flock"),
            ("ezek.34.11", "I myself will search for my sheep"),
            ("zech.13.7", "Smite the Shepherd"),
            ("john.10.11", "I am the good Shepherd"),
            ("1pet.5.4", "Chief Shepherd shall appear"),
        ],
    },
    "creation_new_creation": {
        "title": "Creation & New Creation",
        "description": "The biblical arc from creation to new creation",
        "connections": [
            ("gen.1.1", "In the beginning God created"),
            ("gen.1.26", "Man created in God's image"),
            ("gen.2.7", "Man formed from the dust"),
            ("gen.3.17", "The ground cursed because of sin"),
            ("isa.65.17", "New heavens and a new earth"),
            ("2cor.5.17", "If any man be in Christ, new creature"),
            ("rev.21.1", "New heaven and new earth"),
            ("rev.22.1", "River of life — Eden restored and surpassed"),
        ],
    },
}

@app.get("/api/v1/studies/thematic/{guide_id:path}")
def get_thematic_study(guide_id: str):
    """Get a thematic study guide — ordered progression of verses on a theme."""
    gid = guide_id.strip("/").lower()
    guide = THEMATIC_GUIDES.get(gid)
    if not guide:
        return {"ok": False, "error": f"Guide not found. Available: {list(THEMATIC_GUIDES.keys())}"}

    conn = get_db()
    enriched = []
    for verse_ref, explanation in guide["connections"]:
        row = conn.execute("""
            SELECT text_english, text_hebrew, text_greek
            FROM verses WHERE id = ?
        """, (verse_ref,)).fetchone()
        entry = {"reference": verse_ref, "explanation": explanation}
        if row:
            entry["text"] = row["text_english"]
            entry["has_hebrew"] = bool(row["text_hebrew"])
        enriched.append(entry)
    conn.close()

    return {"ok": True, "data": {
        "id": gid,
        "title": guide["title"],
        "description": guide["description"],
        "connections": enriched,
        "total": len(enriched),
    }}

@app.get("/api/v1/studies/thematic")
def list_thematic_studies():
    """List all available thematic study guides."""
    return {"ok": True, "data": {
        "studies": [
            {"id": k, "title": v["title"], "description": v["description"], "count": len(v["connections"])}
            for k, v in THEMATIC_GUIDES.items()
        ],
        "total": len(THEMATIC_GUIDES),
    }}


# ─── User Study Guides (JSON-first, with graph paths) ───


class CreateStudyRequest(BaseModel):
    title: str
    description: str = ""
    theme: str = ""
    seed_verse: str = ""
    created_by: str = "anonymous"
    steps: list = []

class ImportStudyRequest(BaseModel):
    json_str: str
    created_by: str = "user"

class PublishStudyRequest(BaseModel):
    author_name: str = "anonymous"
    author_id: str = ""
    forked_from: str = ""


@app.get("/api/v1/studies")
def list_study_guides(theme: str = "", limit: int = 20):
    """List all study guides."""
    conn = get_db()
    result = list_guides(conn, theme=theme or None, limit=limit)
    conn.close()
    return {"ok": True, "data": result}


@app.post("/api/v1/studies")
def create_study_guide(req: CreateStudyRequest):
    """Create a new study guide with optional initial steps."""
    conn = get_db()
    steps_data = [dict(s) for s in req.steps] if req.steps else None
    result = create_guide(conn, req.title, req.description, req.theme,
                          req.seed_verse, req.created_by, steps=steps_data)
    conn.close()
    return {"ok": True, "data": result}


# ─── Published Studies (public, immutable, shareable) — defined BEFORE {guide_id} routes ───


@app.get("/api/v1/studies/published")
def list_published_studies(limit: int = 20, offset: int = 0):
    """List all published studies, most recent first."""
    conn = get_db()
    result = study_list_published(conn, limit=limit, offset=offset)
    conn.close()
    return {"ok": True, "data": result}


@app.post("/api/v1/studies/import")
def import_study(req: ImportStudyRequest):
    """Import a study from a JSON string."""
    conn = get_db()
    try:
        result = study_import_json(conn, req.json_str, created_by=req.created_by)
        conn.close()
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}



@app.post("/api/v1/studies/published/{slug}/fork")
def fork_published_study(slug: str, created_by: str = "user"):
    """Fork a published study into a new mutable study guide."""
    conn = get_db()
    result = study_fork(conn, slug, created_by=created_by)
    conn.close()
    return {"ok": True, "data": result}


# These use path() suffix to avoid conflicting with "published" path component
@app.api_route("/api/v1/studies/published/{slug}.json", methods=["GET"])
def download_published_study_json(slug: str):
    """Download a published study as JSON. Slug must not have .json extension."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    from fastapi.responses import Response
    import json
    return Response(content=json.dumps(result, indent=2, ensure_ascii=False),
                    media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.json"'})


@app.api_route("/api/v1/studies/published/{slug}.html", methods=["GET"])
def download_published_study_html(slug: str):
    """Download a published study as self-contained HTML. Slug must not have .html extension."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    from lib.api.study import _render_html
    html = _render_html(result)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.get("/api/v1/studies/published/{slug}")
def get_published_study(slug: str):
    """Get a published study by its slug."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    return {"ok": True, "data": result}


# ─── Parameterized study guide routes (keep after static routes) ───


@app.get("/api/v1/studies/{guide_id}")
def get_study_guide(guide_id: int):
    """Get a study guide with enriched steps and graph paths."""
    conn = get_db()
    result = get_guide(conn, guide_id)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    return {"ok": True, "data": result}


@app.get("/api/v1/studies/{guide_id}/export.json")
def export_study_json(guide_id: int):
    """Export a study guide as JSON with full graph paths."""
    conn = get_db()
    js = study_export_json(conn, guide_id)
    conn.close()
    if not js:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    from fastapi.responses import Response
    return Response(content=js, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="study-{guide_id}.json"'})


@app.get("/api/v1/studies/{guide_id}/export.html")
def export_study_html(guide_id: int):
    """Export a study guide as a self-contained HTML page."""
    conn = get_db()
    html = study_export_html(conn, guide_id)
    conn.close()
    if not html:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.post("/api/v1/studies/{guide_id}/publish")
def publish_study_guide(guide_id: int, req: PublishStudyRequest = None):
    """Publish a study as an immutable snapshot with a shareable URL."""
    conn = get_db()
    kw = {"author_name": req.author_name, "author_id": req.author_id} if req else {}
    if req and req.forked_from:
        kw["forked_from"] = req.forked_from
    result = study_publish(conn, guide_id, **kw)
    conn.close()
    return {"ok": True, "data": result}


class UpdateStudyRequest(BaseModel):
    title: str = ""
    description: str = ""
    theme: str = ""
    seed_verse: str = ""

class AddStepRequest(BaseModel):
    step_number: int
    verse_id: str
    title: str = ""
    explanation: str = ""
    connection_from: str = ""
    connection_type: str = ""
    connection_layer: str = ""

class BulkStepsRequest(BaseModel):
    steps: list


@app.patch("/api/v1/studies/{guide_id}")
def update_study_metadata(guide_id: int, req: UpdateStudyRequest):
    """Update study guide metadata."""
    conn = get_db()
    kw = {k: v for k, v in req.dict().items() if v}
    result = study_update(conn, guide_id, **kw)
    conn.close()
    return {"ok": True, "data": result}


@app.post("/api/v1/studies/{guide_id}/steps")
def add_study_step(guide_id: int, req: AddStepRequest):
    """Add a step to a study guide."""
    conn = get_db()
    result = study_add_step(conn, guide_id, req.step_number, req.verse_id,
                            title=req.title, explanation=req.explanation,
                            connection_from=req.connection_from,
                            connection_type=req.connection_type,
                            connection_layer=req.connection_layer)
    conn.close()
    return {"ok": True, "data": result}


@app.delete("/api/v1/studies/{guide_id}/steps/{step_number}")
def delete_study_step(guide_id: int, step_number: int):
    """Remove a step from a study guide and re-number remaining steps."""
    conn = get_db()
    result = study_remove_step(conn, guide_id, step_number)
    conn.close()
    return {"ok": True, "data": result}


@app.put("/api/v1/studies/{guide_id}/steps")
def bulk_update_study_steps(guide_id: int, req: BulkStepsRequest):
    """Replace all steps of a study guide (deletes existing, inserts new)."""
    conn = get_db()
    result = study_bulk_update(conn, guide_id, req.steps)
    conn.close()
    return {"ok": True, "data": result}


# ─── Read-Along (audio + word timestamps) ───

# Audio sources available
AUDIO_SOURCES = ["schmueloff", "tts"]

@app.get("/api/v1/read-along/{verse_id:path}")
def get_read_along_data(verse_id: str):
    """Get read-along data for a verse: audio URL + word timestamps.

    Returns the verse text, word-by-word timestamps, and an audio URL for playback.
    The frontend highlights each word as the audio plays.

    Example:
      GET /api/v1/read-along/gen.1.1
      → {
          "verse": "gen.1.1",
          "text_hebrew": "בְּרֵאשִׁית ...",
          "text_english": "In the beginning ...",
          "audio_url": "/api/v1/audio/play/gen.1.1",
          "word_timestamps": [
            {"word": "בְּרֵאשִׁית", "start": 0.0, "end": 1.2},
            ...
          ],
          "source": "schmueloff"
        }
    """
    import re
    vid = verse_id.strip("/").replace(":", ".").replace(" ", ".").lower()
    m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', vid)
    if m:
        vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"
    
    conn = get_db()
    
    # Get verse text
    verse = conn.execute("""
        SELECT text_hebrew, text_english, text_greek, book_id, chapter, verse
        FROM verses WHERE id = ?
    """, (vid,)).fetchone()
    
    if not verse:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Verse not found: {vid}")
    
    # Get word timestamps from DB
    ts_row = conn.execute("""
        SELECT start_sec, end_sec, word_timestamps, source_file
        FROM audio_timestamps WHERE verse_id = ?
    """, (vid,)).fetchone()
    
    # Determine audio source and URL
    audio_source = "schmueloff" if ts_row else "tts"
    audio_url = f"/api/v1/audio/play/{vid}"
    
    word_ts = []
    if ts_row:
        try:
            word_ts = json.loads(ts_row["word_timestamps"])
        except (json.JSONDecodeError, TypeError):
            word_ts = []
    
    # Also get the full audio file URL for the raw book recording
    raw_audio_url = None
    if ts_row and ts_row["source_file"]:
        raw_audio_url = f"/api/v1/audio/play-raw/{ts_row['source_file']}?start={ts_row['start_sec']}&end={ts_row['end_sec']}"
    
    result = {
        "verse": vid,
        "text_hebrew": verse["text_hebrew"],
        "text_english": verse["text_english"],
        "text_greek": verse["text_greek"],
        "audio_url": audio_url,
        "word_timestamps": word_ts,
        "audio_source": audio_source,
    }
    
    if ts_row:
        result["segment_start"] = ts_row["start_sec"]
        result["segment_end"] = ts_row["end_sec"]
        result["raw_audio_url"] = raw_audio_url
    
    conn.close()
    return {"ok": True, "data": result}


import subprocess, os as audio_os

RAW_AUDIO_DIR = Path(__file__).parent.parent / "data" / "audio" / "raw"

@app.get("/api/v1/audio/play-raw/{filename:path}")
def play_raw_audio_segment(filename: str, start: float = 0.0, end: float = 30.0):
    """Stream a segment from a raw audio file (e.g. book-level recording).

    Use for the read-along: streams a portion of the full Genesis recording
    corresponding to a specific verse.
    """
    safe_name = audio_os.path.basename(filename)
    audio_file = RAW_AUDIO_DIR / safe_name
    
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail=f"Raw audio not found: {safe_name}")
    
    # Use ffmpeg to extract the segment and pipe it as WAV
    from fastapi.responses import StreamingResponse
    import io
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", str(audio_file),
        "-f", "wav",
        "-acodec", "pcm_s16le",
        "-ar", "24000",
        "-ac", "1",
        "pipe:1"
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        return StreamingResponse(
            io.BytesIO(proc.stdout),
            media_type="audio/wav",
            headers={"Content-Disposition": f"inline; filename=\"{safe_name}_{start:.0f}_{end:.0f}.wav\""}
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Audio extraction timed out")

@app.get("/api/v1/audio/{word}")
def get_audio_pronunciation(word: str, lemma: str = ""):
    """Get pronunciation data for a Hebrew word.

    Returns the word with its transliteration, gematria, definition,
    and a link to the cached audio file if available.
    No Strong's number prefix — just the word, clean.
    """
    import re, json as j
    conn = get_db()

    clean_word = word.strip()

    row = conn.execute("""
        SELECT word_hebrew, word_english, transliteration, lemma, verse_id
        FROM gematria g
        LEFT JOIN lexicon l ON l.lemma LIKE '%' || g.lemma || '%'
        WHERE g.word_hebrew LIKE ? OR g.word_english LIKE ?
        LIMIT 1
    """, (f"%{clean_word}%", f"%{clean_word}%")).fetchone()

    result = {"word": word}

    if row:
        heb = row["word_hebrew"]
        eng = row["word_english"]
        trans = row["transliteration"]

        if row["transliteration"]:
            result["transliteration"] = row["transliteration"]
        else:
            plain = re.sub(r'[\u05B0-\u05C7]', '', heb)
            result["transliteration"] = plain

        result["hebrew"] = heb
        result["english_gloss"] = eng
        result["lemma"] = row["lemma"]

        gem = conn.execute("""
            SELECT value_standard, value_ordinal, value_reduced
            FROM gematria WHERE word_hebrew = ? LIMIT 1
        """, (heb,)).fetchone()
        if gem:
            result["gematria"] = {
                "standard": gem["value_standard"],
                "ordinal": gem["value_ordinal"],
                "reduced": gem["value_reduced"],
            }

        if row["lemma"]:
            lex = conn.execute("""
                SELECT definition, part_of_speech, root_letters
                FROM lexicon WHERE lemma LIKE ? LIMIT 1
            """, (f"%{row['lemma']}%",)).fetchone()
            if lex and lex["definition"]:
                result["definition"] = lex["definition"]
                result["part_of_speech"] = lex["part_of_speech"]
                result["root"] = lex["root_letters"]

        # Check for cached audio
        import os
        verse_id = row["verse_id"]
        if verse_id:
            audio_path = f"data/audio/verses/{verse_id}.wav"
            if os.path.exists(audio_path):
                result["audio_url"] = f"/api/v1/audio/play/{verse_id}"
                result["audio_available"] = True

    conn.close()
    return {"ok": True, "data": result}


AUDIO_DIR = Path(__file__).parent.parent / "data" / "audio" / "verses"

@app.get("/api/v1/audio/play/{verse_id:path}")
def play_verse_audio(verse_id: str):
    """Stream cached Hebrew audio for a verse or word."""
    from fastapi.responses import FileResponse
    
    vid = verse_id.strip("/")
    
    # Try verse audio
    audio_file = AUDIO_DIR / f"{vid}.wav"
    if not audio_file.exists():
        # Try without .wav
        audio_file = AUDIO_DIR / vid
        if not audio_file.exists() or not str(audio_file).endswith('.wav'):
            raise HTTPException(status_code=404, detail=f"Audio not found: {vid}")
    
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail=f"Audio not found: {vid}")
    
    return FileResponse(str(audio_file), media_type="audio/wav", filename=f"{vid}.wav")


# ─── Forum System ───

@app.get("/api/v1/forum/topics")
def list_forum_topics(category: str = ""):
    """List forum topics, optionally filtered by category."""
    conn = get_db()
    query = "SELECT * FROM forum_topics"
    params = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY post_count DESC, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"ok": True, "data": {
        "topics": [dict(r) for r in rows],
        "total": len(rows),
    }}


@app.get("/api/v1/forum/topics/{topic_id:path}")
def get_forum_topic(topic_id: str):
    """Get a forum topic with its posts."""
    conn = get_db()
    topic = conn.execute("SELECT * FROM forum_topics WHERE id = ? OR slug = ?",
                        (topic_id, topic_id)).fetchone()
    if not topic:
        conn.close()
        return {"ok": False, "error": "Topic not found"}

    posts = conn.execute("""
        SELECT * FROM forum_posts WHERE topic_id = ? ORDER BY created_at ASC
    """, (topic["id"],)).fetchall()

    conn.close()
    return {"ok": True, "data": {"topic": dict(topic), "posts": [dict(p) for p in posts]}}


class ForumPostCreate(BaseModel):
    topic_id: int
    content: str
    author: str = "anonymous"
    parent_id: Optional[int] = None

@app.post("/api/v1/forum/posts")
def create_forum_post(post: ForumPostCreate):
    """Create a new post in a forum topic."""
    if not post.content.strip():
        return {"ok": False, "error": "Content is required"}
    conn = get_db()
    conn.execute("""
        INSERT INTO forum_posts (topic_id, author, content, parent_id)
        VALUES (?, ?, ?, ?)
    """, (post.topic_id, post.author, post.content.strip(), post.parent_id))
    conn.execute("UPDATE forum_topics SET post_count = post_count + 1 WHERE id = ?", (post.topic_id,))
    conn.commit()
    post_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"ok": True, "data": {"post_id": post_id, "message": "Post created"}}


# ─── Verse Annotations (per-verse comments) ───

@app.get("/api/v1/verses/{ref:path}/annotations")
def get_verse_annotations(ref: str):
    """Get comments/annotations on a specific verse."""
    ref = ref.replace(":", ".").replace(" ", ".").lower()
    import re
    m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', ref)
    if m:
        vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"
    else:
        vid = ref

    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM verse_annotations
        WHERE verse_id = ? AND parent_id IS NULL
        ORDER BY created_at DESC
    """, (vid,)).fetchall()

    # Get replies
    result = []
    for r in rows:
        entry = dict(r)
        replies = conn.execute("""
            SELECT * FROM verse_annotations WHERE parent_id = ? ORDER BY created_at ASC
        """, (r["id"],)).fetchall()
        entry["replies"] = [dict(re) for re in replies]
        result.append(entry)

    conn.close()
    return {"ok": True, "data": {"verse": vid, "annotations": result, "total": len(result)}}


class AnnotationCreate(BaseModel):
    verse_id: str
    content: str
    user_id: str = "anonymous"
    parent_id: Optional[int] = None

@app.post("/api/v1/verses/annotations")
def create_annotation(ann: AnnotationCreate):
    """Add a comment/annotation to a verse."""
    if not ann.content.strip():
        return {"ok": False, "error": "Content is required"}
    conn = get_db()
    conn.execute("""
        INSERT INTO verse_annotations (verse_id, user_id, content, parent_id)
        VALUES (?, ?, ?, ?)
    """, (ann.verse_id, ann.user_id, ann.content.strip(), ann.parent_id))
    conn.commit()
    ann_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"ok": True, "data": {"annotation_id": ann_id, "message": "Annotation created"}}


# ─── Conversation / Chat Sessions ───

class ConversationCreate(BaseModel):
    title: str = ""
    theme: str = ""
    created_by: str = "anonymous"

class MessageCreate(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Optional[dict] = {}

class SessionUpdate(BaseModel):
    title: Optional[str] = None
    is_starred: Optional[bool] = None

class ConnectionPromote(BaseModel):
    layer: str = "intertextual"
    type_name: str = "parallel"
    subtype: str = ""
    strength: float = 0.5
    confidence: float = 0.5
    discovered_by: str = "conversation"

class ManualConnection(BaseModel):
    source_verse: str
    target_verse: str
    relationship: str = ""
    connection_type: str = "discovered"
    confidence: float = 0.5
    description: str = ""

@app.get("/api/v1/conversations")
def list_conversations(page: int = 1, per_page: int = 20, starred: Optional[bool] = None, search: str = ""):
    """List conversation sessions, paginated."""
    conn = get_db()
    result = list_sessions(conn, page=page, per_page=per_page, starred=starred, search=search)
    conn.close()
    return {"ok": True, "data": result}

@app.post("/api/v1/conversations")
def create_conversation(body: ConversationCreate):
    """Create a new conversation session."""
    conn = get_db()
    session = create_session(conn, title=body.title, theme=body.theme, created_by=body.created_by)
    conn.close()
    return {"ok": True, "data": session}

@app.get("/api/v1/conversations/{session_id}")
def get_conversation(session_id: str):
    """Get a conversation session with all messages, refs, and connections."""
    conn = get_db()
    session = get_session(conn, session_id)
    conn.close()
    if not session:
        return {"ok": False, "error": "Session not found"}
    return {"ok": True, "data": session}

@app.patch("/api/v1/conversations/{session_id}")
def update_conversation(session_id: str, body: SessionUpdate):
    """Update session title or starred status."""
    conn = get_db()
    session = update_session(conn, session_id, title=body.title, is_starred=body.is_starred)
    conn.close()
    return {"ok": True, "data": session}

@app.delete("/api/v1/conversations/{session_id}")
def delete_conversation(session_id: str):
    """Delete a conversation session."""
    conn = get_db()
    result = delete_session(conn, session_id)
    conn.close()
    return {"ok": True, "data": result}

@app.post("/api/v1/conversations/{session_id}/messages")
def add_conversation_message(session_id: str, body: MessageCreate):
    """Add a message to a conversation. Auto-extracts verse refs and detects connections."""
    if not body.content.strip():
        return {"ok": False, "error": "Content is required"}
    conn = get_db()
    # Verify session exists
    session = conn.execute(
        "SELECT id FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return {"ok": False, "error": "Session not found"}
    result = add_message(conn, session_id, body.role, body.content, metadata=body.metadata)
    conn.close()
    return {"ok": True, "data": result}

@app.post("/api/v1/conversations/{session_id}/messages/batch")
def add_conversation_messages_batch(session_id: str, body: list[MessageCreate]):
    """Add multiple messages at once (for page reload recovery)."""
    conn = get_db()
    session = conn.execute(
        "SELECT id FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return {"ok": False, "error": "Session not found"}
    results = []
    for msg in body:
        r = add_message(conn, session_id, msg.role, msg.content, metadata=msg.metadata)
        results.append(r)
    conn.close()
    return {"ok": True, "data": {"messages": results, "count": len(results)}}

@app.get("/api/v1/conversations/{session_id}/connections")
def get_conversation_connections(session_id: str, connection_type: Optional[str] = None):
    """List connections discovered/retrieved in a conversation."""
    conn = get_db()
    result = list_connections(conn, session_id, connection_type=connection_type)
    conn.close()
    return {"ok": True, "data": {"connections": result, "total": len(result)}}

@app.post("/api/v1/conversations/{session_id}/connections")
def add_conversation_connection(session_id: str, body: ManualConnection):
    """Manually add a connection to a session."""
    conn = get_db()
    add_connection(
        conn, session_id,
        source_verse=body.source_verse,
        target_verse=body.target_verse,
        relationship=body.relationship,
        connection_type=body.connection_type,
        confidence=body.confidence,
        description=body.description,
    )
    conn.close()
    return {"ok": True, "data": {"message": "Connection added"}}

@app.post("/api/v1/conversations/{session_id}/connections/{connection_id}/promote")
def promote_conversation_connection(session_id: str, connection_id: int, body: ConnectionPromote):
    """Promote a conversation connection to the main connection graph."""
    conn = get_db()
    result = promote_connection(
        conn, connection_id,
        layer=body.layer,
        type_name=body.type_name,
        subtype=body.subtype,
        strength=body.strength,
        confidence=body.confidence,
        discovered_by=body.discovered_by,
    )
    conn.close()
    if result.get("ok"):
        return {"ok": True, "data": result}
    return {"ok": False, "error": result.get("error", "Promotion failed")}


# ─── Health Check ───

@app.get("/api/v1/health")
def health():
    return {
        "ok": True,
        "data": {
            "status": "running",
            "connections": 478323,
            "guides": 41126,
            "tools": len(TOOL_REGISTRY),
            "lexicon": len(LEXICON_CACHE),
            "wiki": len(WIKI_CACHE),
            "ratings_available": True,
            "rating_tiers": ["verified(5★)", "strong(4★)", "probable(3★)", "suggested(2★)", "pattern(1★)"],
            "star_scale": "1-5",
            "rating_system": "Multi-signal: discovery_method + connection_type + reasoning + confidence + confirmations",
            "api_filtering": "Filter by: layer, min_quality, discovered_by, min_confidence, show_signals",
            "user_feedback": "POST /api/v1/connections/feedback — confirm, reject, or unclear",
        }
    }


# ─── Debug Logging (file-backed — survives server restarts) ───

import os as _os

DEBUG_LOG_PATH = _os.environ.get("SCRIPTURE_DEBUG_LOG", "/tmp/scripture-debug.jsonl")
DEBUG_MAX_ENTRIES = 500


def _read_debug_log():
    """Read all entries from the debug log file."""
    if not _os.path.exists(DEBUG_LOG_PATH):
        return []
    try:
        with open(DEBUG_LOG_PATH) as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception:
        return []


def _append_debug_log(entries):
    """Append entries to the debug log file, trimming to max."""
    existing = _read_debug_log()
    all_entries = existing + entries
    if len(all_entries) > DEBUG_MAX_ENTRIES:
        all_entries = all_entries[-DEBUG_MAX_ENTRIES:]
    try:
        with open(DEBUG_LOG_PATH, "w") as f:
            for entry in all_entries:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _clear_debug_log():
    """Clear the debug log file."""
    try:
        if _os.path.exists(DEBUG_LOG_PATH):
            _os.remove(DEBUG_LOG_PATH)
    except Exception:
        pass


@app.post("/api/v1/debug/log")
async def debug_log(request: Request):
    """Receive client-side error logs from the frontend (single or batch)."""
    body = await request.json()
    entries_raw = body if isinstance(body, list) else [body]
    entries = []
    for e in entries_raw:
        entries.append({
            "level": str(e.get("level", "log"))[:20],
            "message": str(e.get("message", ""))[:500],
            "stack": str(e.get("stack", ""))[:2000],
            "url": str(e.get("url", ""))[:500],
            "timestamp": str(e.get("timestamp", ""))[:30],
        })
    _append_debug_log(entries)
    return {"ok": True, "recorded": len(entries)}


@app.get("/api/v1/debug")
def debug_info():
    """Server diagnostics — I can curl this to check health + logs."""
    db_ok = False
    verse_count = 0
    try:
        conn = get_db()
        verse_count = conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()["c"]
        conn.close()
        db_ok = True
    except Exception:
        pass

    logs = _read_debug_log()
    return {
        "ok": True,
        "data": {
            "server": "running",
            "db_connected": db_ok,
            "verses_in_db": verse_count,
            "cache": {
                "verses": len(VERSE_CACHE),
                "guides": len(GUIDE_CACHE),
                "lexicon": len(LEXICON_CACHE),
                "entities": len(ENTITY_CACHE),
                "wiki": len(WIKI_CACHE),
            },
            "log_count": len(logs),
            "log_file": DEBUG_LOG_PATH,
        },
    }


@app.get("/api/v1/debug/log")
def debug_log_list(clear: bool = False):
    """Read client-side error logs (survives server restarts)."""
    logs = _read_debug_log()
    if clear:
        _clear_debug_log()
    return {"ok": True, "data": {"count": len(logs), "logs": logs}}


# ─── Book Navigation ───


@app.get("/api/v1/books")
def list_books():
    """Get all books grouped by work, for navigation."""
    conn = get_db()
    works = conn.execute("SELECT id, title FROM works ORDER BY id").fetchall()
    works_list = []
    for w in works:
        books = conn.execute("""
            SELECT id, title, position FROM books
            WHERE work_id = ? ORDER BY position
        """, (w["id"],)).fetchall()
        works_list.append({
            "id": w["id"],
            "title": w["title"],
            "books": [{"id": b["id"], "title": b["title"], "position": b["position"]} for b in books],
        })
    conn.close()
    return {"ok": True, "data": {"works": works_list}}


# ─── Agent Control (LLM-driven frontend testing) ───

import threading as _threading
_agent_lock = _threading.Lock()
_agent_actions = []    # list of {id, action, ...}
_agent_next_id = 0
_agent_state = {}       # last reported frontend state
_agent_file = _os.environ.get("SCRIPTURE_AGENT_STATE", "/tmp/scripture-agent.json")
_MAX_QUEUE = 100


def _save_state():
    """Persist agent state to disk so I can read it."""
    try:
        with open(_agent_file, "w") as f:
            json.dump({"actions": _agent_actions[-20:], "state": _agent_state}, f)
    except Exception:
        pass


@app.post("/api/v1/agent/action")
async def agent_enqueue(request: Request):
    """Queue an action for the frontend to execute."""
    global _agent_next_id
    body = await request.json()
    with _agent_lock:
        entry = {"id": _agent_next_id, "ts": time.time(), **body}
        _agent_actions.append(entry)
        _agent_next_id += 1
        if len(_agent_actions) > _MAX_QUEUE:
            _agent_actions[:50] = []
    return {"ok": True, "action_id": entry["id"]}


@app.get("/api/v1/agent/actions")
def agent_poll(after: int = -1):
    """Frontend polls this for pending actions since the last seen id."""
    with _agent_lock:
        new = [a for a in _agent_actions if a["id"] > after]
    return {"ok": True, "data": {
        "actions": new,
        "cursor": _agent_next_id - 1,
        "pending": len(new),
    }}


@app.post("/api/v1/agent/state")
async def agent_report_state(request: Request):
    """Frontend reports its current state after executing actions."""
    global _agent_state
    body = await request.json()
    _agent_state = body
    _save_state()
    return {"ok": True}


@app.get("/api/v1/agent/state")
def agent_read_state():
    """I read this to see what the frontend looks like."""
    return {"ok": True, "data": _agent_state}


@app.post("/api/v1/agent/clear")
def agent_clear():
    """Clear the action queue and state."""
    with _agent_lock:
        _agent_actions.clear()
        _agent_state.clear()
    try:
        if _os.path.exists(_agent_file):
            _os.remove(_agent_file)
    except Exception:
        pass
    return {"ok": True}


# ─── LLM Chat Proxy with Function Calling (DeepSeek) ───

DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# Reusable HTTP client for DeepSeek API calls (avoids creating a new connection each time)
import httpx
_http_client = httpx.AsyncClient(timeout=600.0)  # 10 min — DeepSeek thinking mode can take 8+ min

# Pricing per 1M tokens (deepseek-v4-flash)
PRICING = {
    "input": 0.14,
    "output": 0.28,
    "cache_hit": 0.07,
}

# Load system prompt from CHAT_AGENTS.md
_CHAT_AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHAT_AGENTS.md")
CHAT_SYSTEM_PROMPT = ""
if os.path.exists(_CHAT_AGENTS_PATH):
    with open(_CHAT_AGENTS_PATH) as f:
        CHAT_SYSTEM_PROMPT = f.read()

# --- Tool definitions ---

# Maps tool names to their function-calling schema for DeepSeek/OpenAI
# Subset of the 42 engine tools that are most useful for scripture study
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "scripture_verse",
            "description": "Look up a verse with text, gematria, connections, and quality info. Works for all 8 works: OT (gen, exo, isa), NT (matt, john, rev), BoM (1ne, alma, 3ne), D&C (dc1-dc138), PGP (moses, abraham), DSS (1QS, 1QHa, 11Q19, CD, 1Qisaa), Apocrypha (wis, sir, tob, 1ma), Pseudepigrapha (1en, jub, ascis, barn, odessol)",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID (gen, exo, isa, matt, 1ne, 1QS, 1en, wis, etc.)"},
                    "chapter": {"type": "integer"},
                    "verse": {"type": "integer"},
                    "version": {"type": "string", "description": "Bible version (WEB, KJV, etc.)"},
                },
                "required": ["book", "chapter", "verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_search",
            "description": "Search for verses by keyword in English text across all 8 works (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "book": {"type": "string", "description": "Optional book filter (e.g., '1en' for 1 Enoch, '1QS' for Community Rule, 'jub' for Jubilees)"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_passage_guide",
            "description": "Get pre-computed passage guide — all connections, gematria, and quality distribution",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_gematria",
            "description": "Compute gematria for a Hebrew word or look up verses by gematria value",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "Hebrew word (e.g., יהוה)"},
                    "value": {"type": "integer", "description": "Look up verses with this gematria value"},
                    "system": {"type": "string", "enum": ["standard", "ordinal", "reduced"], "default": "standard"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_connections",
            "description": "Get all connections for a verse, with layer and quality filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "layer": {"type": "string", "description": "Filter by connection layer"},
                    "min_quality": {"type": "string", "description": "Minimum quality level (pattern, suggested, verified, scholarly)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_intertext",
            "description": "Get intertextual connections — quotations, allusions, echoes",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_pardes",
            "description": "Show connections grouped by PaRDeS level (Pshat, Remez, Drash, Sod)",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                    "level": {"type": "string", "enum": ["pshat", "remez", "drash", "sod"], "description": "Filter to one PaRDeS level"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sod",
            "description": "Explore hidden (Sod-level) patterns — atbash, acrostics, advanced gematria, hidden names",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse to analyze"},
                    "atbash_word": {"type": "string", "description": "Hebrew word to decode via Atbash"},
                    "acrostic_book": {"type": "string", "description": "Book ID to scan for acrostics"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_path",
            "description": "Find the shortest connection path between two verses through the typed graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Starting verse ID (gen.1.1)"},
                    "end": {"type": "string", "description": "Target verse ID"},
                    "max_depth": {"type": "integer", "default": 3, "description": "Maximum path length in hops"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_reachable",
            "description": "Find all verses reachable within N hops from a verse through the connection graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Starting verse ID"},
                    "max_depth": {"type": "integer", "default": 3},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_entities",
            "description": "Get entities (people, places, concepts) linked to a specific verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_shared_entities",
            "description": "Find other verses that share entities (people, places) with this verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_hubs",
            "description": "Find hub verses — those connecting to the most diverse other verses",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_connections": {"type": "integer", "default": 3},
                    "layer": {"type": "string", "description": "Optional layer scope"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources_by_scholar",
            "description": "Get all connections from a specific scholar by tag",
            "parameters": {
                "type": "object",
                "properties": {
                    "scholar_tag": {"type": "string", "description": "Scholar tag (e.g., barker_temple, beale_temple, heiser_council)"},
                    "scholar_name": {"type": "string", "description": "Scholar name (e.g., Margaret Barker)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_strongs",
            "description": "Look up Strong's definition for a Hebrew or Greek word",
            "parameters": {
                "type": "object",
                "properties": {
                    "lemma": {"type": "string", "description": "Strong's number (e.g., H430, G26)"},
                    "word": {"type": "string", "description": "Hebrew or Greek word text"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_interlinear",
            "description": "Get word-by-word interlinear analysis with transliteration, Strong's, morphology",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID"},
                    "chapter": {"type": "integer"},
                    "verse": {"type": "integer"},
                },
                "required": ["book", "chapter", "verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_suggest",
            "description": "Suggest an exploration path from a seed verse through the connection graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "seed_verse": {"type": "string"},
                    "theme": {"type": "string", "description": "Optional theme (e.g., angel_of_yhwh, temple, covenant)"},
                },
                "required": ["seed_verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_info",
            "description": "Get database statistics — total verses, connections per layer, quality distribution",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── Additional search & source tools ──
    {
        "type": "function",
        "function": {
            "name": "scripture_search_xlingual",
            "description": "Search across Hebrew, Greek, AND English simultaneously using entity alignment",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "language": {"type": "string", "enum": ["all", "english", "hebrew", "greek"], "default": "all"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_entity_network",
            "description": "Get all verses connected to a specific entity (person, place, or concept)",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity ID (e.g., 'person.abraham')"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_centrality",
            "description": "Find the most central (best-connected) verses in the graph by degree centrality",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Optional book ID to scope analysis"},
                    "layer": {"type": "string", "description": "Optional layer scope"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_consensus",
            "description": "Get ecumenical consensus data — which traditions engage with this verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_disagreements",
            "description": "Get interpretive disagreements — contradictory readings across traditions",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources",
            "description": "Get source provenance breakdown for a verse's connections",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources_list",
            "description": "List all scholars with connections in the graph",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_verse_text",
            "description": "Get verse text in a specific Bible version",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "version": {"type": "string", "description": "Bible version (WEB, KJV, etc.)", "default": "WEB"},
                },
                "required": ["verse"],
            },
        },
    },

    # ── Study guide tools ──
    {
        "type": "function",
        "function": {
            "name": "scripture_study_create",
            "description": "Create a study guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string", "default": ""},
                    "theme": {"type": "string", "default": ""},
                    "seed_verse": {"type": "string", "default": ""},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_add_step",
            "description": "Add a step to a study guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                    "step_number": {"type": "integer"},
                    "verse_id": {"type": "string"},
                    "title": {"type": "string", "default": ""},
                    "explanation": {"type": "string", "default": ""},
                },
                "required": ["guide_id", "step_number", "verse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_get",
            "description": "Get a study guide with all its steps",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                },
                "required": ["guide_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_list",
            "description": "List study guides, optionally filtered by theme",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },

    # ── Staging — propose new data (web UI / LLM → staging table → dev review) ──
    {
        "type": "function",
        "function": {
            "name": "scripture_stage_connection",
            "description": "Propose a new connection between two verses. Goes to staging for dev review before entering the graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_verse": {"type": "string", "description": "Source verse ID (gen.1.1)"},
                    "target_verse": {"type": "string", "description": "Target verse ID"},
                    "layer": {"type": "string", "description": "Connection layer"},
                    "type_name": {"type": "string", "description": "Connection type (direct_quotation, allusion, etc.)"},
                    "subtype": {"type": "string", "default": ""},
                    "strength": {"type": "number", "default": 0.5},
                    "confidence": {"type": "number", "default": 0.5},
                    "reasoning": {"type": "string", "default": ""},
                },
                "required": ["source_verse", "target_verse", "layer", "type_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_stage_study",
            "description": "Propose a study guide (goes to staging for dev review before publishing).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string", "default": ""},
                    "theme": {"type": "string", "default": ""},
                    "seed_verse": {"type": "string", "default": ""},
                    "steps_json": {"type": "string", "description": "JSON array of steps: [{\"step_number\":1, \"verse\":\"gen.1.1\", \"title\":\"...\", \"explanation\":\"...\"}]"},
                },
                "required": ["title"],
            },
        },
    },
]

# ── Staging tool names (recognized by the chat handler) ──
STAGING_TOOLS = {"scripture_stage_connection", "scripture_stage_study"}


def _compute_cost(usage: dict) -> dict:
    """Estimate cost from DeepSeek usage response."""
    p_in = usage.get("prompt_tokens", 0)
    p_out = usage.get("completion_tokens", 0)
    cache_hit = usage.get("prompt_cache_hit_tokens", 0)
    cost_input = p_in * PRICING["input"] / 1_000_000
    cost_output = p_out * PRICING["output"] / 1_000_000
    cost_cache = cache_hit * PRICING["cache_hit"] / 1_000_000
    return {
        "total": round(cost_input + cost_output - cost_cache, 6),
        "input": round(cost_input, 6),
        "output": round(cost_output, 6),
        "cache_saved": round(cost_cache, 6),
    }


class ChatRequest(BaseModel):
    messages: list[dict]
    model: str = DEEPSEEK_MODEL
    max_tokens: int = 4096
    temperature: float = 0.7
    tools_enabled: bool = True
    disabled_tools: list[str] = []


@app.get("/api/v1/chat/instructions")
def chat_instructions():
    """Return the AGENTS-style system prompt and tool definitions for the chat LLM."""
    return {
        "ok": True,
        "data": {
            "system_prompt": CHAT_SYSTEM_PROMPT,
            "tools": TOOL_DEFINITIONS,
            "model": DEEPSEEK_MODEL,
            "pricing": PRICING,
        },
    }


@app.post("/api/v1/chat")
async def llm_chat(body: ChatRequest):
    """Proxy chat requests to DeepSeek API with function calling support.

    If the LLM requests a tool call, the server executes it against the
    scripture engine and feeds the result back to the LLM for a final response.
    """
    if not DEEPSEEK_API_KEY:
        return {"ok": False, "error": "DEEPSEEK_API_KEY not configured"}

    import httpx
    from lib.api import call_tool, list_tools
    from lib.api.staging import stage_connection, stage_study
    from lib.db import get_db

    # Build messages with system prompt
    msgs = list(body.messages)
    if CHAT_SYSTEM_PROMPT:
        # Prepend system instruction if not already present
        if not any(m.get("role") == "system" for m in msgs):
            msgs.insert(0, {"role": "system", "content": CHAT_SYSTEM_PROMPT})

    # Context budget management
    # Total budget: 300K tokens. max_tokens capped at 128K. Compaction trigger at 200K prompt tokens.
    MAX_PROMPT_TOKENS = 200_000
    KEEP_EXCHANGES = 15  # user+assistant pairs to keep before compaction
    body.max_tokens = min(body.max_tokens, 128_000)

    def estimate_tokens(text):
        return len(text) // 4  # rough estimate: ~4 chars per token

    def apply_context_budget(message_list):
        """Trim message list to stay within budget. Strips tool traces first,
        then keeps only the last KEEP_EXCHANGES user+assistant exchanges."""
        total_est = sum(estimate_tokens(m.get("content", "") or "") for m in message_list)
        if total_est <= MAX_PROMPT_TOKENS:
            return message_list

        # 1. Strip tool traces from messages older than the last KEEP_EXCHANGES exchanges
        system = [m for m in message_list if m["role"] == "system"]
        exchanges = [m for m in message_list if m["role"] != "system"]

        # Count exchanges (user+assistant pairs)
        exchange_count = 0
        keep_from = len(exchanges)
        for i in range(len(exchanges) - 1, -1, -1):
            if exchanges[i]["role"] == "user":
                exchange_count += 1
                if exchange_count > KEEP_EXCHANGES:
                    keep_from = i
                    break

        before = exchanges[:keep_from]
        after = exchanges[keep_from:]

        # Strip tool-related messages from the 'before' portion
        cleaned_before = [m for m in before if m["role"] in ("user", "assistant") and m.get("content")]
        cleaned_all = cleaned_before + after
        total_est = sum(estimate_tokens(m.get("content", "") or "") for m in cleaned_all)

        if total_est <= MAX_PROMPT_TOKENS:
            return system + cleaned_all

        # 2. Still over budget: keep only the most recent KEEP_EXCHANGES exchanges
        if exchange_count > KEEP_EXCHANGES:
            # Take the last KEEP_EXCHANGES exchanges from the 'after' portion
            final_after = after
            if len(exchanges) > KEEP_EXCHANGES * 2:
                final_after = exchanges[-(KEEP_EXCHANGES * 2):]
            else:
                final_after = exchanges[-(KEEP_EXCHANGES * 2):]
            system.append({
                "role": "system",
                "content": "[Earlier conversation context omitted to stay within token budget.]"
            })
            return system + final_after

        return system + after

    msgs = apply_context_budget(msgs)

    # Prepare request payload (no explicit thinking flags — let DeepSeek use own defaults
    # like OpenCode does. No thinking/reasoning_effort forcing means the model naturally
    # balances its token budget between thinking and visible response.)
    payload = {
        "model": body.model,
        "messages": msgs,
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
    }
    if body.tools_enabled:
        # Filter out disabled tools
        if body.disabled_tools:
            payload["tools"] = [t for t in TOOL_DEFINITIONS
                                if t["function"]["name"] not in body.disabled_tools]
        else:
            payload["tools"] = TOOL_DEFINITIONS
        payload["tool_choice"] = "auto"

    tool_results = []
    max_tool_rounds = 15  # prevent infinite loops; 10 was too low for multi-work searches

    async def call_deepseek(req_payload):
        global _http_client
        resp = await _http_client.post(
            f"{DEEPSEEK_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=req_payload,
        )
        return resp.json()

    data = await call_deepseek(payload)

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        friendly_map = {
            400: "Invalid request format.",
            401: "API key issue — contact the repo maintainer.",
            429: "Rate limited — please wait a moment.",
            500: "DeepSeek server error. Try again.",
        }
        msg = err.get("message", str(err))
        friendly = friendly_map.get(code, "")
        return {"ok": False, "error": f"{friendly} [{msg}]" if friendly else msg}

    rounds = 0
    while data.get("choices") and rounds < max_tool_rounds:
        choice = data["choices"][0]
        msg = choice.get("message", {})

        # Check for tool calls
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            break  # No more tool calls, we have final response

        # Execute each tool call
        # First, add the assistant's tool_calls message once (DeepSeek requires this order)
        msgs.append(msg)
        conn = get_db()

        # Separate staging (write) tools from read-only tools
        staging_calls = [tc for tc in tool_calls if tc["function"]["name"] in STAGING_TOOLS]
        ro_calls = [tc for tc in tool_calls if tc["function"]["name"] not in STAGING_TOOLS]

        # Run read-only tools in parallel
        async def run_ro(tc):
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            try:
                return tc, call_tool(fn_name, conn, **fn_args)
            except Exception as e:
                return tc, {"error": str(e)}

        ro_results = []
        if ro_calls:
            ro_results = await asyncio.gather(*[run_ro(tc) for tc in ro_calls])

        # Run staging tools sequentially (they write to DB)
        staging_results = []
        for tc in staging_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            try:
                if fn_name == "scripture_stage_connection":
                    result = stage_connection(conn, submitted_by="llm", **fn_args)
                elif fn_name == "scripture_stage_study":
                    steps = json.loads(fn_args.pop("steps_json", "[]"))
                    result = stage_study(conn, steps=steps, submitted_by="llm", **fn_args)
                else:
                    result = {"error": f"Unknown staging tool: {fn_name}"}
            except Exception as e:
                result = {"error": str(e)}
            staging_results.append((tc, result))

        # Combine all results
        all_results = ro_results + staging_results
        for tc, result in all_results:

            # Truncate large results to avoid overflowing context
            result_str = json.dumps(result, default=str, ensure_ascii=False)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + '..." [truncated]'

            # Also truncate the tool_result sent to frontend (saves context bandwidth + metadata bloat)
            tool_result_data = result
            if len(json.dumps(tool_result_data, default=str, ensure_ascii=False)) > 3000:
                import copy
                trunced = copy.copy(result) if isinstance(result, dict) else result
                if isinstance(trunced, dict):
                    # Return truncated instead of the full result
                    tool_result_data = {"_truncated": True, "data_preview": result_str[:500]}
                else:
                    tool_result_data = {"_truncated": True, "data_preview": result_str[:500]}
            tool_results.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"]),
                "result": tool_result_data,
            })

            # Add tool result message (one per tool call, with matching call_id)
            msgs.append({
                "role": "tool",
                "content": result_str,
                "tool_call_id": tc["id"],
            })

        conn.close()

        # Apply budget check only when approaching the limit (saves scanning all messages)
        est = sum(len(m.get("content", "") or "") // 4 for m in msgs)
        if est > MAX_PROMPT_TOKENS * 0.8:
            msgs = apply_context_budget(msgs)

        # Call DeepSeek again with tool results
        payload["messages"] = msgs
        data = await call_deepseek(payload)

        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err))
            return {"ok": False, "error": f"DeepSeek API error: {msg}"}

        rounds += 1

    # Final response
    usage = data.get("usage", {})
    choice = data["choices"][0] if data.get("choices") else None
    if not choice:
        return {"ok": False, "error": "No response from LLM"}

    final_content = choice["message"]["content"] or choice["message"].get("reasoning_content") or ""
    final_reasoning = choice["message"].get("reasoning_content")

    # If LLM only made tool calls without summarizing, force a summary
    # Also force summary if the content is just planning text (starts with "Let me")
    is_planning = final_content.strip()[:20].lstrip().startswith("Let me")
    if (not final_content or is_planning) and tool_results:
        msgs.append({"role": "user", "content":
            "You have all the data you need from the tool calls above. "
            "Now synthesize a complete answer in natural language based on the information you found. "
            "Cite the specific verses and data you found. "
            "Use full book names like 'Genesis 1:1'. "
            "Do not list the tools you used."})
        retry = await call_deepseek({
            "model": body.model, "messages": msgs,
            "max_tokens": body.max_tokens, "temperature": body.temperature,
        })
        if retry.get("choices"):
            rc_msg = retry["choices"][0].get("message", {})
            if rc_msg.get("content") or rc_msg.get("reasoning_content"):
                final_content = rc_msg["content"] or rc_msg.get("reasoning_content") or ""
                final_reasoning = rc_msg.get("reasoning_content") or final_reasoning
            # Merge usage from the retry call
            retry_usage = retry.get("usage", {})
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens"):
                if retry_usage.get(k):
                    usage[k] = usage.get(k, 0) + retry_usage[k]

    cost = _compute_cost(usage)

    return {
        "ok": True,
        "data": {
            "content": final_content,
            "reasoning_content": final_reasoning,
            "model": data.get("model", body.model),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cache_hit_tokens": usage.get("prompt_cache_hit_tokens", 0),
            },
            "cost": cost,
            "tool_results": tool_results,
        },
    }


# ─── Staging API (read-only list endpoints for web UI) ───

@app.get("/api/v1/staging/connections")
def staging_list_connections(status: str = "pending", layer: str = "", limit: int = 50):
    """List staging connections (proposed by LLM/UI)."""
    try:
        from lib.api.staging import list_staging_connections
        conn = get_db()
        kwargs = {"status": status, "limit": limit}
        if layer:
            kwargs["layer"] = layer
        items = list_staging_connections(conn, **kwargs)
        conn.close()
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/v1/staging/studies")
def staging_list_studies(status: str = "submitted", limit: int = 20):
    """List staging studies (proposed by LLM/UI)."""
    try:
        from lib.api.staging import list_staging_studies
        conn = get_db()
        items = list_staging_studies(conn, status, limit)
        conn.close()
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Static frontend serving (SPA with fallback) — MUST be last ───

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="frontend_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve frontend SPA — try exact file, then index.html fallback."""
        target = FRONTEND_DIR / full_path
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
