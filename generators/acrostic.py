"""Acrostic generator — acrostic connections.

Detects Hebrew alphabetic acrostics in the text and creates connections
between verses at symmetric letter positions.

Known acrostic chapters: Psalm 111, 112, 119, 145; Lamentations 1-4;
Proverbs 31:10-31; select other passages.
"""

import unicodedata

from lib.db import add_connection

# Hebrew alphabet in order (22 letters)
HEBREW_ALPHABET = list("אבגדהוזחטיכלמנסעפצקרשת")

# Canonical acrostic chapters (book_id, chapter)
# These are well-established; the detector will also discover new ones
KNOWN_ACROSTICS = {
    ("psa", 111), ("psa", 112), ("psa", 119), ("psa", 145),
    ("lam", 1), ("lam", 2), ("lam", 3), ("lam", 4),
}


def strip_hebrew_marks(text):
    """Remove niqqud (vowel points) and cantillation marks from Hebrew text,
    returning only the base consonants."""
    if not text:
        return ""
    # Unicode blocks: Niqqud = U+0591–U+05C7, Cantillation = U+0591–U+05AF
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Skip combining marks (Mn = Mark, Nonspacing; Cf = Format)
        if cat.startswith("M") or cat == "Cf":
            continue
        # Keep Hebrew letters (U+05D0–U+05EA) and regular characters
        if "\u05d0" <= ch <= "\u05ea" or ch.isalpha() or ch.isspace():
            result.append(ch)
    return "".join(result)


def extract_first_letter(text):
    """Extract the first Hebrew consonant from text, after stripping marks."""
    cleaned = strip_hebrew_marks(text)
    for ch in cleaned:
        if "\u05d0" <= ch <= "\u05ea":
            return ch
    return None


def run(conn, book_ids=None):
    """Detect Hebrew acrostics and create connections.

    For each book/chapter, check if the first letter of each verse
    follows the Hebrew alphabet. If detected, create connections
    pairing symmetric letter positions.

    Returns count of connections created.
    """
    count = 0

    # Get all verses grouped by (book_id, chapter)
    query = """
        SELECT id, book_id, chapter, verse, text_hebrew
        FROM verses
        WHERE text_hebrew != '' AND text_hebrew IS NOT NULL
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND book_id IN ({placeholders})"
    query += " ORDER BY book_id, chapter, verse"
    rows = conn.execute(query).fetchall()

    # Group by (book_id, chapter)
    chapters = {}
    for r in rows:
        key = (r["book_id"], r["chapter"])
        if key not in chapters:
            chapters[key] = []
        chapters[key].append({
            "id": r["id"],
            "book_id": r["book_id"],
            "chapter": r["chapter"],
            "verse": r["verse"],
            "text_hebrew": r["text_hebrew"],
        })

    total_acrostics = 0
    detected = []

    for (book_id, chapter), verses in chapters.items():
        if len(verses) < 5:
            continue

        # Extract first letter of each verse
        first_letters = []
        for v in verses:
            letter = extract_first_letter(v["text_hebrew"])
            if letter:
                first_letters.append(letter)
            else:
                first_letters.append(None)

        if len(first_letters) < 5:
            continue

        # Check if the sequence matches the Hebrew alphabet
        # Try different starting positions
        matched_letters = 0
        match_start = None

        for start_idx in range(len(first_letters)):
            match_count = 0
            for i in range(start_idx, min(len(first_letters), start_idx + 22)):
                if first_letters[i] is not None:
                    alpha_idx = i - start_idx
                    if alpha_idx < 22 and first_letters[i] == HEBREW_ALPHABET[alpha_idx]:
                        match_count += 1

            if match_count >= len(first_letters) - start_idx and match_count >= 5 and match_count > matched_letters:
                    matched_letters = match_count
                    match_start = start_idx

        # If significant acrostic match found
        if matched_letters >= 10 or (book_id, chapter) in KNOWN_ACROSTICS:
            total_acrostics += 1
            detected.append((book_id, chapter, verses, match_start or 0, matched_letters))

    # Create connections for detected acrostics
    for book_id, chapter, verses, _start, _letter_count in detected:
        verse_list = [v for v in verses if extract_first_letter(v["text_hebrew"])]

        # Pair symmetric letter positions: Aleph↔Tav, Bet↔Shin, etc.
        # In a 22-letter acrostic, position i pairs with position 21-i
        pairs_created = set()
        for i in range(len(verse_list)):
            for j in range(i + 1, len(verse_list)):
                letter_i = extract_first_letter(verse_list[i]["text_hebrew"])
                letter_j = extract_first_letter(verse_list[j]["text_hebrew"])

                if letter_i is None or letter_j is None:
                    continue

                # Check if these are symmetric in the alphabet
                try:
                    idx_i = HEBREW_ALPHABET.index(letter_i)
                    idx_j = HEBREW_ALPHABET.index(letter_j)
                except ValueError:
                    continue

                # Symmetric pair: if the sum of their indices is 21 (א+ת=0+21=21, etc.)
                # or close to it (with some tolerance for missing letters)
                if idx_i + idx_j == 21:
                    pair = (min(verse_list[i]["id"], verse_list[j]["id"]),
                            max(verse_list[i]["id"], verse_list[j]["id"]))
                    if pair not in pairs_created:
                        pairs_created.add(pair)
                        try:
                            add_connection(conn, verse_list[i]["id"], verse_list[j]["id"],
                                          layer="structural",
                                          type_name="acrostic",
                                          subtype=f"{book_id}.{chapter}",
                                          strength=0.7,
                                          confidence=0.85,
                                          discovered_by="algorithm",
                                          metadata={
                                              "book": book_id,
                                              "chapter": chapter,
                                              "letter_a": letter_i,
                                              "letter_b": letter_j,
                                              "acrostic_type": "alphabetic",
                                              "verse_a_letter": idx_i,
                                              "verse_b_letter": idx_j,
                                          })
                            count += 1
                        except Exception:
                            pass

        # Also connect this acrostic chapter to other acrostic chapters
        for other_book, other_chapter, _, _, _ in detected:
            if (other_book, other_chapter) != (book_id, chapter):
                # Use first verses as hub
                hub_verse = verse_list[0]["id"]
                other_verses = [v for v in verses
                                if extract_first_letter(v["text_hebrew"])]
                if other_verses:
                    other_hub = other_verses[0]["id"]
                    try:
                        add_connection(conn, hub_verse, other_hub,
                                      layer="structural",
                                      type_name="acrostic",
                                      subtype="inter_chapter",
                                      strength=0.5,
                                      confidence=0.7,
                                      discovered_by="algorithm",
                                      metadata={
                                          "chapter_a": f"{book_id}.{chapter}",
                                          "chapter_b": f"{other_book}.{other_chapter}",
                                          "acrostic_type": "inter_chapter_link",
                                      })
                        count += 1
                    except Exception:
                        pass

    conn.commit()
    print(f"  Acrostic: {count} connections across {total_acrostics} acrostic chapters")
    return count
