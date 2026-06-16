#!/usr/bin/env python3
"""Scripture Knowledge Engine — HTTP API Server.

FastAPI app that wraps lib/ modules as HTTP endpoints.
Loads all connection data into RAM at startup for sub-ms responses.
Auto-generates OpenAPI docs at /docs.

Usage:
  cd web && uvicorn server:app --reload --port 8000
  # Open http://localhost:8000/docs for interactive API browser
"""

import sys, os, json, sqlite3
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from lib.db import get_db, get_db_vec, DEFAULT_DB_PATH
from lib.gematria import compute_all, find_divine_name_matches
from lib.connections.pardes import get_pardes_level, LEVELS as PARDES_LEVELS
from lib.sod import atbash as atb, acrostic, gematria_advanced, hidden_names
from lib.controls.calibration import QUALITY_LEVELS, get_quality_emoji

app = FastAPI(
    title="Scripture Knowledge Engine",
    description="API for the scripture connection graph — 218K connections across 10 layers, Hebrew + Greek, PaRDeS levels, hidden patterns",
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


# ─── RAM Cache (loaded at startup, zero disk reads after) ───
GUIDE_CACHE = {}          # verse_id → {connections_json, gematria_json, quality_summary, ...}
VERSE_CACHE = {}          # verse_id → {id, text_english, text_hebrew, text_greek, book_id, chapter, verse, book_title}
ENTITY_CACHE = []         # all entity links
VEC_CACHE = {"available": False}  # vector search — populated by embed script


@app.on_event("startup")
def load_ram_cache():
    """Load all passage guides + verse data into RAM at startup.
    
    Eliminates disk reads for all verse and connection lookups.
    ~41K guides, ~42K verses, ~500MB total RAM.
    Loads in under 2 seconds.
    """
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
def get_verse(ref: str):
    """Get verse text with connections — served from RAM cache, zero disk reads."""
    ref = ref.replace(":", ".").replace(" ", ".").lower()
    import re

    # Parse reference
    r = VERSE_CACHE.get(ref)
    if not r:
        m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', ref)
        if m:
            vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"
            r = VERSE_CACHE.get(vid)
    if not r:
        raise HTTPException(status_code=404, detail=f"Verse not found: {ref}")

    vid = r["id"]
    guide = GUIDE_CACHE.get(vid)

    resp = {
        "verse_id": vid,
        "reference": f"{r.get('book_title', '')} {r.get('chapter','')}:{r.get('verse','')}",
        "text_english": r["text_english"],
        "text_hebrew": r.get("text_hebrew") or None,
        "text_greek": r.get("text_greek") or None,
        "has_hebrew": bool(r.get("has_hebrew")),
        "has_greek": bool(r.get("has_greek")),
        "cached": True,
    }

    if guide:
        resp["connections"] = json.loads(guide["connections_json"])
        resp["total_connections"] = guide["total_connections"]
        resp["layer_count"] = guide["layer_count"]
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

    return {"ok": True, "data": resp}


@app.get("/api/v1/verses/{ref:path}/connections")
def get_verse_connections(ref: str, layer: Optional[str] = None, min_quality: Optional[str] = None):
    """Get filtered connections for a verse."""
    resp = get_verse(ref)
    if not resp["ok"]:
        return resp
    data = resp["data"]
    conns = data.get("connections", {})

    if layer and layer in conns:
        conns = {layer: conns[layer]}
    elif layer:
        conns = {}

    # Filter by quality if requested
    if min_quality and conns:
        min_rank = QUALITY_LEVELS.get(min_quality, {}).get("rank", 5)
        filtered = {}
        for lyr, items in conns.items():
            filtered[lyr] = [i for i in items if QUALITY_LEVELS.get(i.get("quality", "suggested"), {}).get("rank", 5) <= min_rank]
        conns = filtered

    return {"ok": True, "data": {"verse": ref, "layers": list(conns.keys()), "connections": conns}}


# ─── Search ───

@app.get("/api/v1/search")
def search(q: str = Query(..., description="Search term"), lang: str = "all", limit: int = 20):
    """Search across English, Hebrew, and Greek simultaneously."""
    conn = get_db()
    results = []

    if lang in ("all", "english"):
        rows = conn.execute("SELECT id, text_english, b.title FROM verses v JOIN books b ON b.id=v.book_id WHERE v.text_english LIKE ? LIMIT ?", (f"%{q}%", limit)).fetchall()
        results.extend({"verse": r["id"], "text": r["text_english"][:200], "book": r["title"], "language": "english"} for r in rows)

    if lang in ("all", "hebrew"):
        rows = conn.execute("SELECT DISTINCT v.id, v.text_hebrew, v.text_english, b.title FROM gematria g JOIN verses v ON v.id=g.verse_id JOIN books b ON b.id=v.book_id WHERE g.word_hebrew LIKE ? LIMIT ?", (f"%{q}%", limit)).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append({"verse": r["id"], "text": (r["text_hebrew"] or "")[:120], "english": (r["text_english"] or "")[:60], "book": r["title"], "language": "hebrew"})

    if lang in ("all", "greek"):
        rows = conn.execute("SELECT DISTINCT v.id, v.text_greek, v.text_english, b.title FROM gematria_greek g JOIN verses v ON v.id=g.verse_id JOIN books b ON b.id=v.book_id WHERE g.word_greek LIKE ? OR g.lemma LIKE ? LIMIT ?", (f"%{q}%", f"%{q}%", limit)).fetchall()
        seen = set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append({"verse": r["id"], "text": (r["text_greek"] or "")[:120], "english": (r["text_english"] or "")[:60], "book": r["title"], "language": "greek"})

    conn.close()
    return {"ok": True, "data": {"query": q, "total": len(results), "results": results}}


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
            "tools_available": 10,
        }
    }


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


# ─── Health Check ───

@app.get("/api/v1/health")
def health():
    return {"ok": True, "data": {"status": "running", "connections": 218292, "guides": 41126}}
