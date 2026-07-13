#!/usr/bin/env python3
"""Scripture Knowledge Engine — HTTP API Server.

FastAPI app that wraps lib/ modules as HTTP endpoints.
Loads all connection data into RAM at startup for sub-ms responses.
Auto-generates OpenAPI docs at /docs.

Usage:
  cd web && uvicorn server:app --reload --port 8002
  # Open http://localhost:8002/docs for interactive API browser
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from biblical_transliteration import HebrewOptions, HebrewScheme, HebrewTransliterator
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lib.api import TOOL_REGISTRY, call_tool
from lib.connections.pardes import LEVELS as PARDES_LEVELS
from lib.connections.pardes import get_pardes_level
from lib.controls.calibration import (
    enrich_connection,
    rate_connection_row,
)
from lib.db import DEFAULT_DB_PATH, get_db, get_db_vec
from lib.gematria import compute_all, find_divine_name_matches
from lib.lexicon import (
    get_concordance,
    get_domain_members,
    get_lexicon_entry,
    get_root_family,
    search_lexicon,
)
from lib.patterns.intra_verse import detect_intra_verse
from lib.sod import acrostic, gematria_advanced, hidden_names
from lib.sod import atbash as atb

_hebrew_trans = HebrewTransliterator(HebrewOptions(scheme=HebrewScheme.SIMPLE))

# Track server start time for uptime reporting
_start_time = time.time()

import contextlib

@contextlib.asynccontextmanager
async def lifespan(app):
    """Startup: create debug table, load caches. Shutdown: no-op."""
    _startup_debug()
    load_ram_cache()
    _build_lexicon_cache_index()
    # Load wiki articles into RAM cache
    _wiki_conn = get_db()
    _wiki_rows = _wiki_conn.execute("SELECT * FROM wiki_articles").fetchall()
    for _r in _wiki_rows:
        WIKI_CACHE[_r["id"]] = dict(_r)
    _wiki_conn.close()
    if WIKI_CACHE:
        log.info("Cache loaded", cache="wiki_articles", count=len(WIKI_CACHE))
    yield

app = FastAPI(
    title="Scripture Knowledge Engine",
    description="API for the scripture connection graph — 1,356,667 connections across 124 types in 11 layers, Hebrew + Greek + Vulgate, PaRDeS levels, hidden patterns, lexicon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include route modules

from web.routes.assessment import router as assessment_router
from web.routes.audio import router as audio_router
from web.routes.auth import router as auth_router
from web.routes.chat import router as chat_router
from web.routes.conversations import router as conversations_router
from web.routes.graph import router as graph_router
from web.routes.hebrew import router as hebrew_router
from web.routes.learn import router as learn_router
from web.routes.memorize import router as memorize_router
from web.routes.studies import router as studies_router

app.include_router(hebrew_router)
app.include_router(audio_router)
app.include_router(chat_router)
app.include_router(studies_router)
app.include_router(conversations_router)
app.include_router(assessment_router)
app.include_router(auth_router)
app.include_router(graph_router)
app.include_router(memorize_router)
app.include_router(learn_router)


# ─── RAM Cache (loaded at startup, zero disk reads after) ───
GUIDE_CACHE = {}          # verse_id → {connections_json, gematria_json, quality_summary, ...}
VERSE_CACHE = {}          # verse_id → {id, text_english, text_hebrew, text_greek, book_id, chapter, verse, book_title}
ENTITY_CACHE = []         # all entity links
LEXICON_CACHE = {}        # lemma → lexicon entry (loaded at startup)
VEC_CACHE = {"available": False}  # vector search — populated by embed script
BOOKS_CACHE = None         # work/book tree — precomputed at startup, static data

# ── Structured JSON Logger ──

class JSONLogger:
    """Simple JSON-structured logger. Replaces print() for server-side logging."""
    def _log(self, level, msg, **extra):
        record = {"level": level, "msg": msg, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        record.update(extra)
        print(json.dumps(record), flush=True)

    def info(self, msg, **extra): self._log("info", msg, **extra)
    def warn(self, msg, **extra): self._log("warn", msg, **extra)
    def error(self, msg, **extra): self._log("error", msg, **extra)

log = JSONLogger()

# ── Request Timing Middleware ──

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if duration > 2.0:
        log.warn("slow_request", method=request.method, path=str(request.url.path),
                 duration=round(duration, 3), status=response.status_code)
    return response


def _startup_debug():
    """Create client_logs table for debug error reporting."""
    try:
        import sqlite3 as _s
        from pathlib import Path as _Path
        _c = _s.connect(str(_Path(__file__).parent.parent / "data" / "processed" / "scripture.db"))
        _c.execute(
            "CREATE TABLE IF NOT EXISTS client_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "level TEXT DEFAULT 'error', "
            "message TEXT, "
            "stack TEXT DEFAULT '', "
            "url TEXT DEFAULT '', "
            "user_agent TEXT DEFAULT '', "
            "created_at TEXT DEFAULT (datetime('now'))"
            ")"
        )
        _c.commit()
        _c.close()
    except Exception:
        pass

def load_ram_cache():
    """Load all passage guides + verse data into RAM at startup.

    Eliminates disk reads for all verse and connection lookups.
    ~41K guides, ~42K verses, ~500MB total RAM.
    Automatically skips when running multi-worker (each worker loads its own).

    Set SCRIPTURE_WORKERS=1 to force RAM cache, SCRIPTURE_WORKERS=0 to skip.
    """
    workers = int(os.environ.get("SCRIPTURE_WORKERS", "1"))

    log.info("Loading cache", phase="start")
    db_path = DEFAULT_DB_PATH
    if not os.path.exists(db_path):
        log.error("DB not found", path=str(db_path))
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Load books/work tree — always cache (tiny data, ~2KB)
    global BOOKS_CACHE
    works_rows = conn.execute("SELECT id, title, subtitle FROM works ORDER BY position").fetchall()
    books_result = []
    for w in works_rows:
        books = conn.execute(
            "SELECT id, title, subtitle FROM books WHERE work_id=? ORDER BY position",
            (w["id"],)
        ).fetchall()
        books_result.append({
            "id": w["id"],
            "title": w["title"],
            "subtitle": w["subtitle"],
            "books": [{"id": b["id"], "title": b["title"], "subtitle": b["subtitle"]} for b in books],
        })
    BOOKS_CACHE = {"works": books_result, "total": len(books_result)}
    log.info("Cache loaded", cache="books", count=len(books_result))

    # Multi-worker mode: skip heavy caches, books already loaded above
    if workers != 1:
        log.info("Skipping RAM cache (multi-worker)", workers=workers, mode="direct_sqlite")
        conn.close()
        total = len(books_result)
        log.info("Cache load complete", total_items=total)
        return

    # Load verses
    rows = conn.execute("""
        SELECT v.*, b.title as book_title
        FROM verses v JOIN books b ON b.id = v.book_id
    """).fetchall()
    for r in rows:
        d = dict(r)
        VERSE_CACHE[d["id"]] = d
    log.info("Cache loaded", cache="verses", count=len(VERSE_CACHE))

    # Load passage guides
    rows = conn.execute("""
        SELECT verse_id, connections_json, gematria_json, quality_summary,
               layer_count, total_connections
        FROM passage_guides
    """).fetchall()
    for r in rows:
        d = dict(r)
        GUIDE_CACHE[d["verse_id"]] = d
    log.info("Cache loaded", cache="passage_guides", count=len(GUIDE_CACHE))

    # Load entity links
    rows = conn.execute("SELECT * FROM entity_links").fetchall()
    for r in rows:
        ENTITY_CACHE.append(dict(r))
    log.info("Cache loaded", cache="entity_links", count=len(ENTITY_CACHE))

    # Load lexicon
    lex_rows = conn.execute("SELECT * FROM lexicon").fetchall()
    for r in lex_rows:
        LEXICON_CACHE[r["lemma"]] = dict(r)
    log.info("Cache loaded", cache="lexicon", count=len(LEXICON_CACHE))

    # Check vector availability — without loading vec0 module
    vec_table = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='vec_verses'
    """).fetchone()
    if vec_table:
        VEC_CACHE["available"] = True
        VEC_CACHE["count"] = "check via vec queries"
        log.info("Vectors available", check="semantic_search")
    else:
        log.warn("Vectors not found", fix=".venv/bin/python3 scripts/embed_verses.py")

    conn.close()
    total = len(VERSE_CACHE) + len(GUIDE_CACHE) + len(ENTITY_CACHE) + len(books_result)
    log.info("Cache load complete", total_items=total)

