"""Intertextual generator — quotation and allusion connections.

Detects intertextual relationships by finding shared rare-word clusters.
For speed, focuses on the most intertextually active book pairs:
  OT↔NT (especially Isaiah→NT, Psalms→NT)
  OT↔BoM (especially Isaiah→BoM)
  NT↔BoM
  BoM↔D&C
"""

import re
from collections import defaultdict, Counter
from lib.db import add_connection


STOPWORDS = {
    "the", "and", "that", "for", "of", "to", "in", "he", "she", "it",
    "they", "them", "their", "his", "her", "its", "a", "an", "is", "was",
    "were", "are", "be", "been", "has", "have", "had", "do", "did", "does",
    "shall", "will", "would", "could", "should", "may", "might", "can",
    "not", "no", "nor", "but", "or", "as", "at", "by", "from", "into",
    "with", "upon", "unto", "thou", "thy", "thee", "thine",
    "ye", "your", "you", "our", "us", "we", "my", "me", "i", "all",
    "every", "each", "some", "any", "one", "two", "very", "also", "now",
    "then", "than", "thus", "so", "yet", "for", "therefore", "wherefore",
    "behold", "hath", "doth", "dost", "didst", "art", "wast",
    "shalt", "wilt", "canst", "couldst", "wouldst", "shouldst",
    "cometh", "goeth", "saith", "answered", "spake",
    "jesus", "christ", "lord", "god", "spirit", "man", "men",
}


# High-value intertextual book pairs to focus on
TARGET_PAIRS = [
    # NT quotes OT
    ("isa", "matt"), ("isa", "mark"), ("isa", "luke"), ("isa", "john"),
    ("isa", "acts"), ("isa", "rom"), ("isa", "1pet"), ("isa", "heb"),
    ("psa", "matt"), ("psa", "mark"), ("psa", "luke"), ("psa", "john"),
    ("psa", "acts"), ("psa", "rom"), ("psa", "heb"),
    ("gen", "rom"), ("gen", "gal"), ("gen", "heb"),
    ("deu", "matt"), ("deu", "luke"), ("deu", "john"), ("deu", "acts"),
    ("exo", "rom"), ("exo", "1cor"), ("exo", "heb"),
    ("jer", "matt"), ("jer", "luke"), ("jer", "john"), ("jer", "heb"),
    ("dan", "matt"), ("dan", "luke"), ("dan", "rev"),
    ("hos", "matt"), ("hos", "rom"), ("hos", "1pet"),
    ("amos", "acts"), ("hab", "rom"), ("hab", "gal"),
    ("zech", "matt"), ("zech", "john"), ("zech", "rev"),
    ("mal", "matt"), ("mal", "luke"), ("mal", "3ne"),
    # BoM quotes OT
    ("isa", "1ne"), ("isa", "2ne"), ("isa", "mosiah"),
    ("gen", "1ne"), ("gen", "2ne"), ("gen", "alma"),
    ("psa", "2ne"), ("deu", "1ne"),
    # BoM quotes NT (or vice versa)
    ("matt", "3ne"), ("luke", "3ne"), ("john", "3ne"),
    # APOCRYPHA — NT cross-references
    ("wis", "matt"), ("wis", "luke"), ("wis", "john"),
    ("wis", "rom"), ("wis", "1cor"), ("wis", "heb"),
    ("sir", "matt"), ("sir", "luke"), ("sir", "john"),
    ("sir", "rom"), ("sir", "james"),
    ("2esd", "matt"), ("2esd", "rev"),
    ("tob", "luke"), ("tob", "john"),
    ("bar", "rom"), ("bar", "heb"),
    ("1ma", "heb"), ("2ma", "heb"),
    # APOCRYPHA — OT cross-references
    ("wis", "isa"), ("wis", "psa"), ("wis", "gen"),
    ("sir", "psa"), ("sir", "prov"), ("sir", "gen"),
    ("tob", "gen"),
    ("bar", "jer"), ("bar", "psa"),
    # APOCRYPHA — BoM cross-references
    ("wis", "2ne"), ("sir", "2ne"),
    # PSEUDEPIGRAPHA — NT cross-references
    ("1en", "matt"), ("1en", "luke"), ("1en", "john"),
    ("1en", "acts"), ("1en", "rom"), ("1en", "2pet"), ("1en", "jude"),
    ("1en", "rev"),
    ("jub", "matt"), ("jub", "luke"), ("jub", "john"), ("jub", "rev"),
    ("ascis", "matt"), ("ascis", "luke"), ("ascis", "john"),
    ("odessol", "john"), ("odessol", "rev"),
    ("psssol", "matt"), ("psssol", "luke"),
    ("barn", "matt"), ("barn", "heb"), ("barn", "rom"),
    ("apabr", "luke"), ("apabr", "rev"),
    ("tabr", "luke"), ("tabr", "heb"),
    # PSEUDEPIGRAPHA — OT cross-references
    ("1en", "gen"), ("1en", "isa"), ("1en", "dan"), ("1en", "psa"),
    ("jub", "gen"), ("jub", "exo"), ("jub", "psa"),
    ("ascis", "isa"),
    ("odessol", "psa"), ("odessol", "isa"),
    ("psssol", "psa"),
    ("asis", "isa"),
    ("barn", "psa"), ("barn", "isa"),
    ("tjob", "job"),
    # PSEUDEPIGRAPHA — BoM cross-references
    ("1en", "1ne"), ("1en", "2ne"),
    ("jub", "1ne"), ("jub", "2ne"),
    # PSEUDEPIGRAPHA — DSS cross-references  
    ("1en", "1QHa"), ("1en", "1QS"),
    ("jub", "CD"), ("jub", "11Q19"),
    # DSS — NT cross-references (now with Vermès English!)
    ("1QS", "matt"), ("1QS", "luke"), ("1QS", "john"),
    ("1QS", "acts"), ("1QS", "rom"), ("1QS", "heb"),
    ("1QS", "eph"), ("1QS", "1cor"), ("1QS", "2cor"),
    ("CD", "matt"), ("CD", "luke"), ("CD", "rom"),
    ("CD", "gal"), ("CD", "heb"),
    ("1QHa", "matt"), ("1QHa", "luke"), ("1QHa", "john"),
    ("1QHa", "psa"), ("1QHa", "rom"),
    ("1QM", "matt"), ("1QM", "luke"), ("1QM", "rev"),
    ("1QM", "eph"), ("1QM", "rev"),
    # DSS — OT cross-references
    ("1QS", "isa"), ("1QS", "psa"), ("1QS", "jer"),
    ("CD", "isa"), ("CD", "psa"), ("CD", "deu"),
    ("1QHa", "psa"), ("1QHa", "isa"),
    # DSS — BoM cross-references
    ("1QS", "2ne"), ("1QS", "mosiah"),
    ("CD", "alma"),
]


