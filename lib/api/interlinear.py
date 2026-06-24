"""Interlinear tool — word-by-word verse analysis.

Returns each word with: original text, transliteration, Strong's number,
parsed morphology, and definition.

Used by MCP (scripture_interlinear) and CLI.
"""

from lib.db import get_verse
from lib.hebrew_util import transliterate as heb_translit, clean_hebrew
from lib.greek_util import transliterate as gr_translit
from lib.morphology import parse as parse_morph


def get_interlinear(conn, book, chapter, verse):
    """Get word-by-word interlinear analysis of a verse.

    Args:
        book: Book ID (gen, exo, john, etc.)
        chapter: Chapter
        verse: Verse number

    Returns:
        Dict with reference, verse_id, words array (each with text, translit,
        strongs, morph, morph_parsed, definition)
    """
    verse_id = f"{book}.{chapter}.{verse}"
    result = get_verse(conn, book, chapter, verse)
    if not result:
        return {"error": f"Verse {verse_id} not found"}

    words = []

    # Hebrew words
    heb_words = conn.execute(
        """SELECT word_hebrew, lemma, morph, value_standard
           FROM gematria WHERE verse_id = ? ORDER BY word_index""",
        (verse_id,)
    ).fetchall()
    heb_words = [dict(w) for w in heb_words]

    # Batch-fetch definitions for Hebrew lemmas
    heb_lemmas = [w["lemma"] for w in heb_words if w.get("lemma")]
    defs = {}
    if heb_lemmas:
        placeholders = ",".join("?" for _ in heb_lemmas)
        rows = conn.execute(
            f"SELECT lemma, definition FROM lexicon WHERE lemma IN ({placeholders})",
            heb_lemmas
        ).fetchall()
        for r in rows:
            defs[r["lemma"]] = r["definition"]

    for w in heb_words:
        word_data = {
            "text": w["word_hebrew"],
            "transliteration": heb_translit(w["word_hebrew"]),
            "type": "hebrew",
        }
        if w.get("lemma"):
            word_data["strongs"] = w["lemma"]
            word_data["definition"] = defs.get(w["lemma"], "")[:120]
        if w.get("morph"):
            word_data["morph"] = w["morph"]
            word_data["morph_parsed"] = parse_morph(w["morph"])
        words.append(word_data)

    # Greek words
    gr_words = conn.execute(
        """SELECT word_greek, lemma, morph, value_standard
           FROM gematria_greek WHERE verse_id = ? ORDER BY word_index""",
        (verse_id,)
    ).fetchall()
    gr_words = [dict(w) for w in gr_words]

    gr_lemmas = [w["lemma"] for w in gr_words if w.get("lemma")]
    gr_defs_map = {}
    if gr_lemmas:
        placeholders = ",".join("?" for _ in gr_lemmas)
        rows = conn.execute(
            f"SELECT lemma, definition FROM lexicon WHERE lemma IN ({placeholders})",
            gr_lemmas
        ).fetchall()
        for r in rows:
            gr_defs_map[r["lemma"]] = r["definition"]

    for w in gr_words:
        word_data = {
            "text": w["word_greek"],
            "transliteration": gr_translit(w["word_greek"]),
            "type": "greek",
        }
        if w.get("lemma"):
            word_data["strongs"] = w["lemma"]
            word_data["definition"] = gr_defs_map.get(w["lemma"], "")[:120]
        if w.get("morph"):
            word_data["morph"] = w["morph"]
            word_data["morph_parsed"] = parse_morph(w["morph"])
        words.append(word_data)

    return {
        "reference": f"{result.get('book_title', book)} {chapter}:{verse}",
        "verse_id": verse_id,
        "word_count": len(words),
        "words": words,
    }
