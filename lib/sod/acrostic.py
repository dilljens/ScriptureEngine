"""Acrostic detection — Hebrew alphabetical patterns in verses.

Detects when the first letters of consecutive verses form the
Hebrew alphabet (א-ת), or other meaningful letter sequences.

Known acrostics in the Hebrew Bible:
  - Psalm 119: 22 stanzas of 8 verses, each stanza starts with next letter
  - Psalm 111-112: Each half-verse starts with consecutive letter
  - Psalm 145: Each verse starts with consecutive letter (missing Nun)
  - Proverbs 31:10-31: 22 verses, each starts with next letter
  - Lamentations 1-4: Chapters 1-2 have 22 verses each;
    chapter 3 has 66 verses (triple alphabetical);
    chapter 4 has 22 verses
  - Psalms 9-10: Partial acrostic
  - Nahum 1:2-8: Partial acrostic
"""

from ..gematria import extract_consonants


# Hebrew alphabet in order
ALEPH_BET = list("אבגדהוזחטיכלמנסעפצקרשת")


def get_first_hebrew_letter(text):
    """Get the first Hebrew consonant from a text string."""
    cons = extract_consonants(text)
    return cons[0] if cons else None


def detect_acrostic(verses):
    """Detect if a list of verses forms a Hebrew alphabetical acrostic.
    
    Args:
        verses: list of dicts with 'text_hebrew' or 'id' keys
    
    Returns:
        dict with acrostic info, or None
    """
    if len(verses) < 5:
        return None
    
    # Extract first Hebrew letter from each verse
    first_letters = []
    for v in verses:
        eh = v.get("text_hebrew", "")
        if not eh:
            continue
        fl = get_first_hebrew_letter(eh)
        if fl:
            first_letters.append(fl)
        else:
            first_letters.append(None)
    
    if len(first_letters) < 5:
        return None
    
    # Check: standard 22-verse alphabetical acrostic
    for start in range(max(0, len(first_letters) - 22 + 1)):
        segment = first_letters[start:start + 22]
        if None not in segment:
            matches = sum(1 for i, letter in enumerate(segment) 
                         if i < len(ALEPH_BET) and letter == ALEPH_BET[i])
            if matches >= 20:  # 20+ out of 22 matches
                end = start + 22
                return {
                    "type": "standard_acrostic",
                    "start_index": start,
                    "end_index": end,
                    "matches": matches,
                    "total": 22,
                    "letters_found": segment[:22],
                    "confidence": round(matches / 22, 2),
                }
    
    # Check: Psalm 119 style (22 stanzas × 8 verses)
    if len(first_letters) >= 176:  # 22 × 8
        for stanza_size in (8, 16):
            stanza_count = 22
            total = stanza_size * stanza_count
            if len(first_letters) < total:
                continue
            
            matches = 0
            for s in range(stanza_count):
                idx = s * stanza_size
                if idx < len(first_letters) and first_letters[idx] == ALEPH_BET[s]:
                    matches += 1
            
            if matches >= 18:
                return {
                    "type": "stanza_acrostic",
                    "stanza_size": stanza_size,
                    "matches": matches,
                    "total": stanza_count,
                    "confidence": round(matches / stanza_count, 2),
                }
    
    return None


def scan_book_for_acrostics(conn, book_id):
    """Scan an entire book for acrostic patterns."""
    from ..db import get_db
    
    rows = conn.execute("""
        SELECT id, chapter, verse, text_hebrew
        FROM verses
        WHERE book_id = ? AND has_hebrew = 1
        ORDER BY chapter, verse
    """, (book_id,)).fetchall()
    
    verses = [dict(r) for r in rows]
    
    # Check whole book
    result = detect_acrostic(verses)
    if result:
        start_v = verses[result["start_index"]]
        end_v = verses[min(result["end_index"], len(verses) - 1)]
        result["book"] = book_id
        result["start_verse"] = f"{start_v['chapter']}:{start_v['verse']}"
        result["end_verse"] = f"{end_v['chapter']}:{end_v['verse']}"
        return result
    
    # Check per-chapter
    chapters = {}
    for v in verses:
        ch = v["chapter"]
        if ch not in chapters:
            chapters[ch] = []
        chapters[ch].append(v)
    
    for ch, ch_verses in sorted(chapters.items()):
        result = detect_acrostic(ch_verses)
        if result:
            start_v = ch_verses[result["start_index"]]
            end_v = ch_verses[min(result["end_index"], len(ch_verses) - 1)]
            return {
                "type": result["type"],
                "book": book_id,
                "chapter": ch,
                "start_verse": f"{ch}:{start_v['verse']}",
                "end_verse": f"{ch}:{end_v['verse']}",
                "matches": result["matches"],
                "confidence": result["confidence"],
                "letters_found": result.get("letters_found", [])[:15],
            }
    
    # Check for acrostics starting at later verse positions (like Prov 31:10-31)
    # This handles acrostics embedded within chapters
    for ch, ch_verses in sorted(chapters.items()):
        if len(ch_verses) < 22:
            continue
        # Try starting at each verse position
        for start_offset in range(1, len(ch_verses) - 22):
            segment = ch_verses[start_offset:start_offset + 22]
            result = detect_acrostic(segment)
            if result and result["confidence"] >= 0.9:
                start_v = segment[0]
                end_v = segment[-1]
                return {
                    "type": result["type"],
                    "book": book_id,
                    "chapter": ch,
                    "offset_verses": True,
                    "start_verse": f"{ch}:{start_v['verse']}",
                    "end_verse": f"{ch}:{end_v['verse']}",
                    "matches": result["matches"],
                    "confidence": result["confidence"],
                    "letters_found": result.get("letters_found", [])[:15],
                }
    
    return None
