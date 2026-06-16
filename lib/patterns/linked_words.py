"""Linked words / catchword detection for Hebrew parallelism.

Detects when semantically related word pairs appear in corresponding
positions across parallel clauses — like Isaiah 1:3:

  "The ox knows its owner,
   the ass its master's stall"

  ox ↔ ass (paired animals)
  owner ↔ master's stall (paired concepts of possession/authority)
  knows is implied for the second line (ellipsis)

This is a specific form of synonymous parallelism where:
  1. Elements in corresponding positions form semantic pairs
  2. The pairing reveals the text's structure and meaning
  3. The same Hebrew root often appears at structural seams (catchwords)
"""

import re
from collections import defaultdict
from ..gematria import extract_consonants


# Known semantic pair categories for linked-word detection
SEMANTIC_PAIRS = {
    "animals": {
        "ox": ["ox", "oxen", "bullock", "bull", "cow", "calf"],
        "ass": ["ass", "donkey", "she-ass"],
        "sheep": ["sheep", "ewe", "ram", "lamb"],
        "goat": ["goat", "kid"],
        "lion": ["lion", "lioness"],
        "horse": ["horse", "steed"],
    },
    "people": {
        "man": ["man", "husband", "male"],
        "woman": ["woman", "wife", "female"],
        "father": ["father", "sire"],
        "mother": ["mother"],
        "son": ["son", "child", "boy"],
        "daughter": ["daughter", "girl", "maid"],
        "king": ["king", "ruler", "sovereign", "monarch"],
        "priest": ["priest", "cohen", "minister"],
        "prophet": ["prophet", "seer"],
        "servant": ["servant", "slave", "attendant"],
        "master": ["master", "lord", "owner"],
    },
    "places": {
        "city": ["city", "town", "village"],
        "house": ["house", "home", "dwelling", "habitation"],
        "temple": ["temple", "sanctuary", "tabernacle"],
        "land": ["land", "earth", "ground", "soil"],
        "desert": ["desert", "wilderness", "waste"],
        "mountain": ["mountain", "hill", "peak"],
        "field": ["field", "pasture"],
    },
    "actions": {
        "hear": ["hear", "listen", "hearken"],
        "see": ["see", "behold", "look", "perceive"],
        "know": ["know", "understand", "discern"],
        "speak": ["speak", "say", "tell", "declare"],
        "walk": ["walk", "go", "come"],
        "stand": ["stand", "arise", "rise"],
    },
    "concepts": {
        "righteousness": ["righteousness", "justice", "judgment"],
        "mercy": ["mercy", "lovingkindness", "grace"],
        "truth": ["truth", "faithfulness"],
        "peace": ["peace", "rest", "quietness"],
        "joy": ["joy", "gladness", "rejoicing"],
        "sorrow": ["sorrow", "mourning", "grief"],
        "light": ["light", "day"],
        "darkness": ["darkness", "night", "shadow"],
        "life": ["life", "live", "living"],
        "death": ["death", "die", "dead"],
        "blessing": ["blessing", "bless", "blessed"],
        "curse": ["curse", "cursed"],
        "sin": ["sin", "iniquity", "transgression", "wickedness"],
        "covenant": ["covenant", "testament"],
    },
    "divine": {
        "yhwh": ["lord", "yhwh", "jehovah"],
        "elohim": ["god", "elohim", "almighty"],
        "spirit": ["spirit", "breath", "wind"],
        "angel": ["angel", "messenger"],
    },
}

# Build reverse lookup: word → category pair
CATEGORY_LOOKUP = {}
for cat, pairs in SEMANTIC_PAIRS.items():
    for pair_name, words in pairs.items():
        for word in words:
            CATEGORY_LOOKUP[word.lower()] = (cat, pair_name)


def get_semantic_tag(word):
    """Get (category, pair_name) for a word if it's in our semantic dictionary."""
    w = word.lower().strip(".,;:!?-'\"")
    return CATEGORY_LOOKUP.get(w)


def find_linked_word_pairs(text_a, text_b):
    """Find linked word pairs in two parallel texts.
    
    For each word in text_a, check if the corresponding position
    in text_b has a word from the same semantic pair category.
    
    Returns list of (word_a, word_b, category, pair_type) tuples.
    """
    words_a = re.findall(r"[a-zA-Z']+", text_a.lower())
    words_b = re.findall(r"[a-zA-Z']+", text_b.lower())
    
    linked_pairs = []
    matched_a = set()
    matched_b = set()
    
    # Check each word in text_a against words in text_b
    for i, wa in enumerate(words_a):
        tag_a = get_semantic_tag(wa)
        if not tag_a or i in matched_a:
            continue
        
        for j, wb in enumerate(words_b):
            if j in matched_b:
                continue
            
            tag_b = get_semantic_tag(wb)
            if not tag_b:
                continue
            
            # Same category, same pair = linked
            if tag_a[0] == tag_b[0] and tag_a[1] == tag_b[1]:
                linked_pairs.append({
                    "word_a": words_a[i],
                    "word_b": words_b[j],
                    "category": tag_a[0],
                    "pair_type": tag_a[1],
                    "position_a": i,
                    "position_b": j,
                })
                matched_a.add(i)
                matched_b.add(j)
                break
    
    return linked_pairs


