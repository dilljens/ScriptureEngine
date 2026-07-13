"""
Shared tool: gematria lookup and value search.

Used by MCP (scripture_gematria),
HTTP API (/api/v1/gematria),
and CLI (tools/gematria.py).
"""

from lib.gematria import compute_all, find_divine_name_matches
from lib.hebrew_util import rtl_mark, transliterate


def gematria_lookup(conn, word=None, value=None, system="standard"):
    """Compute gematria for a Hebrew word or look up verses by value.

    Args:
        word: Hebrew word (e.g., יהוה)
        value: Numerical value to search for
        system: 'standard', 'ordinal', or 'reduced' (default 'standard')

    Returns: dict with gematria values and/or verse matches
    """
    if word:
        vals = compute_all(word)
        matches = find_divine_name_matches(vals["standard"])
        return {
            "word": word,
            "hebrew_display": {
                "text": rtl_mark(word),
                "transliteration": transliterate(word, strip_accents=False),
            },
            "gematria": vals,
            "divine_name_matches": matches,
        }

    if value is not None:
        col = {
            "standard": "value_standard",
            "ordinal": "value_ordinal",
            "reduced": "value_reduced",
        }.get(system, "value_standard")

        rows = conn.execute(
            f"""
            SELECT DISTINCT g.verse_id, g.word_hebrew, g.{col},
                   v.text_english, b.title
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE g.{col} = ? LIMIT 30
        """,
            (value,),
        ).fetchall()

        matches = find_divine_name_matches(value)
        return {
            "value": value,
            "system": system,
            "total": len(rows),
            "divine_name_matches": matches,
            "results": [
                {
                    "verse": r["verse_id"],
                    "word": r["word_hebrew"],
                    "hebrew_display": {
                        "text": rtl_mark(r["word_hebrew"]),
                        "transliteration": transliterate(r["word_hebrew"]),
                    },
                    "text": r["text_english"][:120],
                    "book": r["title"],
                }
                for r in rows
            ],
        }

    return {"error": "Provide word or value"}
