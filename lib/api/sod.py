"""
Shared tool: hidden (Sod-level) patterns — atbash, acrostics, advanced gematria.

Used by MCP (scripture_sod),
HTTP API (/api/v1/sod),
and CLI (tools/sod.py).
"""

from lib.sod import acrostic, atbash as atb, gematria_advanced, hidden_names
from lib.sod.notarikon import first_letters, last_letters


def hidden_patterns(conn, verse=None, atbash_word=None, acrostic_book=None):
    """Explore hidden (Sod-level) patterns — atbash, acrostics, advanced gematria.

    Args:
        verse: Verse ID to analyze for advanced gematria
        atbash_word: Hebrew word to decode via Atbash
        acrostic_book: Book ID to scan for acrostics

    Returns: dict with requested pattern analyses
    """
    result = {}

    if atbash_word:
        result["atbash"] = {
            "input": atbash_word,
            "decoded": atb.decode_atbash(atbash_word),
        }

    if acrostic_book:
        acro = acrostic.scan_book_for_acrostics(conn, acrostic_book)
        result["acrostic"] = (
            acro if acro else {"note": "No acrostic found in this book"}
        )

    if verse:
        row = conn.execute(
            "SELECT text_hebrew, text_english FROM verses WHERE id = ?", (verse,)
        ).fetchone()
        if not row:
            result["verse_error"] = f"Verse {verse} not found"
        else:
            result["verse"] = verse
            result["text_english"] = row["text_english"][:200]
            if row["text_hebrew"]:
                result["gematria"] = gematria_advanced.analyze_verse_gematria(
                    row["text_hebrew"]
                )
                result["hidden_names"] = hidden_names.find_divine_name_gematria_matches(
                    conn, verse
                )
                result["notarikon"] = {
                    "first_letters": first_letters(row["text_hebrew"]),
                    "last_letters": last_letters(row["text_hebrew"]),
                }
            else:
                result["note"] = "No Hebrew text available for this verse"

    return result