def find_linked_words_in_passage(verses):
    """Find linked word pairs across adjacent parallel verses.
    
    Looks for the Isaiah 1:3 pattern where semantically paired words
    appear in corresponding positions.
    """
    texts = [v.get("text_english", "") for v in verses if v.get("text_english")]
    results = []
    
    for i in range(len(texts) - 1):
        pairs = find_linked_word_pairs(texts[i], texts[i + 1])
        if pairs:
            results.append({
                "verse_a_index": i,
                "verse_b_index": i + 1,
                "linked_pairs": pairs,
                "count": len(pairs),
            })
    
    return results


# Giliadi-style keyword detection
# Isaiah uses specific keywords as catchwords that link passages

GILIADI_KEYWORDS = [
    # Divine names/titles
    ("יהוה צבאות", "YHWH of Hosts"),
    ("קדוש ישראל", "Holy One of Israel"),
    ("אביר ישראל", "Mighty One of Israel"),
    ("מלך ישראל", "King of Israel"),
    ("גאל", "Redeemer"),
    
    # Thematic keywords
    ("שאר", "remnant"),
    ("ציון", "Zion"),
    ("ירושלם", "Jerusalem"),
    ("משפט", "judgment/justice"),
    ("צדקה", "righteousness"),
    ("ישע", "salvation"),
    ("גוי", "nation/nations"),
    ("עבד", "servant"),
    ("ברית", "covenant"),
    ("חסד", "lovingkindness/mercy"),
    ("אמת", "truth/faithfulness"),
    
    # Structural markers
    ("כי", "for/because (structural pivot marker)"),
    ("לכן", "therefore (conclusion marker)"),
    ("הנה", "behold (attention marker)"),
    ("הוי", "woe (judgment oracle marker)"),
]


def find_giliadi_catchwords(conn, book_id="isa"):
    """Find Giliadi-style keywords in Isaiah.
    
    Tracks where each keyword appears and connects verses
    that share the same thematic keyword.
    """
    from ..db import get_db, add_connection
    
    count = 0
    for heb, meaning in GILIADI_KEYWORDS:
        # Build a consonant-only search pattern
        cons_only = extract_consonants(heb)
        if not cons_only:
            continue
        
        # Search through gematria table
        like_pattern = f"%{'%'.join(cons_only)}%" if len(cons_only) > 1 else f"%{cons_only}%"
        
        rows = conn.execute("""
            SELECT DISTINCT g.verse_id FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            WHERE v.book_id = ? AND g.word_hebrew LIKE ?
            LIMIT 30
        """, (book_id, like_pattern)).fetchall()
        
        verses = [r["verse_id"] for r in rows]
        
        # Connect using hub-and-spoke to avoid N² explosion
        if len(verses) >= 2:
            hub = verses[0]
            for v in verses[1:]:
                try:
                    add_connection(conn, hub, v,
                                  layer="structural",
                                  type_name="keyword_linking",
                                  subtype="giliadi_catchword",
                                  strength=0.6,
                                  confidence=0.55,
                                  discovered_by="algorithm",
                                  metadata={
                                      "keyword": meaning.split(" — ")[0] if "—" in meaning else meaning,
                                      "hebrew": heb,
                                      "notes": f"Giliadi catchword: {meaning}",
                                  })
                    count += 1
                    if count % 100 == 0:
                        conn.commit()
                except Exception:
                    pass
    
    return count


def generate_linked_word_connections(conn, book_ids=None):
    """Generate linked-word connections for all books.
    
    Detects semantically paired words in parallel verses and
    creates keyword_linking connections.
    """
    from ..db import get_db, add_connection
    
    if book_ids is None:
        book_ids = [r["book_id"] for r in conn.execute(
            "SELECT DISTINCT book_id FROM verses WHERE text_english != ''"
        ).fetchall()]
    
    count = 0
    for bid in book_ids[:5]:  # Limit to 5 books to avoid explosion
        rows = conn.execute("""
            SELECT id, chapter, verse, text_english FROM verses
            WHERE book_id = ? AND text_english != ''
            ORDER BY chapter, verse
        """, (bid,)).fetchall()
        
        verses = [dict(r) for r in rows]
        link_results = find_linked_words_in_passage(verses)
        
        for lr in link_results:
            idx_a = lr["verse_a_index"]
            idx_b = lr["verse_b_index"]
            if idx_a >= len(verses) or idx_b >= len(verses):
                continue
            
            for pair in lr["linked_pairs"]:
                try:
                    add_connection(conn, verses[idx_a]["id"], verses[idx_b]["id"],
                                  layer="structural",
                                  type_name="keyword_linking",
                                  subtype="linked_words",
                                  strength=0.55,
                                  confidence=0.5,
                                  discovered_by="algorithm",
                                  metadata={
                                      "word_a": pair["word_a"],
                                      "word_b": pair["word_b"],
                                      "category": pair["category"],
                                      "pair_type": pair["pair_type"],
                                  })
                    count += 1
                except Exception:
                    pass
    
    conn.commit()
    return count
