"""Hidden divine name patterns in the Hebrew text.

Detects instances where divine names (YHWH, Elohim, etc.) appear
hidden within or across words — not as standalone names but embedded
in the letter sequence of other words.
"""

from ..gematria import extract_consonants

# Divine names to search for as hidden patterns
DIVINE_NAMES = {
    "יהוה": "YHWH",
    "אלהים": "Elohim",
    "אדני": "Adonai",
    "אל": "El",
    "שדי": "Shaddai",
}


def find_hidden_names_in_word(word):
    """Check if a Hebrew word contains a hidden divine name.

    Returns list of (name, position, meaning) tuples.
    """
    cons = extract_consonants(word)
    results = []
    for name, meaning in DIVINE_NAMES.items():
        pos = cons.find(name)
        if pos >= 0:
            results.append({
                "name": name,
                "meaning": meaning,
                "position": pos,
                "in_word": cons,
                "type": "embedded",
            })
    return results


def find_across_word_patterns(words):
    """Check if a sequence of words spells a divine name via:
    - Last letter of word N + first letter of word N+1
    - Consecutive letters across word boundaries
    """
    cons_words = [extract_consonants(w) for w in words if extract_consonants(w)]
    if not cons_words:
        return []

    results = []

    # Check: last + first across adjacent words
    for i in range(len(cons_words) - 1):
        combined = cons_words[i][-1] + cons_words[i + 1][0]
        for name, meaning in DIVINE_NAMES.items():
            if combined == name:
                results.append({
                    "type": "across_words",
                    "pattern": f"word_{i}_last + word_{i+1}_first",
                    "found": name,
                    "meaning": meaning,
                    "words": f"{cons_words[i][-1]} + {cons_words[i+1][0]}",
                })

    # Check: every other letter across words (skip-letter pattern)
    for skip in (1, 2, 3):
        all_letters = "".join(cons_words)
        selected = all_letters[::skip]
        for name, meaning in DIVINE_NAMES.items():
            if name in selected:
                results.append({
                    "type": f"skip_{skip}_pattern",
                    "found": name,
                    "meaning": meaning,
                    "in_sequence": selected[:40],
                })

    return results


def find_divine_name_gematria_matches(conn, verse_id):
    """For a given verse, check if gematria values match divine names.

    Uses the existing gematria data to find hidden divine name
    value matches in the verse's words.
    """
    from ..gematria import find_divine_name_matches

    words = conn.execute("""
        SELECT word_hebrew, value_standard FROM gematria
        WHERE verse_id = ? ORDER BY word_index
    """, (verse_id,)).fetchall()

    results = []
    for w in words:
        matches = find_divine_name_matches(w["value_standard"])
        for m in matches:
            results.append({
                "word": w["word_hebrew"],
                "value": w["value_standard"],
                "divine_name": m["name"],
                "hebrew": m["hebrew"],
            })

    return results
