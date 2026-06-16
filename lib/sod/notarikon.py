"""Notarikon — acronym detection from first/last letters.

Notarikon (נוטריקון) extracts hidden words by taking:
- The first letter of each word in a phrase
- The last letter of each word in a phrase
- The first AND last letters alternating
- Specific letters marked in Masoretic notation
"""

from ..gematria import extract_consonants


def first_letters(text):
    """Extract the first Hebrew letter from each word in a text."""
    words = text.split()
    result = []
    for w in words:
        cons = extract_consonants(w)
        if cons:
            result.append(cons[0])
    return "".join(result)


def last_letters(text):
    """Extract the last Hebrew letter from each word in a text."""
    words = text.split()
    result = []
    for w in words:
        cons = extract_consonants(w)
        if cons:
            result.append(cons[-1])
    return "".join(result)


def first_and_last(text):
    """Extract first+last letters paired from each word."""
    words = text.split()
    result = []
    for w in words:
        cons = extract_consonants(w)
        if len(cons) >= 2:
            result.append(cons[0])
            result.append(cons[-1])
        elif cons:
            result.append(cons[0])
    return "".join(result)


def find_notarikon_patterns(conn, book_id=None):
    """Find notarikon patterns in Hebrew verses.
    
    For each verse with Hebrew text, extract first/last letters
    and check if they form known biblical names or meaningful patterns.
    """
    from ..db import get_db
    
    query = """
        SELECT v.id, v.text_hebrew
        FROM verses v
        WHERE v.has_hebrew = 1 AND v.text_hebrew != ''
    """
    params = []
    if book_id:
        query += " AND v.book_id = ?"
        params.append(book_id)
    query += " LIMIT 1000"
    
    rows = conn.execute(query, params).fetchall()
    
    # Names we're looking for in notarikon patterns
    target_names = {"יהוה": "YHWH",
                    "אלהים": "Elohim",
                    "ישראל": "Israel",
                    "אמן": "Amen",
                    "משיח": "Messiah",
                    }
    
    results = []
    for r in rows:
        heb = r["text_hebrew"]
        fl = first_letters(heb)
        ll = last_letters(heb)
        
        for name, meaning in target_names.items():
            if name in fl:
                results.append({
                    "verse": r["id"],
                    "pattern_type": "notarikon_first",
                    "found": name,
                    "meaning": meaning,
                    "context": fl[:20],
                })
            if name in ll:
                results.append({
                    "verse": r["id"],
                    "pattern_type": "notarikon_last",
                    "found": name,
                    "meaning": meaning,
                    "context": ll[:20],
                })
    
    return results
