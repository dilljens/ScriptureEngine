"""
Shared tool: verse lookup, passage guide, and comprehensive study verse.

Used by MCP (scripture_verse, scripture_passage_guide, scripture_study_verse),
HTTP API (/api/v1/verses/{ref}, /api/v1/verses/{ref}/guide),
and CLI (tools/verse.py).
"""

import json
import unicodedata
from collections import defaultdict
from lib.db import get_connections_by_layer, get_gematria_for_verse, get_verse_gematria_total
from lib.controls.calibration import get_quality_stars, get_quality_color
from lib.hebrew_util import transliterate, rtl_mark, strip_cantillation, clean_hebrew as clean_heb
from lib.greek_util import transliterate as greek_translit, clean_greek
from lib.morphology import parse as parse_morph
from lib.lexicon import normalize_lemma
from lib.api.consensus import get_consensus


def lookup_verse(conn, book, chapter, verse, version=None):
    """Look up a verse and return all data — text, gematria, connections, quality.

    Args:
        book: Book ID (gen, exo, isa, matt, 1ne, etc.)
        chapter: Chapter number
        verse: Verse number
        version: Preferred Bible version (WEB, KJV, etc.)

    Returns: dict with reference, text_english, text_hebrew, text_greek,
             connections grouped by layer, gematria, quality info,
             text_versions (available translations), available_languages
    """
    from lib.db import get_verse as db_get_verse

    result = db_get_verse(conn, book, chapter, verse)
    if not result:
        return {"error": f"Verse {book}.{chapter}.{verse} not found"}

    verse_id = result["id"]

    # Gematria
    gematria_words = get_gematria_for_verse(conn, verse_id)
    gematria_total = get_verse_gematria_total(conn, verse_id)

    # Greek isopsephy
    greek_words = conn.execute("""
        SELECT word_greek, lemma, morph, value_standard, value_ordinal
        FROM gematria_greek WHERE verse_id = ? ORDER BY word_index
    """, (verse_id,)).fetchall()
    greek_words = [dict(r) for r in greek_words]
    greek_total = sum(w["value_standard"] for w in greek_words) if greek_words else 0

    # Batch lookup definitions for Hebrew words
    heb_map = {}
    for w in gematria_words:
        raw = w.get("lemma", "")
        if raw:
            base = normalize_lemma(raw)
            if base:
                heb_map[raw] = base
    if heb_map:
        all_bases = list(set(heb_map.values()))
        placeholders = ",".join("?" for _ in all_bases)
        # Search both numeric and H-prefixed forms
        search_terms = []
        for b in all_bases:
            search_terms.append(b)
            search_terms.append(f"H{b}")
        search_placeholders = ",".join("?" for _ in search_terms)
        def_rows = conn.execute(
            f"SELECT lemma, definition FROM lexicon WHERE lemma IN ({search_placeholders})",
            search_terms
        ).fetchall()
        defs = {}
        for r in def_rows:
            defs[r["lemma"]] = r["definition"]
        for w in gematria_words:
            raw = w.get("lemma", "")
            if raw in heb_map:
                base = heb_map[raw]
                for key in (base, f"H{base}"):
                    if key in defs and defs[key]:
                        w["definition"] = defs[key][:100]
                        break

    # Batch lookup definitions for Greek words (matched via normalized Greek text)
    gk_lemmas_unique = list(set(w.get("lemma", "") for w in greek_words if w.get("lemma")))
    gk_defs = {}
    if gk_lemmas_unique:
        for gk_lemma in gk_lemmas_unique:
            nfc_lemma = unicodedata.normalize("NFC", gk_lemma)
            row = conn.execute(
                "SELECT definition FROM lexicon WHERE hebrew = ? AND definition != '' LIMIT 1",
                (nfc_lemma,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT definition FROM lexicon WHERE hebrew LIKE ? AND definition != '' LIMIT 1",
                    (nfc_lemma + "%",)
                ).fetchone()
            if row and row["definition"]:
                gk_defs[gk_lemma] = row["definition"]
        for w in greek_words:
            l = w.get("lemma", "")
            if l in gk_defs:
                w["definition"] = gk_defs[l][:100]

    # Morphology parsing for gematria_words and greek_words
    for w in gematria_words:
        if w.get("morph"):
            w["morph_parsed"] = parse_morph(w["morph"])
    for w in greek_words:
        if w.get("morph"):
            w["morph_parsed"] = parse_morph(w["morph"])

    # Connections grouped by layer with quality
    connections = get_connections_by_layer(conn, verse_id)

    connection_detail = {}
    for layer, conns in connections.items():
        connection_detail[layer] = {
            "count": len(conns),
            "types": {},
        }
        for c in conns:
            t = c["type"]
            if t not in connection_detail[layer]["types"]:
                connection_detail[layer]["types"][t] = []

            quality = c.get("quality_level", "suggested")
            connection_detail[layer]["types"][t].append({
                "target": c.get("target_verse", ""),
                "subtype": c.get("subtype", ""),
                "strength": c.get("strength", 0),
                "confidence": c.get("confidence", 0),
                "discovered_by": c.get("discovered_by", ""),
                "quality": {
                    "level": quality,
                    "stars": get_quality_stars(quality),
                    "color": get_quality_color(quality),
                },
                "p_value": c.get("p_value"),
            })

    # Hebrew display enhancements (RTL-safe, transliterated, accent-stripped)
    raw_heb = result.get("text_hebrew") or ""
    heb_display = None
    if raw_heb:
        clean = clean_heb(raw_heb)
        heb_display = {
            "text": rtl_mark(clean),
            "clean": clean,
            "transliteration": transliterate(raw_heb),
        }

    # Greek display (LTR, transliterated)
    raw_greek = result.get("text_greek") or ""
    greek_disp = None
    if raw_greek:
        greek_disp = {
            "text": raw_greek,
            "clean": clean_greek(raw_greek),
            "transliteration": greek_translit(raw_greek),
        }

    # Consensus data — only for verses with original-language text
    consensus = None
    if result.get("has_hebrew") or result.get("has_greek"):
        cdata = get_consensus(conn, verse_id)
        if cdata["tradition_count"] > 0:
            consensus = {
                "tradition_count": cdata["tradition_count"],
                "traditions": cdata["traditions"],
            }

    # Get available text versions
    version_rows = conn.execute(
        "SELECT version, language, is_default, text FROM text_resources WHERE verse_id = ?",
        (verse_id,)
    ).fetchall()

    text_versions = {}
    for v in version_rows:
        text_versions[v["version"]] = {
            "text": v["text"],
            "language": v["language"],
            "is_default": bool(v["is_default"]),
        }

    # Find the default version or use the requested one
    if version:
        # User explicitly requested a version
        if version in text_versions:
            result["text_english"] = text_versions[version]["text"]
    elif text_versions:
        # Find the default version
        default = None
        for vname, vdata in text_versions.items():
            if vdata.get("is_default"):
                default = vname
                break
        if default is None:
            # First available is default
            default = list(text_versions.keys())[0]
        result["text_english"] = text_versions[default]["text"]

    return {
        "reference": f"{result.get('book_title', book)} {chapter}:{verse}",
        "verse_id": verse_id,
        "text_english": result.get("text_english", ""),
        "text_hebrew": result.get("text_hebrew") or None,
        "text_greek": result.get("text_greek") or None,
        "text_versions": text_versions if text_versions else None,
        "hebrew_display": heb_display,
        "greek_display": greek_disp,
        "book": result.get("book_title", book),
        "book_id": book,
        "chapter": chapter,
        "verse": verse,
        "languages": {
            "has_hebrew": bool(result.get("has_hebrew")),
            "has_greek": bool(result.get("has_greek")),
            "hebrew_gematria_words": len(gematria_words),
            "hebrew_total_gematria": gematria_total if any(v for v in gematria_total.values()) else None,
            "greek_isopsephy_words": len(greek_words),
            "greek_total_isopsephy": greek_total,
        },
        "available_languages": {
            "hebrew": bool(result.get("has_hebrew")),
            "greek": bool(result.get("has_greek")),
            "greek_lxx": bool(not result.get("has_greek") and result.get("text_versions", {}) and any(
                v.get("language") == "grc" for v in result.get("text_versions", {}).values()
            )),
            "latin": "lxx" in str(result.get("book_id", "")),
        },
        "gematria_words": gematria_words[:20] if gematria_words else [],
        "greek_words": greek_words[:20] if greek_words else [],
        "connections": connection_detail if connection_detail else None,
        "total_connections": sum(d["count"] for d in connection_detail.values()) if connection_detail else 0,

        # Consensus data
        "consensus": consensus,
    }


def study_verse(conn, verse, max_reachable=10):
    """Complete verse study package — replaces 6+ separate tool calls.

    Returns verse text + all connections + gematria + entities + quality + sources
    + 1-hop reachable verses in ONE response.

    Args:
        verse: Verse ID (gen.1.1)
        max_reachable: Max 1-hop neighbors to include (default 10)

    Returns: dict with everything an LLM needs for deep verse analysis
    """
    parts = verse.split(".")
    if len(parts) < 3:
        return {"error": f"Invalid verse ID: {verse}. Use format: book.chapter.verse (e.g., gen.1.1)"}

    book, chapter, vnum = parts[0], int(parts[1]), int(parts[2])
    base = lookup_verse(conn, book, chapter, vnum)
    if "error" in base:
        return base

    from lib.api.graph import graph_entities, graph_reachable
    from lib.api.sources import get_sources_for_verse
    from lib.connections.pardes import get_pardes_level, LEVELS as PARDES_LEVELS

    # Add entities
    entities = graph_entities(conn, verse, min_confidence=0.3)
    base["entities"] = entities.get("entities", [])

    # Add sources/provenance
    sources = get_sources_for_verse(conn, verse)
    base["sources"] = sources.get("scholars", [])

    # Add 1-hop reachable verses with text
    reachable = graph_reachable(conn, verse, max_depth=1, limit=max_reachable)
    base["reachable"] = reachable.get("by_depth", {}).get(1, [])

    # Add PaRDeS-level-sorted connections
    if base.get("connections"):
        pardes_grouped = defaultdict(list)
        for layer, data in base["connections"].items():
            pl = get_pardes_level(layer)
            pardes_grouped[pl].append({
                "layer": layer,
                "count": data["count"],
                "types": data["types"],
            })
        base["connections_by_pardes"] = {
            level: pardes_grouped[level]
            for level in ["p'shat", "remez", "drash", "sod"]
            if pardes_grouped[level]
        }

    # Add quality summary as star ratings
    if base.get("connections"):
        total = base.get("total_connections", 0)
        # Count by quality level across all connection types
        quality_counts = defaultdict(int)
        for layer_data in base["connections"].values():
            for type_name, type_conns in layer_data.get("types", {}).items():
                for c in type_conns:
                    q = c.get("quality", {}).get("level", "suggested")
                    quality_counts[q] += 1
        base["quality_summary"] = {
            "total_connections": total,
            "by_level": dict(quality_counts),
        }

    return base


def passage_guide(conn, verse, guide_cache=None):
    """Get the pre-computed passage guide for a verse — instant access.

    Args:
        verse: Verse ID (gen.1.1)
        guide_cache: Optional dict for RAM-cached lookups (web server)

    Returns: dict with connections_json, gematria, quality_summary, layer_count
    """
    # Try RAM cache first
    if guide_cache and verse in guide_cache:
        g = guide_cache[verse]
        result = {
            "verse": verse,
            "connections": json.loads(g["connections_json"]),
            "layer_count": g["layer_count"],
            "total_connections": g["total_connections"],
        }
        if g.get("gematria_json") and g["gematria_json"] != "null":
            result["gematria"] = json.loads(g["gematria_json"])
        if g.get("quality_summary"):
            result["quality_summary"] = json.loads(g["quality_summary"])
        return result

    # Fallback to SQLite
    guide = conn.execute(
        "SELECT * FROM passage_guides WHERE verse_id = ?", (verse,)
    ).fetchone()
    if not guide:
        return {"error": f"No passage guide for {verse}"}

    g = dict(guide)
    result = {
        "verse": g["verse_id"],
        "connections": json.loads(g["connections_json"]),
        "layer_count": g["layer_count"],
        "total_connections": g["total_connections"],
    }
    if g.get("gematria_json") and g["gematria_json"] != "null":
        result["gematria"] = json.loads(g["gematria_json"])
    if g.get("quality_summary"):
        result["quality_summary"] = json.loads(g["quality_summary"])
    return result
