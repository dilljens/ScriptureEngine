"""
Hebrew-specific parallelism detection.

Detects parallelism types that are only visible in the Hebrew text:
  - Cognate accusative: verb + object from same root (חלם חלום, "dreamed a dream")
  - Numerical parallelism: "three things... yea, four" (שלשה המה... וארבעה)
  - Hendiadys: two coordinated nouns expressing one idea
  - Merismus: paired opposites expressing totality (heaven and earth)

These types are invisible or weak in English translation but can be
detected via Hebrew morphological analysis from our WLC data.
"""

import re

# Known merismatic pairs (opposites that together mean "everything")
MERISMATIC_PAIRS = [
    ("שׁמים", "ארץ"),      # heaven and earth
    ("יום", "לילה"),        # day and night
    ("אור", "חשך"),        # light and darkness
    ("ימין", "שמאל"),      # right and left
    ("צפון", "דרום"),      # north and south
    ("מזרח", "מערב"),      # east and west
    ("עליון", "תחתון"),   # above and below
    ("אדם", "בהמה"),       # man and beast
    ("חי", "מת"),          # living and dead
    ("זכר", "נקבה"),       # male and female
    ("עבד", "בן־חורין"),   # slave and free (post-biblical but pattern exists)
    ("גר", "אזרח"),        # stranger and citizen
    ("עשיר", "רש"),        # rich and poor
    ("צדיק", "רשע"),       # righteous and wicked
    ("חכם", "כסיל"),       # wise and foolish
]


# Merismatic terms (single terms that imply pairs)
MERISMATIC_TERMS = {
    "כל": "all/every (implies totality)",
    "רב": "many/much (implies abundance)",
    "אין": "there is not (negation of totality)",
}


def extract_root(lemma):
    """Extract the triliteral root from a Strong's lemma.

    Stored as e.g., '7225' from 'b/7225' or '1254 a' from '1254 a'.
    We can't get the root directly from Strong's numbers without a root lexicon,
    but we can check for cognate accusative by other means.
    """
    # Strip prefixes like 'b/' or 'c/' or 'd/'
    if "/" in lemma:
        lemma = lemma.split("/")[-1]
    # Strip suffixes like ' a', ' b', etc.
    parts = lemma.split()
    return parts[0] if parts else lemma


def detect_cognate_accusative(conn, book_id, chapter=None, limit=30):
    """Detect cognate accusative constructions: verb + noun from same root.

    Example: 'בָּרָא... בְּרִיאָה' (created... creation) or
             'חָלַם חֲלוֹם' (dreamed a dream)
    """
    sql = """
        SELECT g1.verse_id, g1.word_hebrew as verb, g1.lemma as verb_lemma,
               g2.word_hebrew as noun, g2.lemma as noun_lemma,
               v.text_english
        FROM gematria g1
        JOIN gematria g2 ON g2.verse_id = g1.verse_id
            AND g2.word_index = g1.word_index + 1
        JOIN verses v ON v.id = g1.verse_id
        WHERE v.book_id = ?
    """
    params = [book_id]
    if chapter:
        sql += " AND v.chapter = ?"
        params.append(chapter)

    sql += " AND g1.morph LIKE 'HV%' AND g2.morph LIKE 'HN%'"  # verb followed by noun
    sql += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()

    results = []
    for r in rows:
        verb_lemma = extract_root(r["verb_lemma"])
        noun_lemma = extract_root(r["noun_lemma"])

        # Check if they share the same Strong's number (indicating same root)
        if verb_lemma and noun_lemma and verb_lemma == noun_lemma:
            results.append({
                "verse_id": r["verse_id"],
                "verb": r["verb"],
                "noun": r["noun"],
                "type": "cognate_accusative",
                "lemma": verb_lemma,
                "context": (r["text_english"] or "")[:120],
            })

    return results


def detect_numerical_parallelism(conn, book_id, limit=30):
    """Detect numerical parallelism: 'X things... X+1 things'.

    Hebrew pattern: 'שְׁלֹשָׁה הֵמָּה... וְאַרְבָּעָה...'
    English pattern: 'There are three things... yea, four...'
    """
    # Scan for number words followed by "things" or similar patterns
    rows = conn.execute("""
        SELECT v.id, v.chapter, v.verse, v.text_english FROM verses v
        WHERE v.book_id = ?
        AND (
            v.text_english LIKE '%three%yea%four%'
            OR v.text_english LIKE '%three%and%four%'
            OR v.text_english LIKE '%six%yea%seven%'
            OR v.text_english LIKE '%two%yea%three%'
            OR v.text_english LIKE '%seven%yea%eight%'
            OR v.text_english LIKE '%four%yea%five%'
            OR v.text_english REGEXP '[0-9]+ things.*[0-9]+'
        )
        LIMIT ?
    """, (book_id, limit)).fetchall()

    results = []
    for r in rows:
        # Identify which number pair is used
        text = r["text_english"]
        nums = re.findall(r'\b(three|four|five|six|seven|eight|two|ten|one|two|3|4|5|6|7|8|2|10|1|2)\b', text.lower())
        results.append({
            "verse_id": r["id"],
            "verse": f"{r['chapter']}:{r['verse']}",
            "text": text[:150],
            "type": "numerical_parallelism",
            "numbers_found": nums,
        })

    return results


