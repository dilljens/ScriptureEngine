#!/usr/bin/env python3
"""MCP Tool: scripture_sod — Explore hidden/mystical (Sod) patterns.

The deepest level of PaRDeS interpretation. Discovers hidden patterns
in the Hebrew text that aren't visible on the surface.

Usage:
  python3 sod.py '{"verse": "gen.1.1"}'
  python3 sod.py '{"atbash": "ששך"}'
  python3 sod.py '{"acrostic": true, "book": "pro"}'
  python3 sod.py '{"gematria_advanced": true, "verse": "gen.1.1"}'
  python3 sod.py '{"hidden_names": true, "verse": "gen.1.1"}'
  python3 sod.py '{"scan": true, "book": "psa"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.sod import acrostic, atbash, gematria_advanced, hidden_names, notarikon


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())
    conn = get_db()
    result = {}

    # Atbash decode
    if "atbash" in args:
        word = args["atbash"]
        decoded = atbash.decode_atbash(word)
        result = {
            "input": word,
            "decoded": decoded,
            "method": "atbash",
        }

    # Notarikon patterns in a verse
    elif "notarikon" in args:
        verse = args["notarikon"]
        row = conn.execute("SELECT text_hebrew FROM verses WHERE id = ?", (verse,)).fetchone()
        if row and row["text_hebrew"]:
            heb = row["text_hebrew"]
            result = {
                "verse": verse,
                "first_letters": notarikon.first_letters(heb),
                "last_letters": notarikon.last_letters(heb),
                "first_and_last": notarikon.first_and_last(heb),
            }

    # Acrostic scan
    elif "acrostic" in args:
        book = args.get("book", "")
        if not book:
            result = {"error": "Provide book"}
        else:
            acro = acrostic.scan_book_for_acrostics(conn, book)
            result = acro or {"book": book, "acrostic": None, "note": "No acrostic pattern found"}

    # Advanced gematria
    elif "gematria_advanced" in args:
        verse = args.get("verse", "")
        if not verse:
            result = {"error": "Provide verse"}
        else:
            row = conn.execute("SELECT text_hebrew FROM verses WHERE id = ?", (verse,)).fetchone()
            if row and row["text_hebrew"]:
                patterns = gematria_advanced.analyze_verse_gematria(row["text_hebrew"])
                result = {"verse": verse, "patterns": patterns}
            else:
                result = {"verse": verse, "error": "No Hebrew text", "patterns": []}

    # Hidden name analysis
    elif "hidden_names" in args:
        verse = args["hidden_names"]
        words = conn.execute("""
            SELECT word_hebrew FROM gematria WHERE verse_id = ? ORDER BY word_index
        """, (verse,)).fetchall()

        hidden = []
        across = []
        for w in words:
            hidden.extend(hidden_names.find_hidden_names_in_word(w["word_hebrew"]))

        heb_words = [w["word_hebrew"] for w in words]
        if heb_words:
            across = hidden_names.find_across_word_patterns(heb_words)

        # Divine name gematria matches
        gem_matches = hidden_names.find_divine_name_gematria_matches(conn, verse)

        result = {
            "verse": verse,
            "hidden_in_words": hidden,
            "across_words": across,
            "divine_name_gematria": gem_matches,
        }

    # Full scan — all patterns for a verse
    elif "verse" in args:
        verse = args["verse"]
        vrow = conn.execute("""
            SELECT v.*, b.title as book_title FROM verses v
            JOIN books b ON b.id = v.book_id WHERE v.id = ?
        """, (verse,)).fetchone()

        if not vrow:
            result = {"error": "Verse not found"}
        else:
            result = {
                "verse": verse,
                "text_english": vrow["text_english"][:150],
                "sod_patterns": {},
            }

            if vrow["text_hebrew"]:
                # Advanced gematria
                result["sod_patterns"]["gematria"] = gematria_advanced.analyze_verse_gematria(vrow["text_hebrew"])

                # Notarikon
                result["sod_patterns"]["notarikon"] = {
                    "first_letters": notarikon.first_letters(vrow["text_hebrew"]),
                    "last_letters": notarikon.last_letters(vrow["text_hebrew"]),
                }

                # Hidden names in words
                words = conn.execute("""
                    SELECT word_hebrew FROM gematria WHERE verse_id = ? ORDER BY word_index
                """, (verse,)).fetchall()
                hidden = []
                for w in words:
                    hidden.extend(hidden_names.find_hidden_names_in_word(w["word_hebrew"]))
                result["sod_patterns"]["hidden_names"] = hidden

                # Divine name gematria
                result["sod_patterns"]["divine_gematria"] = hidden_names.find_divine_name_gematria_matches(conn, verse)

    # Full book scan
    elif "scan" in args:
        book = args.get("book", "")
        acro = acrostic.scan_book_for_acrostics(conn, book)
        result = {
            "book": book,
            "acrostic": acro,
        }

    else:
        result = {"error": "Provide verse, atbash, acrostic, gematria_advanced, hidden_names, notarikon, or scan"}

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