CONNECTION_TYPE_MAP = {
    "linguistic": "Linguistic", "numerical": "Numerical",
    "structural": "Structural", "intertextual": "Intertextual",
    "textual": "Textual", "geographic": "Geographic",
    "chronological": "Chronological", "interpretive": "Interpretive",
    "frequency": "Frequency", "symbolic": "Symbolic",
}


# ─── Verse & Passage Guide ───

@app.get("/api/v1/verses/{ref:path}")
def get_verse(ref: str, show_signals: bool | None = Query(False, description="Enrich connections with quality signal breakdown"), context: int | None = Query(0, description="Number of surrounding verses to include for context window (e.g. context=3 gives ±3 verses)")):
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

    native_greek = r.get("text_greek") or None
    lxx_fallback = None
    if not native_greek:
        try:
            _conn = get_db()
            _lxx = _conn.execute(
                "SELECT text FROM text_resources WHERE verse_id = ? AND version = 'LXX'",
                (vid,)
            ).fetchone()
            if _lxx:
                lxx_fallback = _lxx["text"]
            _conn.close()
        except Exception:
            pass  # Non-critical
    resp = {
        "verse_id": vid,
        "reference": f"{r.get('book_title', '')} {r.get('chapter','')}:{r.get('verse','')}",
        "text_english": r["text_english"],
        "text_hebrew": r.get("text_hebrew") or None,
        "text_greek": native_greek or lxx_fallback,
        "text_greek_source": "sbl" if native_greek else ("lxx" if lxx_fallback else None),
        "has_hebrew": bool(r.get("has_hebrew")),
        "has_greek": bool(native_greek or lxx_fallback),
        "cached": bool(VERSE_CACHE),
    }

    # JST text (if available)
    try:
        _jst = get_db()
        _jst_row = _jst.execute(
            "SELECT text FROM text_resources WHERE verse_id=? AND version='JST'",
            (vid,)
        ).fetchone()
        if _jst_row:
            resp["text_jst"] = _jst_row["text"]
            # Compute diff type by looking up the JST connection
            _diff = _jst.execute(
                "SELECT type FROM connections WHERE source_verse=? AND target_verse=? AND layer='textual' AND (type='jst_change' OR type='jst_addition')",
                (vid, vid)
            ).fetchone()
            if _diff:
                resp["jst_diff"] = _diff["type"]  # "jst_change" or "jst_addition"
        _jst.close()
    except Exception:
        pass

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

        # Enrich connections with tradition + hermeneutic from DB (batch query)
        try:
            _conn_meta = get_db()
            _targets = []
            for _layer, _items in resp.get("connections", {}).items():
                for _item in _items:
                    _tgt = _item.get("target", "")
                    if _tgt:
                        _targets.append(_tgt)
            if _targets:
                _placeholders = ",".join("?" for _ in _targets)
                _meta_rows = _conn_meta.execute(
                    f"""SELECT source_verse, target_verse, tradition, hermeneutic
                        FROM connections WHERE source_verse=? AND target_verse IN ({_placeholders})""",
                    (vid, *_targets)
                ).fetchall()
                _meta_map = {}
                for _r in _meta_rows:
                    _key = f"{_r[0]}→{_r[1]}"
                    _meta_map[_key] = {"tradition": _r[2] or "none", "hermeneutic": _r[3] or "linguistic"}
                # Apply to connection items
                for _layer, _items in resp.get("connections", {}).items():
                    for _item in _items:
                        _tgt = _item.get("target", "")
                        if _tgt:
                            _key = f"{vid}→{_tgt}"
                            _meta = _meta_map.get(_key, {})
                            _item["tradition"] = _meta.get("tradition", "none")
                            _item["hermeneutic"] = _meta.get("hermeneutic", "linguistic")
            _conn_meta.close()
        except Exception:
            pass  # Non-critical — enrichment failure shouldn't break verse lookup

        # Interpretive disagreements — contradictory readings across traditions
        try:
            from lib.api.disagreements import get_disagreements
            _conn_dis = get_db()
            resp["disagreements"] = get_disagreements(_conn_dis, vid)
            _conn_dis.close()
        except Exception:
            resp["disagreements"] = {"verse": vid, "count": 0, "disagreements": []}

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
def get_verse_connections(ref: str, layer: str | None = None, min_quality: str | None = None, discovered_by: str | None = None, min_confidence: float | None = None, show_signals: bool | None = False):
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

                if discovered_by and sigs["signals"]["discovery_method"] != discovered_by:
                    continue

                if min_confidence is not None and sigs["overall_confidence"] < min_confidence:
                    continue

                if show_signals:
                    item["signals"] = sigs

                filtered_items.append(item)

            if filtered_items:
                filtered[lyr] = filtered_items

        conns = filtered

    return {"ok": True, "data": {"verse": ref, "layers": list(conns.keys()), "connections": conns}}


