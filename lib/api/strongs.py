"""
Shared tool: Strong's definition lookup.
"""


def strongs_lookup(conn, lemma=None, word=None):
    """Look up Strong's definition for a Hebrew or Greek word.

    Args:
        lemma: Strong's number (e.g., H430, G26)
        word: Hebrew or Greek word text to search for

    Returns: dict with lemma, hebrew, transliteration, definition,
             part_of_speech, root_letters
    """
    if not lemma and not word:
        return {"error": "Provide either lemma or word"}

    if lemma:
        # Normalize: strip leading zeros from number portion
        clean = lemma.strip()
        if clean[0:1].isalpha() and clean[1:].isdigit():
            prefix = clean[0]
            num = int(clean[1:])
            clean = f"{prefix}{num}"

        row = conn.execute("""
            SELECT lemma, hebrew, transliteration, definition,
                   part_of_speech, root_letters
            FROM lexicon WHERE lemma = ?
        """, (clean,)).fetchone()

        if row:
            return dict(row)
        return {"error": f"Lemma '{lemma}' not found in lexicon"}

    if word:
        # Search by word text in lexicon
        rows = conn.execute("""
            SELECT lemma, hebrew, transliteration, definition,
                   part_of_speech, root_letters
            FROM lexicon WHERE hebrew = ? OR lemma = ?
            LIMIT 20
        """, (word, word)).fetchall()

        if rows:
            result = [dict(r) for r in rows]
            if len(result) == 1:
                return result[0]
            return result

        # Fallback: search gematria table for Hebrew word
        rows = conn.execute("""
            SELECT DISTINCT g.lemma, l.hebrew, l.transliteration,
                   l.definition, l.part_of_speech, l.root_letters
            FROM gematria g
            LEFT JOIN lexicon l ON l.lemma = g.lemma
            WHERE g.word_hebrew = ? AND g.lemma != ''
            LIMIT 5
        """, (word,)).fetchall()

        if rows:
            result = [dict(r) for r in rows]
            if len(result) == 1:
                return result[0]
            return result

        # Fallback: search Greek gematria table
        rows = conn.execute("""
            SELECT DISTINCT g.lemma, g.word_greek AS hebrew,
                   l.transliteration, l.definition,
                   l.part_of_speech, l.root_letters
            FROM gematria_greek g
            LEFT JOIN lexicon l ON l.lemma = g.lemma
            WHERE g.word_greek = ? AND g.lemma != ''
            LIMIT 5
        """, (word,)).fetchall()

        if rows:
            result = [dict(r) for r in rows]
            if len(result) == 1:
                return result[0]
            return result

        return {"error": f"Word '{word}' not found in lexicon"}
