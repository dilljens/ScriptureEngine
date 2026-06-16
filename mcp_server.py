#!/usr/bin/env python3
"""MCP Server for the Scripture Knowledge Engine.

Single persistent process. All tool definitions with JSON Schema.
Only loads when working in scripture-explorer/ directory.

Protocol: JSON-RPC over stdio (standard MCP protocol)
"""

import sys, json, os, re, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.db import get_db, DEFAULT_DB_PATH
from lib.gematria import compute_all, find_divine_name_matches, DIVINE_NAMES
from lib.connections.pardes import LEVELS as PARDES_LEVELS


# ─── Database connection (persistent) ───
conn = get_db()


# ─── Tool definitions with JSON Schema ───
TOOLS = [
    {
        "name": "scripture_verse",
        "description": "Look up a verse with its pre-computed passage guide — includes all connections grouped by layer, gematria, quality, and PaRDeS levels",
        "inputSchema": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book ID (gen, exo, isa, matt, 1ne, etc.)"},
                "chapter": {"type": "integer"},
                "verse": {"type": "integer"},
            },
            "required": ["book", "chapter", "verse"],
        },
    },
    {
        "name": "scripture_search",
        "description": "Search for verses by keyword in English text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "book": {"type": "string", "description": "Optional book filter"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scripture_gematria",
        "description": "Compute gematria for a Hebrew word or look up values by number",
        "inputSchema": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "Hebrew word (e.g., יהוה)"},
                "value": {"type": "integer", "description": "Look up verses with this gematria value"},
            },
        },
    },
    {
        "name": "scripture_connections",
        "description": "Get all connections for a verse, with quality and PaRDeS filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                "layer": {"type": "string", "description": "Filter by layer"},
                "min_quality": {"type": "string", "description": "Minimum quality (probable, suggested, speculative)"},
            },
            "required": ["verse"],
        },
    },
    {
        "name": "scripture_intertext",
        "description": "Get intertextual connections for a verse — quotations, allusions, echoes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verse": {"type": "string", "description": "Verse ID"},
            },
            "required": ["verse"],
        },
    },
    {
        "name": "scripture_search_xlingual",
        "description": "Search across Hebrew, Greek, AND English simultaneously using entity alignment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Word to search for"},
                "language": {"type": "string", "description": "all, english, hebrew, greek"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scripture_sod",
        "description": "Explore hidden (Sod-level) patterns — atbash, acrostics, advanced gematria, hidden names",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verse": {"type": "string", "description": "Verse to analyze"},
                "atbash": {"type": "string", "description": "Word to decode via Atbash"},
                "acrostic": {"type": "string", "description": "Book ID to scan for acrostics"},
            },
        },
    },
    {
        "name": "scripture_passage_guide",
        "description": "Get the pre-computed passage guide for a verse — instant access to all connections, gematria, and quality distribution",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
            },
            "required": ["verse"],
        },
    },
    {
        "name": "scripture_pardes",
        "description": "Show connections grouped by PaRDeS interpretation level (P'shat, Remez, Drash, Sod)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verse": {"type": "string", "description": "Verse ID"},
                "level": {"type": "string", "description": "Filter to one level: p'shat, remez, drash, sod"},
            },
            "required": ["verse"],
        },
    },
    {
        "name": "scripture_info",
        "description": "Get database statistics — total verses, connections per layer, quality distribution",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

CONNECTION_TYPE_MAP = {
    "linguistic": "📝 Linguistic",
    "numerical": "🔢 Numerical",
    "structural": "📐 Structural",
    "intertextual": "📖 Intertextual",
    "textual": "📜 Textual",
    "geographic": "🌍 Geographic",
    "chronological": "📅 Chronological",
    "interpretive": "💭 Interpretive",
    "frequency": "📊 Frequency",
    "symbolic": "🔮 Symbolic",
}


# ─── Handle MCP JSON-RPC messages ───

def handle_request(request):
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    # MCP protocol methods
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}}

    if method == "list_tools":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "call_tool":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = execute_tool(tool_name, args)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False, default=str)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

    if method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def execute_tool(name, args):
    if name == "scripture_verse":
        book, ch, v = args["book"], int(args["chapter"]), int(args["verse"])
        vid = f"{book}.{ch}.{v}"
        result = conn.execute("""
            SELECT v.*, b.title as book_title, b.work_id
            FROM verses v JOIN books b ON b.id = v.book_id WHERE v.id = ?
        """, (vid,)).fetchone()
        if not result:
            return {"error": f"Verse {vid} not found"}
        r = dict(result)

        # Get passage guide for instant context
        guide = conn.execute("SELECT * FROM passage_guides WHERE verse_id = ?", (vid,)).fetchone()
        guide_data = json.loads(guide["connections_json"]) if guide else {}

        return {
            "reference": f"{r['book_title']} {ch}:{v}",
            "text_english": r["text_english"],
            "text_hebrew": r.get("text_hebrew") or None,
            "text_greek": r.get("text_greek") or None,
            "connection_layers": list(guide_data.keys()) if guide_data else [],
            "total_connections": sum(len(v) for v in guide_data.values()) if guide_data else 0,
            "connections_by_layer": {CONNECTION_TYPE_MAP.get(k, k): len(v) for k, v in guide_data.items()} if guide_data else {},
        }

    if name == "scripture_search":
        query = args["query"]
        book = args.get("book")
        limit = int(args.get("limit", 20))
        sql = "SELECT v.id, v.text_english, b.title FROM verses v JOIN books b ON b.id = v.book_id WHERE v.text_english LIKE ?"
        params = [f"%{query}%"]
        if book:
            sql += " AND v.book_id = ?"
            params.append(book)
        sql += " LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return {"query": query, "count": len(rows), "results": [{"verse": r["id"], "text": r["text_english"][:200], "book": r["title"]} for r in rows]}

    if name == "scripture_gematria":
        if "word" in args:
            vals = compute_all(args["word"])
            matches = find_divine_name_matches(vals["standard"])
            return {"word": args["word"], "gematria": vals, "divine_name_matches": matches}
        if "value" in args:
            val = args["value"]
            rows = conn.execute("""
                SELECT DISTINCT g.verse_id, g.word_hebrew, v.text_english, b.title
                FROM gematria g JOIN verses v ON v.id = g.verse_id JOIN books b ON b.id = v.book_id
                WHERE g.value_standard = ? LIMIT 20
            """, (val,)).fetchall()
            matches = find_divine_name_matches(val)
            return {"value": val, "matches": len(rows), "divine_names": matches, "results": [{"verse": r["verse_id"], "word": r["word_hebrew"]} for r in rows]}

    if name == "scripture_connections":
        vid = args["verse"]
        guide = conn.execute("SELECT connections_json FROM passage_guides WHERE verse_id = ?", (vid,)).fetchone()
        if not guide:
            return {"error": f"No passage guide for {vid}"}
        data = json.loads(guide["connections_json"])
        layer_filter = args.get("layer")
        if layer_filter and layer_filter in data:
            data = {layer_filter: data[layer_filter]}
        elif layer_filter:
            return {layer_filter: []}
        return {"verse": vid, "layers": list(data.keys()), "connections": data}

    if name == "scripture_intertext":
        vid = args["verse"]
        rows = conn.execute("""
            SELECT c.type, c.subtype, c.strength, c.target_verse, v.text_english as target_text, b.title as target_book
            FROM connections c JOIN verses v ON v.id = c.target_verse JOIN books b ON b.id = v.book_id
            WHERE c.source_verse = ? AND c.layer = 'intertextual'
        """, (vid,)).fetchall()
        return {"verse": vid, "count": len(rows), "connections": [dict(r) for r in rows]}

    if name == "scripture_search_xlingual":
        query = args["query"]
        lang = args.get("language", "all")
        results = []
        if lang in ("all", "english"):
            rows = conn.execute("SELECT id, text_english FROM verses WHERE text_english LIKE ? LIMIT 20", (f"%{query}%",)).fetchall()
            results.extend({"verse": r["id"], "text": r["text_english"][:120], "language": "english"} for r in rows)
        if lang in ("all", "hebrew"):
            rows = conn.execute("SELECT v.id, v.text_hebrew, v.text_english FROM gematria g JOIN verses v ON v.id=g.verse_id WHERE g.word_hebrew LIKE ? LIMIT 20", (f"%{query}%",)).fetchall()
            seen = set()
            for r in rows:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    results.append({"verse": r["id"], "text": (r["text_hebrew"] or "")[:120], "english": r["text_english"][:60], "language": "hebrew"})
        return {"query": query, "total": len(results), "results": results}

    if name == "scripture_sod":
        from lib.sod import acrostic, atbash as atb, gematria_advanced, hidden_names
        results = {}
        if "verse" in args:
            vid = args["verse"]
            row = conn.execute("SELECT text_hebrew FROM verses WHERE id = ?", (vid,)).fetchone()
            if row and row["text_hebrew"]:
                results["gematria"] = gematria_advanced.analyze_verse_gematria(row["text_hebrew"])
                results["hidden_names"] = hidden_names.find_divine_name_gematria_matches(conn, vid)
            results["verse"] = vid
        if "atbash" in args:
            results["atbash"] = {"input": args["atbash"], "decoded": atb.decode_atbash(args["atbash"])}
        if "acrostic" in args:
            acro = acrostic.scan_book_for_acrostics(conn, args["acrostic"])
            results["acrostic"] = acro if acro else {"note": "No acrostic found"}
        return results

    if name == "scripture_passage_guide":
        vid = args["verse"]
        guide = conn.execute("SELECT * FROM passage_guides WHERE verse_id = ?", (vid,)).fetchone()
        if not guide:
            return {"error": f"No passage guide for {vid}"}
        g = dict(guide)
        result = {
            "verse": g["verse_id"],
            "text_english": g["text_english"],
            "connections": json.loads(g["connections_json"]),
            "layer_count": g["layer_count"],
            "total_connections": g["total_connections"],
        }
        if g.get("gematria_json") and g["gematria_json"] != "null":
            result["gematria"] = json.loads(g["gematria_json"])
        if g.get("quality_summary"):
            result["quality_summary"] = json.loads(g["quality_summary"])
        return result

    if name == "scripture_pardes":
        vid = args["verse"]
        level_filter = args.get("level")
        from lib.connections.pardes import get_pardes_level, LEVELS as PL
        guide = conn.execute("SELECT connections_json FROM passage_guides WHERE verse_id = ?", (vid,)).fetchone()
        if not guide:
            return {"error": f"No passage guide for {vid}"}
        data = json.loads(guide["connections_json"])
        by_pardes = {}
        for layer, items in data.items():
            for item in items:
                lvl = get_pardes_level(layer, item["type"])
                if level_filter and lvl != level_filter:
                    continue
                if lvl not in by_pardes:
                    info = PL.get(lvl, {})
                    by_pardes[lvl] = {"name": info.get("name", lvl), "hebrew": info.get("hebrew", ""), "connections": []}
                by_pardes[lvl]["connections"].append(item)
        if level_filter and level_filter not in by_pardes and level_filter in PL:
            by_pardes[level_filter] = {"name": PL[level_filter]["name"], "hebrew": PL[level_filter]["hebrew"], "connections": []}
        return {"verse": vid, "levels": by_pardes}

    if name == "scripture_info":
        layers = conn.execute("SELECT layer, COUNT(*) as c FROM connections GROUP BY layer ORDER BY layer").fetchall()
        quality = conn.execute("SELECT quality_level, COUNT(*) as c FROM connections GROUP BY quality_level").fetchall()
        pg = conn.execute("SELECT COUNT(*) as c FROM passage_guides").fetchone()["c"]
        return {
            "total_connections": sum(r["c"] for r in layers),
            "layers": {r["layer"]: r["c"] for r in layers},
            "quality": {r["quality_level"]: r["c"] for r in quality},
            "passage_guides": pg,
            "verses": conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()["c"],
            "tools_available": len(TOOLS),
        }

    return {"error": f"Unknown tool: {name}"}


# ─── Stdio JSON-RPC loop ───

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    main()