@app.get("/api/v1/verses/{ref:path}/disagreements")
def get_verse_disagreements(ref: str):
    """Get interpretive disagreements for a verse — contradictory readings across traditions."""
    conn = get_db()
    try:
        from lib.api.disagreements import get_disagreements
        result = get_disagreements(conn, ref)
        conn.close()
        return {"ok": True, "data": result}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


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
        if token.startswith("book:") or token.startswith("b:") or token.startswith("work:") or token.startswith("w:"):
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

    if lang in ("all", "english") and search_query:
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
            total_row["cnt"] if total_row else 0

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
            total_row["cnt"] if total_row else 0
            rows = conn.execute(f"{like_sql} LIMIT ? OFFSET ?", like_params + [limit_plus_one, offset]).fetchall()

        for r in rows:
            item = {"verse": r["id"], "text": r["text_english"][:200], "book": r["title"], "language": "english"}
            if "match_offsets" in r:
                offsets = []
                parts = r["match_offsets"].split()
                for i in range(0, len(parts), 4):
                    if i + 3 < len(parts):
                        with contextlib.suppress(ValueError, IndexError):
                            offsets.append({"pos": int(parts[i + 2]), "len": int(parts[i + 3])})
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
def gematria(word: str | None = None, value: int | None = None, system: str = "standard"):
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
def sod(verse: str | None = None, atbash_word: str | None = None, acrostic_book: str | None = None):
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
            from lib.sod.notarikon import first_letters, last_letters
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

    import hashlib
    import re
    import struct

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
def get_pardes(ref: str, level: str | None = None):
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