def tokenize(text):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 3]


def _batch_insert(conn, batch):
    """Batch insert connections."""
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def compare_books(conn, book_a, book_b, rare_words, word_verse_index):
    """Compare all verses in book_a with all verses in book_b.
    
    Uses the pre-built rare word index to find shared rare-word clusters.
    """
    verses_a = conn.execute("""
        SELECT id, text_english FROM verses WHERE book_id = ? AND text_english != ''
    """, (book_a,)).fetchall()
    verses_b = conn.execute("""
        SELECT id, text_english FROM verses WHERE book_id = ? AND text_english != ''
    """, (book_b,)).fetchall()

    if not verses_a or not verses_b:
        return []

    batch = []
    count = 0

    for va in verses_a:
        tokens = tokenize(va["text_english"])
        rare_in_va = [t for t in tokens if t in rare_words]
        if len(rare_in_va) < 2:
            continue

        # Find candidate verses in book_b that share rare words
        candidates = Counter()
        for word in rare_in_va:
            if word in word_verse_index:
                for other_vid in word_verse_index[word]:
                    if other_vid == va["id"]:
                        continue
                    # Only count verses from book_b
                    vid_book = other_vid.split(".")[0]
                    if vid_book == book_b:
                        candidates[other_vid] += 1

        # Classify and create connections
        for other_vid, overlap in candidates.most_common(5):
            if overlap >= 8:
                conn_type = "direct_quotation"
                strength = 0.9
                conf = 0.85
            elif overlap >= 4:
                conn_type = "allusion"
                strength = 0.6
                conf = 0.6
            elif overlap >= 2:
                conn_type = "echo"
                strength = 0.35
                conf = 0.35
            else:
                continue

            batch.append((
                va["id"], other_vid, "intertextual",
                conn_type, f"{book_a}_{book_b}", strength, conf, "algorithm",
                f'{{"shared_words": {overlap}, "books": ["{book_a}", "{book_b}"]}}'
            ))
            count += 1

            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []

    if batch:
        _batch_insert(conn, batch)

    return count


def run(conn, book_ids=None):
    """Generate intertextual connections between target book pairs."""
    count = 0
    total_pairs = len(TARGET_PAIRS)

    # Step 1: Build rare word index from the entire corpus
    print("  Building rare word index...", flush=True)

    all_verses = conn.execute("""
        SELECT id, text_english FROM verses WHERE text_english != ''
    """).fetchall()

    # Count word frequencies
    word_freq = Counter()
    verse_tokens = {}
    for r in all_verses:
        tokens = tokenize(r["text_english"])
        verse_tokens[r["id"]] = set(tokens)
        for t in tokens:
            word_freq[t] += 1

    # Identify rare words (< 200 occurrences)
    rare_words = {word for word, freq in word_freq.items() if 2 <= freq < 200}

    # Build rare-word → verses index
    word_verse_index = defaultdict(set)
    for vid, tokens in verse_tokens.items():
        for t in tokens:
            if t in rare_words:
                word_verse_index[t].add(vid)

    print(f"  {len(rare_words)} rare words indexed", flush=True)

    # Step 2: Compare target book pairs
    for i, (book_a, book_b) in enumerate(TARGET_PAIRS):
        result = compare_books(conn, book_a, book_b, rare_words, word_verse_index)
        count += result
        if result > 0:
            print(f"    {book_a}↔{book_b}: {result} connections", flush=True)

    print(f"  Intertextual: {count} total connections across {total_pairs} book pairs")
    return count
