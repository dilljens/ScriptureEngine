#!/usr/bin/env python3
"""MCP Tool: scripture_search_xlingual — Cross-lingual search.

Search across Hebrew, Greek, and English simultaneously.
Uses entity alignment to find the same concept across languages.

Usage:
  python3 search_xlingual.py '{"query": "God"}'
  python3 search_xlingual.py '{"query": "messiah", "language": "hebrew"}'
  python3 search_xlingual.py '{"query": "ἀγάπη", "language": "greek"}'
  python3 search_xlingual.py '{"query": "Jesus", "entities": true}'
  python3 search_xlingual.py '{"entity": "person.moses"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db

# Stopwords for English search
STOPWORDS = {"the", "and", "a", "an", "in", "of", "to", "for", "with",
             "on", "at", "by", "from", "that", "this", "is", "was", "be"}


def build_hebrew_like(word):
    """Build a LIKE pattern that matches Hebrew despite niqqud."""
    cons = ""
    for c in word:
        cp = ord(c)
        if (0x05D0 <= cp <= 0x05EA) or (0x05EF <= cp <= 0x05F2):
            cons += c
    return f"%{'%'.join(cons)}%" if cons else f"%{word}%"


def search_english(conn, query, limit=30):
    """Search English verse text."""
    rows = conn.execute("""
        SELECT v.id, v.text_english, b.title as book_title
        FROM verses v JOIN books b ON b.id = v.book_id
        WHERE v.text_english LIKE ?
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()
    return [dict(r) for r in rows]


def search_hebrew(conn, query, limit=30):
    """Search Hebrew text (strips niqqud for matching)."""
    # Search word-by-word through gematria table
    like_pattern = build_hebrew_like(query)
    rows = conn.execute("""
        SELECT DISTINCT v.id, v.text_hebrew, v.text_english,
               b.title as book_title
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.word_hebrew LIKE ?
        LIMIT ?
    """, (like_pattern, limit)).fetchall()
    return [dict(r) for r in rows]


def search_greek(conn, query, limit=30):
    """Search Greek text through gematria_greek table."""
    rows = conn.execute("""
        SELECT DISTINCT v.id, v.text_greek, v.text_english,
               b.title as book_title
        FROM gematria_greek g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.word_greek LIKE ? OR g.lemma LIKE ?
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit)).fetchall()
    return [dict(r) for r in rows]


def search_by_entity(conn, entity_id):
    """Find all verses mentioning a specific entity across all languages."""
    entity = conn.execute("""
        SELECT * FROM entity_links WHERE entity_id = ?
    """, (entity_id,)).fetchone()

    if not entity:
        return {"error": f"Entity '{entity_id}' not found"}

    entity = dict(entity)
    results = {"entity": entity, "verses": []}

    # Search by Hebrew name
    if entity.get("hebrew_name"):
        heb_pattern = build_hebrew_like(entity["hebrew_name"])
        rows = conn.execute("""
            SELECT DISTINCT v.id, v.text_hebrew, v.text_english,
                   b.title as book_title
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE g.word_hebrew LIKE ?
            LIMIT 30
        """, (heb_pattern,)).fetchall()
        for r in rows:
            results["verses"].append({
                "verse": r["id"],
                "language": "hebrew",
                "text": r["text_hebrew"][:100] if r["text_hebrew"] else "",
                "english": r["text_english"][:100] or "",
                "book": r["book_title"],
            })

    # Search by Greek name
    if entity.get("greek_name"):
        rows = conn.execute("""
            SELECT DISTINCT v.id, v.text_greek, v.text_english,
                   b.title as book_title
            FROM gematria_greek g
            JOIN verses v ON v.id = g.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE g.lemma LIKE ?
            LIMIT 20
        """, (f"%{entity['greek_name']}%",)).fetchall()
        for r in rows:
            results["verses"].append({
                "verse": r["id"],
                "language": "greek",
                "text": r["text_greek"][:100] if r["text_greek"] else "",
                "english": r["text_english"][:100] or "",
                "book": r["book_title"],
            })

    # Search by English name
    if entity.get("english_name"):
        rows = conn.execute("""
            SELECT v.id, v.text_english, b.title as book_title
            FROM verses v JOIN books b ON b.id = v.book_id
            WHERE v.text_english LIKE ?
            LIMIT 20
        """, (f"%{entity['english_name']}%",)).fetchall()
        for r in rows:
            results["verses"].append({
                "verse": r["id"],
                "language": "english",
                "text": r["text_english"][:100],
                "book": r["book_title"],
            })

    return results


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())
    conn = get_db()

    # Entity lookup mode
    if "entity" in args:
        result = search_by_entity(conn, args["entity"])
        print(json.dumps(result, indent=2, ensure_ascii=False))
        conn.close()
        return

    query = args.get("query", "")
    language = args.get("language", "all")
    include_entities = args.get("entities", False)
    limit = args.get("limit", 30)

    if not query:
        print(json.dumps({"error": "Provide a query"}))
        conn.close()
        return

    result = {"query": query, "results": []}

    # Search Hebrew
    if language in ("all", "hebrew"):
        heb = search_hebrew(conn, query, limit)
        for r in heb:
            result["results"].append({
                "verse": r["id"],
                "language": "hebrew",
                "text": r.get("text_hebrew", "")[:100],
                "english": r.get("text_english", "")[:100],
                "book": r.get("book_title", ""),
            })

    # Search Greek
    if language in ("all", "greek"):
        grk = search_greek(conn, query, limit)
        for r in grk:
            result["results"].append({
                "verse": r["id"],
                "language": "greek",
                "text": r.get("text_greek", "")[:100] if r.get("text_greek") else "",
                "english": r.get("text_english", "")[:100],
                "book": r.get("book_title", ""),
            })

    # Search English
    if language in ("all", "english"):
        eng = search_english(conn, query, limit)
        for r in eng:
            result["results"].append({
                "verse": r["id"],
                "language": "english",
                "text": r.get("text_english", "")[:100],
                "book": r.get("book_title", ""),
            })

    # Include entity matches
    if include_entities:
        # Find entities matching the query
        entities = conn.execute("""
            SELECT entity_id, english_name, hebrew_name, greek_name
            FROM entity_links
            WHERE english_name LIKE ? OR hebrew_name LIKE ? OR greek_name LIKE ?
            LIMIT 15
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        if entities:
            result["entity_matches"] = [dict(r) for r in entities]

    result["total"] = len(result["results"])

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