def detect_merismus(conn, book_id, limit=30):
    """Detect merismus — paired opposites that express totality.

    Detection: find known merismatic pairs (heaven/earth, day/night, etc.)
    occurring in close proximity within a single verse.
    """
    results = []

    for term_a, term_b in MERISMATIC_PAIRS:
        rows = conn.execute("""
            SELECT v.id, v.chapter, v.verse, v.text_english, v.text_hebrew
            FROM verses v
            JOIN gematria g1 ON g1.verse_id = v.id
            JOIN gematria g2 ON g2.verse_id = v.id
            WHERE v.book_id = ?
            AND g1.word_hebrew LIKE ? AND g2.word_hebrew LIKE ?
            LIMIT ?
        """, (book_id, f"%{term_a}%", f"%{term_b}%", limit // 10)).fetchall()

        for r in rows:
            results.append({
                "verse_id": r["id"],
                "verse": f"{r['chapter']}:{r['verse']}",
                "text": (r["text_english"] or "")[:150],
                "type": "merismus",
                "pair": f"{term_a} / {term_b}",
            })

    return results


def detect_hendiadys(conn, book_id, limit=30):
    """Detect hendiadys — two coordinated nouns expressing one concept.

    Pattern in Hebrew: 'X ו-Y' (X and Y) where the pair functions as
    a single concept. Annotation: this requires semantic judgment,
    so we flag candidates for AI review rather than classifying definitively.

    Example: 'חֶסֶד וֶאֱמֶת' (chesed ve'emet — "lovingkindness and truth"
    often expressing the single concept of "faithful love")
    """
    rows = conn.execute("""
        SELECT v.id, v.chapter, v.verse, v.text_english
        FROM verses v
        WHERE v.book_id = ?
        AND v.text_english REGEXP '\\w+ and \\w+'
        AND v.text_english LIKE '% and %'
        LIMIT ?
    """, (book_id, limit)).fetchall()

    # We'll return candidates and let the AI (DeepSeek) classify them
    results = []
    for r in rows:
        matches = re.findall(r'(\w+)\s+and\s+(\w+)', r["text_english"])
        for m in matches:
            if len(m[0]) > 2 and len(m[1]) > 2:
                results.append({
                    "verse_id": r["id"],
                    "verse": f"{r['chapter']}:{r['verse']}",
                    "candidate_pair": f"{m[0]} and {m[1]}",
                    "context": (r["text_english"] or "")[:150],
                    "type": "hendiadys_candidate",
                    "note": "AI review needed: is this a hendiadys (two words = one concept) or a simple conjunction?",
                })

    return results


def detect_emblematic_parallelism(conn, book_id, limit=30):
    """Detect emblematic parallelism — simile/comparison in poetic verse.

    Pattern: 'As X... so Y...' using כְּ (as/like) or similar.
    """
    rows = conn.execute("""
        SELECT v.id, v.chapter, v.verse, v.text_english
        FROM verses v
        WHERE v.book_id = ?
        AND v.text_english REGEXP '\\bas\\b.*\\bso\\b'
        AND v.text_english REGEXP '\\blike\\b.*\\bso\\b'
        LIMIT ?
    """, (book_id, limit)).fetchall()

    return [
        {
            "verse_id": r["id"],
            "verse": f"{r['chapter']}:{r['verse']}",
            "text": (r["text_english"] or "")[:150],
            "type": "emblematic_parallelism",
        }
        for r in rows
    ]


def run_all_hebrew_parallelism(conn, book_id, chapter=None):
    """Run all Hebrew-specific parallelism detectors and return combined results."""
    results = {
        "book": book_id,
    }

    try:
        cognate = detect_cognate_accusative(conn, book_id, chapter)
        if cognate:
            results["cognate_accusative"] = cognate
    except Exception as e:
        results["cognate_accusative_error"] = str(e)

    try:
        numerical = detect_numerical_parallelism(conn, book_id)
        if numerical:
            results["numerical_parallelism"] = numerical
    except Exception as e:
        results["numerical_parallelism_error"] = str(e)

    try:
        merismus = detect_merismus(conn, book_id)
        if merismus:
            results["merismus"] = merismus
    except Exception as e:
        results["merismus_error"] = str(e)

    try:
        hendiadys = detect_hendiadys(conn, book_id)
        if hendiadys:
            results["hendiadys_candidates"] = hendiadys
    except Exception as e:
        results["hendiadys_error"] = str(e)

    try:
        emblematic = detect_emblematic_parallelism(conn, book_id)
        if emblematic:
            results["emblematic_parallelism"] = emblematic
    except Exception as e:
        results["emblematic_parallelism_error"] = str(e)

    results["summary"] = {
        "cognate_accusative": len(results.get("cognate_accusative", [])),
        "numerical_parallelism": len(results.get("numerical_parallelism", [])),
        "merismus": len(results.get("merismus", [])),
        "hendiadys_candidates": len(results.get("hendiadys_candidates", [])),
        "emblematic_parallelism": len(results.get("emblematic_parallelism", [])),
    }

    return results
