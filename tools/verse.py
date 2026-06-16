#!/usr/bin/env python3
"""
MCP Tool: scripture_verse
Look up a verse by book, chapter, verse reference.

Usage: python3 verse.py '{"book": "gen", "chapter": 1, "verse": 1}'
       python3 verse.py '{"reference": "isa.6.1"}'
       python3 verse.py '{"reference": "Genesis 1:1"}'
"""

import sys
import json
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, DEFAULT_DB_PATH, get_verse, get_gematria_for_verse, get_verse_gematria_total, get_connections_by_layer


def parse_reference(ref):
    """Parse a scripture reference string like 'Genesis 1:1' or 'gen.1.1'."""
    # Try dot notation first: gen.1.1
    if "." in ref:
        parts = ref.split(".")
        if len(parts) == 3:
            try:
                return parts[0], int(parts[1]), int(parts[2])
            except ValueError:
                pass

    # Try colon notation: Genesis 1:1 or gen 1:1
    import re
    m = re.match(r"(\w+\s?\w*)\s+(\d+):(\d+)", ref)
    if m:
        book_raw = m.group(1).strip().lower().replace(" ", "_")
        chapter = int(m.group(2))
        verse = int(m.group(3))
        # Map common names to IDs
        book_map = {
            "genesis": "gen", "exodus": "exo", "leviticus": "lev", "numbers": "num",
            "deuteronomy": "deu", "joshua": "josh", "judges": "judg", "ruth": "ruth",
            "1_samuel": "1sam", "2_samuel": "2sam", "1_kings": "1kgs", "2_kings": "2kgs",
            "1_chronicles": "1chr", "2_chronicles": "2chr", "ezra": "ezra", "nehemiah": "neh",
            "esther": "esth", "job": "job", "psalms": "psa", "psalm": "psa",
            "proverbs": "prov", "ecclesiastes": "eccl", "song_of_solomon": "song",
            "solomon's_song": "song", "isaiah": "isa", "jeremiah": "jer",
            "lamentations": "lam", "ezekiel": "ezek", "daniel": "dan",
            "hosea": "hos", "joel": "joel", "amos": "amos", "obadiah": "obad",
            "jonah": "jonah", "micah": "mic", "nahum": "nah", "habakkuk": "hab",
            "zephaniah": "zeph", "haggai": "hag", "zechariah": "zech", "malachi": "mal",
            "matthew": "matt", "mark": "mark", "luke": "luke", "john": "john",
            "acts": "acts", "romans": "rom", "1_corinthians": "1cor", "2_corinthians": "2cor",
            "galatians": "gal", "ephesians": "eph", "philippians": "phil", "colossians": "col",
            "1_thessalonians": "1thes", "2_thessalonians": "2thes",
            "1_timothy": "1tim", "2_timothy": "2tim", "titus": "titus", "philemon": "philem",
            "hebrews": "heb", "james": "james", "1_peter": "1pet", "2_peter": "2pet",
            "1_john": "1john", "2_john": "2john", "3_john": "3john", "jude": "jude",
            "revelation": "rev",
            "1_nephi": "1ne", "2_nephi": "2ne", "jacob": "jacob", "enos": "enos",
            "jarom": "jarom", "omni": "omni", "words_of_mormon": "wom",
            "mosiah": "mosiah", "alma": "alma", "helaman": "hel",
            "3_nephi": "3ne", "4_nephi": "4ne", "mormon": "morm", "ether": "ether",
            "moroni": "moro",
            "moses": "moses", "abraham": "abraham",
            "joseph_smith—matthew": "jsm", "joseph_smith_history": "jsh",
            "articles_of_faith": "aoff",
        }
        book_id = book_map.get(book_raw)
        if not book_id:
            # Try using the raw name
            book_id = book_raw
        return book_id, chapter, verse

    return None, None, None


def lookup(book, chapter, verse):
    """Look up a verse and return all related data."""
    conn = get_db()

    result = get_verse(conn, book, chapter, verse)
    if not result:
        return {"error": f"Verse {book}.{chapter}.{verse} not found"}

    verse_id = f"{book}.{chapter}.{verse}"

    # Get gematria if available
    gematria_words = get_gematria_for_verse(conn, verse_id)
    gematria_total = get_verse_gematria_total(conn, verse_id)

    # Get Greek isopsephy if available
    greek_words = conn.execute("""
        SELECT word_greek, lemma, morph, value_standard, value_ordinal
        FROM gematria_greek WHERE verse_id = ? ORDER BY word_index
    """, (verse_id,)).fetchall()
    greek_words = [dict(r) for r in greek_words]
    greek_total = sum(w["value_standard"] for w in greek_words) if greek_words else 0

    # Get connections grouped by layer with details
    connections = get_connections_by_layer(conn, verse_id)

    # Detailed connection view per layer with quality
    from lib.controls.calibration import get_quality_emoji, get_quality_color
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
                    "emoji": get_quality_emoji(quality),
                    "color": get_quality_color(quality),
                },
                "p_value": c.get("p_value"),
            })

    conn.close()

    return {
        "reference": f"{result.get('book_title', book)} {chapter}:{verse}",
        "verse_id": verse_id,
        "text_english": result.get("text_english", ""),
        "text_hebrew": result.get("text_hebrew", "") or None,
        "text_greek": result.get("text_greek", "") or None,
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
        "gematria_words": gematria_words[:20] if gematria_words else [],
        "greek_words": greek_words[:20] if greek_words else [],
        "connections": connection_detail if connection_detail else None,
        "total_connections": sum(d["count"] for d in connection_detail.values()) if connection_detail else 0,
    }


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    if "reference" in args:
        ref = args["reference"]
        book, chapter, verse = parse_reference(ref)
    else:
        book = args.get("book", "")
        chapter = args.get("chapter", 0)
        verse = args.get("verse", 0)

    if not book or not chapter or not verse:
        result = {"error": "Provide book, chapter, and verse"}
    else:
        result = lookup(book, chapter, verse)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