@app.get("/api/v1/books")
def get_books():
    """Get all works and their books for navigation — served from RAM cache."""
    global BOOKS_CACHE
    if BOOKS_CACHE is not None:
        return {"ok": True, "data": BOOKS_CACHE}
    # Fall back to direct SQLite for multi-worker or cold start
    conn = get_db()
    works_rows = conn.execute("SELECT id, title, subtitle FROM works ORDER BY position").fetchall()
    result = []
    for w in works_rows:
        books = conn.execute(
            "SELECT id, title, subtitle FROM books WHERE work_id=? ORDER BY position",
            (w["id"],)
        ).fetchall()
        result.append({
            "id": w["id"],
            "title": w["title"],
            "subtitle": w["subtitle"],
            "books": [{"id": b["id"], "title": b["title"], "subtitle": b["subtitle"]} for b in books],
        })
    conn.close()
    return {"ok": True, "data": {"works": result, "total": len(result)}}


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
        morph[:2] if len(morph) >= 2 else ''
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
        # Fetch raw gematria data, then enrich with lexicon/gloss in Python
        # (SQL joins on compound lemmas like "b/7225" are unreliable)
        rows = conn.execute("""
            SELECT g.verse_id, g.word_hebrew, g.word_english, g.morph, g.lemma, g.word_index,
                   g.value_standard, g.value_ordinal, g.value_reduced
            FROM gematria g
            WHERE g.verse_id LIKE ?
            ORDER BY g.verse_id, g.word_index
        """, (f"{verse_prefix}%",)).fetchall()

        # Build lookup maps from lemma_gloss and lexicon
        gloss_map = {}
        for r in conn.execute("SELECT lemma, english_gloss FROM lemma_gloss"):
            gloss_map[r['lemma']] = r['english_gloss'] or ''
        lex_map = {}
        for r in conn.execute("SELECT lemma, definition, part_of_speech, root_letters FROM lexicon"):
            lex_map[r['lemma']] = dict(r)

        def extract_lemma_key(raw_lemma):
            """Extract the numeric key from a compound lemma like 'b/7225' -> '7225'."""
            if '/' in raw_lemma:
                return raw_lemma.split('/')[1]
            return raw_lemma

        def lookup_gloss(raw_lemma):
            """Try full lemma match first, then numeric extraction."""
            if raw_lemma in gloss_map:
                return gloss_map[raw_lemma]
            key = extract_lemma_key(raw_lemma)
            return gloss_map.get(key, '')

        def lookup_lexicon(raw_lemma):
            """Try full lemma match first, then numeric extraction."""
            if raw_lemma in lex_map:
                return lex_map[raw_lemma]
            key = extract_lemma_key(raw_lemma)
            return lex_map.get(key, {})

    # Group by verse
    verses = {}
    for w in rows:
        vid = w["verse_id"]
        if vid not in verses:
            verses[vid] = []
        morph = w["morph"] or ""
        morph[:2] if len(morph) >= 2 else ""
        color = "#cccccc"
        for pfx, c in MORPH_COLORS.items():
            if morph.startswith(pfx):
                color = c
                break
        word_raw = w["word_hebrew"] or ""
        # Clean Hebrew: remove / separators
        word_clean = word_raw.replace("/", "")
        # Transliterate using biblical-transliteration SIMPLE scheme
        try:
            translit = _hebrew_trans.transliterate_word(word_clean)
        except Exception:
            translit = ""
        # Look up gloss and lexicon data in Python
        raw_lemma = w["lemma"] or ""
        gloss = lookup_gloss(raw_lemma)
        lex = lookup_lexicon(raw_lemma)
        verses[vid].append({
            "hebrew": word_raw,
            "hebrew_clean": word_clean,
            "transliteration": translit,
            "english": gloss or w["word_english"] or "",
            "definition": lex.get("definition", ""),
            "morph": morph,
            "pos": lex.get("part_of_speech", ""),
            "root_letters": lex.get("root_letters", ""),
            "lemma": raw_lemma,
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
        with contextlib.suppress(_json.JSONDecodeError, TypeError):
            ref_data = _json.loads(r["reference_data"]) if r["reference_data"] else {}
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
    connection_id: int | None = None
    source_verse: str | None = None
    target_verse: str | None = None
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
    parent: str | None = None

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
        raise HTTPException(status_code=500, detail=str(e)) from e
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
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        conn.close()



# ─── Hebrew + Vocabulary + Grammar Reference ───
# All moved to web/routes/hebrew.py
# The APIRouter is included at the top of this file.

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


# ─── Wiki Endpoints ───

WIKI_CACHE = {}  # entity/id → article, loaded at startup


@app.get("/api/v1/wiki/search")
def search_wiki(q: str = ""):
    """Search wiki articles by title or summary."""
    query = q.strip().lower()
    if not query or not WIKI_CACHE:
        return {"ok": True, "data": {"results": [], "total": 0}}

    results = []
    for article in WIKI_CACHE.values():
        title = (article.get("title") or "").lower()
        summary = (article.get("summary") or "").lower()
        # Simple substring + word boundary match
        if query in title or query in summary:
            score = 2 if query in title else 1
            results.append({
                "id": article["id"],
                "title": article["title"],
                "summary": (article.get("summary") or "")[:200],
                "article_type": article.get("article_type", ""),
                "score": score,
            })

    results.sort(key=lambda r: -r["score"])
    return {"ok": True, "data": {"results": results[:20], "total": len(results)}}


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


# ─── Assessment ↔ Wiki Bridges ───

@app.get("/api/v1/learn/{knowledge_item_id:path}")
def learn_about_knowledge_item(knowledge_item_id: str):
    """Get wiki articles related to a knowledge item — 'learn more' links.

    Given a knowledge_item_id, finds entities associated with both
    the source and target verses, then returns matching wiki articles.

    Used by the assessment system to show 'Learn more about [Entity]'
    when a user gets a question wrong.

    /api/v1/learn/12345  → wiki articles for entities in both verses
    """
    kid = knowledge_item_id.strip("/")
    conn = get_db()

    # Get the knowledge item
    item = conn.execute(
        "SELECT ki.verse_id, ki.target_verse, ki.connection_type, ki.layer "
        "FROM knowledge_items ki WHERE ki.id = ?", (int(kid) if kid.isdigit() else 0,)
    ).fetchone()

    if not item:
        conn.close()
        # Fallback: try looking up by verse pair
        parts = kid.split("__")
        if len(parts) == 2:
            item = conn.execute(
                "SELECT verse_id, target_verse, connection_type, layer FROM knowledge_items WHERE verse_id=? AND target_verse=? LIMIT 1",
                (parts[0], parts[1])
            ).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Knowledge item not found: {kid}")

    # Find entities for both verses
    [item["verse_id"], item["target_verse"]]
    entities = conn.execute(
        """
        SELECT DISTINCT el.entity_id, el.english_name, el.entity_type
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        WHERE ve.verse_id IN (?, ?) AND ve.confidence >= 0.3
        ORDER BY el.entity_type
    """,
        (item["verse_id"], item["target_verse"]),
    ).fetchall()

    # Match to wiki articles (WIKI_CACHE has article data)
    articles = []
    for e in entities:
        eid = e["entity_id"]
        # Try direct match
        slug = eid.lower().replace(" ", "_")
        article = WIKI_CACHE.get(slug) or WIKI_CACHE.get(eid)
        if article:
            articles.append({
                "entity_id": eid,
                "title": article["title"],
                "summary": (article.get("summary") or "")[:150],
                "article_type": article["article_type"],
            })
        else:
            # Entity exists but no wiki article
            articles.append({
                "entity_id": eid,
                "title": e["english_name"],
                "summary": "",
                "article_type": e["entity_type"],
                "has_article": False,
            })

    conn.close()
    return {"ok": True, "data": {
        "knowledge_item": {
            "id": kid,
            "verse_id": item["verse_id"],
            "target_verse": item["target_verse"],
            "connection_type": item["connection_type"],
            "layer": item["layer"],
        },
        "articles": articles,
        "total_articles": len(articles),
    }}


@app.get("/api/v1/assess/entity/{entity_id:path}")
def start_entity_assessment(entity_id: str):
    """Start an assessment filtered to a specific entity's verses.

    Returns assessment items where both the source and target verse
    mention the given entity. Links from wiki entity pages.

    /api/v1/assess/entity/covenant  → assessment on covenant connections
    """
    eid = entity_id.strip("/").lower()
    conn = get_db()

    # Verify entity exists
    entity = conn.execute(
        "SELECT * FROM entity_links WHERE entity_id = ?", (eid,)
    ).fetchone()
    if not entity:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Entity not found: {eid}")

    # Count available items
    count = conn.execute(
        """
        SELECT COUNT(*) as c
        FROM knowledge_items ki
        JOIN verse_entities ve1 ON ve1.verse_id = ki.verse_id AND ve1.entity_id = ?
        JOIN verse_entities ve2 ON ve2.verse_id = ki.target_verse AND ve2.entity_id = ?
    """,
        (eid, eid),
    ).fetchone()["c"]

    # Get a random sample of items for review
    items = conn.execute(
        """
        SELECT ki.id, ki.verse_id, ki.target_verse, ki.connection_type,
               ki.star_rating, ki.difficulty, ki.pa_r_de_s_level, ki.bloom_level,
               v1.text_english as source_text, v2.text_english as target_text
        FROM knowledge_items ki
        JOIN verse_entities ve1 ON ve1.verse_id = ki.verse_id AND ve1.entity_id = ?
        JOIN verse_entities ve2 ON ve2.verse_id = ki.target_verse AND ve2.entity_id = ?
        JOIN verses v1 ON v1.id = ki.verse_id
        JOIN verses v2 ON v2.id = ki.target_verse
        ORDER BY ki.star_rating DESC, RANDOM()
        LIMIT 20
    """,
        (eid, eid),
    ).fetchall()

    conn.close()

    return {"ok": True, "data": {
        "entity": {
            "entity_id": eid,
            "english_name": entity["english_name"],
            "entity_type": entity["entity_type"],
        },
        "total_items": count,
        "star_distribution": {
            "5": count_where(items, "star_rating", 5),
            "4": count_where(items, "star_rating", 4),
            "3": count_where(items, "star_rating", 3),
            "2": count_where(items, "star_rating", 2),
            "1": count_where(items, "star_rating", 1),
        },
        "sample_items": [dict(r) for r in items[:10]],
    }}


def count_where(rows, field, value):
    """Count items in a list of Row objects where field == value."""
    return sum(1 for r in rows if r[field] == value)


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

        # Add to source verse
        if src in verse_parallelisms:
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
                    with contextlib.suppress(ValueError):
                        verse_nums.append(int(parts[2]))
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
                with contextlib.suppress(ValueError):
                    pivot_ch = int(p_parts[1])

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
    {v["verse"]: v["id"] for v in verse_list}

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

    # 4a. Batch fetch LXX Greek text for verses without native Greek
    missing_greek_ids = [v["id"] for v in verse_list if not v["text_greek"]]
    lxx_texts = {}
    if missing_greek_ids:
        gp = ",".join("?" for _ in missing_greek_ids)
        lxx_rows = conn.execute(f"""
            SELECT verse_id, text FROM text_resources
            WHERE verse_id IN ({gp}) AND version = 'LXX'
        """, missing_greek_ids).fetchall()
        for r in lxx_rows:
            lxx_texts[r["verse_id"]] = r["text"]

    # 4b. Build response verses with intra-verse lines + parallelism
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

        # Fallback: serve LXX Greek translation when native Greek unavailable
        greek_text = v["text_greek"] or lxx_texts.get(v["id"]) or None
        greek_source = "sbl" if v["text_greek"] else ("lxx" if v["id"] in lxx_texts else None)
        response_verses.append({
            "verse": v["verse"],
            "text_english": v["text_english"],
            "text_hebrew": v["text_hebrew"],
            "text_greek": greek_text,
            "text_greek_source": greek_source,
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


@app.get("/api/v1/chapter/{ref:path}/entities")
def get_chapter_entities(ref: str):
    """Get all entities (people, places, concepts) for verses in a chapter.

    /api/v1/chapter/isa.55/entities   → Entities in Isaiah 55
    /api/v1/chapter/gen.1/entities    → Entities in Genesis 1
    """
    ref_clean = ref.strip("/")
    parts = ref_clean.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Use format: book.chapter (e.g., isa.55)")
    book_id = parts[0]
    chapter_num = int(parts[1])

    conn = get_db()

    # Get all verse IDs for this chapter
    verse_rows = conn.execute(
        "SELECT id FROM verses WHERE book_id = ? AND chapter = ? ORDER BY verse",
        (book_id, chapter_num)
    ).fetchall()
    if not verse_rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Chapter not found: {ref_clean}")

    verse_ids = [r["id"] for r in verse_rows]
    placeholders = ",".join("?" for _ in verse_ids)

    # Get all entities for these verses
    entity_rows = conn.execute(f"""
        SELECT ve.verse_id, ve.entity_id, ve.relationship_type, ve.confidence,
               el.english_name, el.hebrew_name, el.greek_name, el.entity_type,
               el.notes
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        WHERE ve.verse_id IN ({placeholders})
          AND ve.confidence >= 0.3
        ORDER BY el.entity_type, el.english_name
    """, verse_ids).fetchall()

    conn.close()

    if not entity_rows:
        return {"ok": True, "data": {"chapter": ref_clean, "entities": [], "total": 0}}

    # Group by entity
    seen = {}
    for r in entity_rows:
        eid = r["entity_id"]
        if eid not in seen:
            seen[eid] = {
                "entity_id": eid,
                "english_name": r["english_name"],
                "hebrew_name": r["hebrew_name"],
                "greek_name": r["greek_name"],
                "entity_type": r["entity_type"],
                "notes": r["notes"],
                "verses": [],
                "total_mentions": 0,
            }
        # Extract verse number from verse_id (format: book.chapter.verse)
        vnum = r["verse_id"].split(".")[-1] if "." in r["verse_id"] else r["verse_id"]
        seen[eid]["verses"].append({
            "verse": vnum,
            "relationship": r["relationship_type"],
            "confidence": r["confidence"],
        })
        seen[eid]["total_mentions"] += 1

    return {"ok": True, "data": {
        "chapter": ref_clean,
        "total_entities": len(seen),
        "entities": list(seen.values()),
    }}



# ─── Study Guides moved to web/routes/studies.py ───

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
    parent_id: int | None = None

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
    vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}" if m else ref

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
    parent_id: int | None = None

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



# ─── Health Check ───

@app.get("/api/v1/health")
def health_check():
    """Health check with DB integrity, cache status, version, and uptime."""
    import time as _time
    conn = get_db()
    verse_count = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    conn_count = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]

    # DB integrity check
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

    # Traditional distribution summary
    trad_dist = {
        r[0]: r[1] for r in conn.execute(
            "SELECT COALESCE(tradition, 'unset') as t, COUNT(*) as cnt "
            "FROM connections WHERE deprecated=0 GROUP BY t ORDER BY cnt DESC"
        ).fetchall()
    }

    # Layer distribution
    layer_dist = {
        r[0]: r[1] for r in conn.execute(
            "SELECT layer, COUNT(*) as cnt FROM connections WHERE deprecated=0 GROUP BY layer ORDER BY cnt DESC"
        ).fetchall()
    }

    # Audio alignments count
    audio_count = 0
    align_dir = Path(__file__).resolve().parent.parent / "data" / "audio" / "alignments"
    if align_dir.exists():
        audio_count = len(list(align_dir.glob("*.json")))

    # Uptime
    uptime_seconds = int(_time.time() - _start_time)
    conn.close()

    # Cache status
    cache_sizes = {
        "wiki_articles": len(WIKI_CACHE),
        "lexicon_entries": len(LEXICON_CACHE),
        "tool_registry": len(TOOL_REGISTRY),
    }

    return {"ok": True, "data": {
        "status": "ok" if integrity == "ok" else "degraded",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "verses": verse_count,
        "connections": conn_count,
        "integrity": integrity,
        "traditional_distribution": trad_dist,
        "layer_distribution": layer_dist,
        "audio_alignments": audio_count,
        "tools": len(TOOL_REGISTRY),
        "lexicon": len(LEXICON_CACHE),
        "cache_sizes": cache_sizes,
    }}


# ─── Conversation sessions moved to web/routes/conversations.py ───

# ─── LLM Chat Proxy moved to web/routes/chat.py ───

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


# ─── Client-side error logging (for debugging) ───

@app.post("/api/v1/debug/log")
def client_error_log(data: dict):
    try:
        conn = get_db()
        conn.execute('CREATE TABLE IF NOT EXISTS client_logs ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT,'
            'level TEXT DEFAULT "error",'
            'message TEXT,'
            'stack TEXT DEFAULT "",'
            'url TEXT DEFAULT "",'
            'user_agent TEXT DEFAULT "",'
            'created_at TEXT DEFAULT (datetime("now"))'
        ')')
        conn.execute(
            'INSERT INTO client_logs (level, message, stack, url, user_agent) VALUES (?, ?, ?, ?, ?)',
            (data.get("level", "error"), data.get("message", "")[:500],
             data.get("stack", "")[:2000], data.get("url", ""), data.get("userAgent", ""))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return {"ok": True}

@app.get("/api/v1/debug/logs")
def get_client_logs(limit: int = 50):
    conn = get_db()
    rows = conn.execute("SELECT * FROM client_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}

@app.get("/api/v1/debug/check")
def debug_check():
    import os
    import sys
    conn = get_db()
    try:
        verse_count = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        conn_count = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
        audio_count = 0
        for _root, _dirs, files in os.walk("data/audio/alignments"):
            audio_count = len(files)
    except Exception:
        verse_count = conn_count = audio_count = 0
    conn.close()
    return {"ok": True, "data": {
        "python": sys.version,
        "platform": __import__("platform").platform(),
        "verses": verse_count,
        "connections": conn_count,
        "audio_alignments": audio_count,
        "assets": os.listdir("frontend/dist/assets/") if os.path.isdir("frontend/dist/assets/") else [],
    }}

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


# ─── Cross-Canon Truth Score API ───

@app.get("/api/v1/truth-score")
def truth_score(
    q: str = Query("", description="Topic or search term"),
    verse: str = Query("", description="Specific verse to analyze"),
    limit: int = Query(20, description="Max verses per work"),
):
    """Cross-canon consensus scoring.

    For a given topic/verse, shows how each canon treats it:
    - Number of relevant verses per work
    - Connection counts and tradition distribution
    - Consensus score across canons

    The goal: let users see which interpretations are supported
    across multiple canons vs. unique to one.
    """
    conn = get_db()
    result = {"query": q or verse, "works": [], "consensus": {}}

    # Get all works
    works = conn.execute("SELECT id, title FROM works ORDER BY position").fetchall()

    for w in works:
        wid = w["id"]
        wtitle = w["title"]

        # Find matching verses in this work
        if verse:
            # Specific verse analysis
            verses_data = conn.execute("""
                SELECT v.id, v.text_english FROM verses v
                JOIN books b ON b.id = v.book_id
                WHERE v.id = ? AND b.work_id = ?
            """, (verse, wid)).fetchall()
        elif q:
            # Search in this work's verses
            verses_data = conn.execute("""
                SELECT v.id, v.text_english FROM verses v
                JOIN books b ON b.id = v.book_id
                WHERE b.work_id = ? AND v.text_english LIKE ?
                LIMIT ?
            """, (wid, f"%{q}%", limit)).fetchall()
        else:
            verses_data = []

        if not verses_data:
            continue

        verse_ids = [v["id"] for v in verses_data]

        # Count connections from/to these verses
        placeholders = ",".join("?" for _ in verse_ids)

        conn_count = conn.execute(f"""
            SELECT COUNT(*) as c FROM connections
            WHERE (source_verse IN ({placeholders}) OR target_verse IN ({placeholders}))
            AND deprecated = 0
        """, (*verse_ids, *verse_ids)).fetchone()["c"]

        # Tradition distribution
        trad_dist = conn.execute(f"""
            SELECT COALESCE(tradition, 'unset') as t, COUNT(*) as cnt
            FROM connections
            WHERE (source_verse IN ({placeholders}) OR target_verse IN ({placeholders}))
            AND deprecated = 0
            GROUP BY t ORDER BY cnt DESC
        """, (*verse_ids, *verse_ids)).fetchall()

        # Layer distribution
        layer_dist = conn.execute(f"""
            SELECT layer, COUNT(*) as cnt
            FROM connections
            WHERE (source_verse IN ({placeholders}) OR target_verse IN ({placeholders}))
            AND deprecated = 0
            GROUP BY layer ORDER BY cnt DESC
        """, (*verse_ids, *verse_ids)).fetchall()

        # JST changes for these verses
        jst_count = conn.execute(f"""
            SELECT COUNT(*) as c FROM connections
            WHERE source_verse IN ({placeholders}) AND type LIKE 'jst_%'
        """, (*verse_ids,)).fetchone()["c"]

        # Gematria values
        gem_count = conn.execute(f"""
            SELECT COUNT(*) as c FROM gematria WHERE verse_id IN ({placeholders})
        """, (*verse_ids,)).fetchone()["c"]

        result["works"].append({
            "work_id": wid,
            "title": wtitle,
            "verses_found": len(verses_data),
            "verse_samples": [{"id": v["id"], "text": (v["text_english"] or "")[:100]} for v in verses_data[:5]],
            "total_connections": conn_count,
            "tradition_distribution": {r["t"]: r["cnt"] for r in trad_dist},
            "layer_distribution": {r["layer"]: r["cnt"] for r in layer_dist},
            "jst_changes": jst_count,
            "gematria_entries": gem_count,
        })

    conn.close()

    # Compute consensus
    works_found = len(result["works"])
    if works_found > 0:
        # Average connections per work
        avg_conn = sum(w["total_connections"] for w in result["works"]) / works_found
        # Works with connections
        works_with_conn = sum(1 for w in result["works"] if w["total_connections"] > 0)
        # Works with JST changes
        works_with_jst = sum(1 for w in result["works"] if w["jst_changes"] > 0)

        result["consensus"] = {
            "works_found": works_found,
            "works_with_connections": works_with_conn,
            "works_with_jst_changes": works_with_jst,
            "average_connections": round(avg_conn, 1),
            "consensus_score": round(works_with_conn / max(len(works), 1), 2),
            "interpretation": (
                "supported across multiple canons" if works_with_conn >= 3
                else "found in multiple traditions" if works_with_conn >= 2
                else "unique to one tradition" if works_with_conn == 1
                else "no connection data"
            ),
        }

    return {"ok": True, "data": result}


# ─── Joseph Smith Teachings Search ───

@app.get("/api/v1/js/search")
def search_js(q: str = "", limit: int = 20, year: int = 0):
    """Search Joseph Smith's teachings/discourses by keyword."""
    conn = get_db()

    if not q.strip():
        rows = conn.execute(
            "SELECT id, title, source, year, length(content) as content_len FROM js_texts ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    else:
        # Use FTS5 if available, fall back to LIKE
        try:
            rows = conn.execute("""
                SELECT j.id, j.title, j.source, j.year, length(j.content) as content_len
                FROM js_texts_fts f JOIN js_texts j ON j.id = f.rowid
                WHERE js_texts_fts MATCH ?
                ORDER BY rank LIMIT ?
            """, (q, limit)).fetchall()
        except Exception:
            rows = conn.execute(
                "SELECT id, title, source, year, length(content) as content_len FROM js_texts WHERE content LIKE ? ORDER BY id LIMIT ?",
                (f"%{q}%", limit)
            ).fetchall()

    if year > 0:
        rows = [r for r in rows if r["year"] == year]

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "title": (r["title"] or "")[:200],
            "source": r["source"],
            "year": r["year"],
            "content_length": r["content_len"],
        })

    total = conn.execute("SELECT COUNT(*) FROM js_texts").fetchone()[0]
    conn.close()
    return {"ok": True, "data": {"results": results, "total": total, "matched": len(results)}}


@app.get("/api/v1/js/text/{text_id}")
def get_js_text(text_id: int):
    """Get full text of a Joseph Smith discourse."""
    conn = get_db()
    row = conn.execute("SELECT id, title, content, source, year FROM js_texts WHERE id=?", (text_id,)).fetchone()
    conn.close()
    if not row:
        return {"ok": False, "error": "Text not found"}
    return {"ok": True, "data": dict(row)}


# ─── Daily Verse / Maintenance Mode ───

@app.get("/api/v1/verse-of-day")
def verse_of_day(user_id: str = "default"):
    """Get a random verse with word-by-word breakdown for daily study.

    Returns: random verse with Hebrew, English, Strong's, gematria,
    and connection count. Used by the DailyVerse component for
    maintenance-mode study.
    """
    conn = get_db()
    # Pick a random verse with Hebrew text
    row = conn.execute("""
        SELECT id, book_id, chapter, verse, text_english, text_hebrew
        FROM verses
        WHERE text_hebrew IS NOT NULL
        ORDER BY RANDOM() LIMIT 1
    """).fetchone()

    if not row:
        conn.close()
        return {"ok": False, "error": "No verses found"}

    vid = row["id"]
    result = {
        "verse_id": vid,
        "reference": f"{row['book_id']}.{row['chapter']}.{row['verse']}",
        "text_english": row["text_english"],
        "text_hebrew": row["text_hebrew"],
    }

    # Word count
    heb_words = [w for w in row["text_hebrew"].split() if w.strip()]
    result["word_count"] = len(heb_words)

    # Gematria if available
    gem = conn.execute(
        "SELECT COUNT(*) as c FROM gematria WHERE verse_id=? AND value_standard IS NOT NULL",
        (vid,)
    ).fetchone()
    result["has_gematria"] = (gem and gem["c"] > 0)

    # Connection count
    conns = conn.execute(
        "SELECT COUNT(*) as c FROM connections WHERE (source_verse=? OR target_verse=?) AND deprecated=0",
        (vid, vid)
    ).fetchone()
    result["connections_count"] = conns["c"] if conns else 0

    conn.close()
    return {"ok": True, "data": result}


# ─── Client-side error logging (for debugging) ───

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
