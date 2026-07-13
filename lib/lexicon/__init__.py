"""
Scripture Lexicon — a word-level dictionary built from the gematria table.

Three layers:
1. **Dictionary** — one entry per unique lemma (21K+ Strong's numbers)
2. **Word families** — roots, semantic domains, collocations
3. **Concordance** — every occurrence of a lemma across the canon

All data is derived algorithmically from the gematria table — no LLM needed
for the initial build. LLM-defined definitions are added in a later phase.
"""

import json
import re
from collections import defaultdict

# ─── Lexicon Tables ───

LEXICON_SCHEMA = """
CREATE TABLE IF NOT EXISTS lexicon (
    lemma TEXT PRIMARY KEY,                       -- base Strong's number (e.g., "H430")
    hebrew TEXT DEFAULT '',                       -- most common Hebrew spelling
    transliteration TEXT DEFAULT '',               -- phonetic transliteration
    part_of_speech TEXT DEFAULT '',                -- noun, verb, etc. (from morph)
    root_letters TEXT DEFAULT '',                  -- triconsonantal root (e.g., "אלה")
    semantic_domain TEXT DEFAULT '',               -- FK to semantic_domains
    definition TEXT DEFAULT '',                    -- LLM-written in later phase
    definition_source TEXT DEFAULT 'algorithm',    -- 'algorithm', 'ai', 'human'
    frequency INTEGER DEFAULT 0,                   -- total occurrences across canon
    frequency_per_book TEXT DEFAULT '{}',          -- JSON: {"gen": 5, "exo": 20}
    books_list TEXT DEFAULT '',                    -- comma-separated book IDs
    morphology TEXT DEFAULT '',                    -- dominant morph pattern
    ai_generated INTEGER DEFAULT 0,
    reviewed INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS semantic_domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    ai_generated INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS domain_members (
    domain_id INTEGER NOT NULL REFERENCES semantic_domains(id),
    lemma TEXT NOT NULL REFERENCES lexicon(lemma),
    PRIMARY KEY (domain_id, lemma)
);

CREATE TABLE IF NOT EXISTS word_collocations (
    word_a TEXT NOT NULL,                          -- lemma
    word_b TEXT NOT NULL,                          -- lemma
    book_id TEXT NOT NULL DEFAULT '',
    frequency INTEGER DEFAULT 0,
    strength REAL DEFAULT 0.0,                     -- PMI or co-occurrence score
    PRIMARY KEY (word_a, word_b, book_id)
);

CREATE INDEX IF NOT EXISTS idx_collocations_a ON word_collocations(word_a);
CREATE INDEX IF NOT EXISTS idx_collocations_b ON word_collocations(word_b);
"""


def init_lexicon_tables(conn):
    """Create lexicon tables if they don't exist."""
    conn.executescript(LEXICON_SCHEMA)
    conn.commit()


def normalize_lemma(raw_lemma):
    """Strip prefixes to get base Strong's number.

    Handles:
      'c/853' → '853', 'd/776' → '776' (letter + slash)
      'H430' → '430', 'G2316' → '2316' (Strong's letter prefix)
      '5921 a' → '5921' (trailing letters)
    Returns the bare numeric portion.
    """
    if not raw_lemma:
        return ""
    raw = raw_lemma.strip()
    # Strip Strong's letter prefix (H for Hebrew, G for Greek, etc.)
    raw = re.sub(r'^[A-Z]+', '', raw)
    # Strip prefix: "c/853" -> "853", "b/7225 a" -> "7225 a"
    m = re.match(r'^[a-z]+/(.+)$', raw)
    if m:
        raw = m.group(1).strip()
    # Strip trailing letters like "5921 a"
    raw = re.sub(r'\s+[a-z]+$', '', raw)
    return raw.strip()


def extract_root(hebrew_word):
    """Extract likely triconsonantal root from a Hebrew word.

    Heuristic: takes the last 3-4 consonants (most Hebrew roots are 3-4
    letters at the end of the word). Does NOT strip prefixes, as that
    requires proper morphological analysis.
    """
    if not hebrew_word:
        return ""
    heb_letters = []
    for c in hebrew_word:
        cp = ord(c)
        if (0x05D0 <= cp <= 0x05EA) or (0x05EF <= cp <= 0x05F2):
            heb_letters.append(c)
    if not heb_letters:
        return ""
    # Take last 3-4 consonants as the root
    root = ''.join(heb_letters[-4:])
    return root


def build_lexicon(conn):
    """Build the lexicon table from the gematria table.

    Algorithmic only — extracts lemmas, Hebrew, frequencies, morphology.
    Definitions are added later by LLM.

    Returns stats dict.
    """
    stats = {"lemmas": 0, "collocations": 0}

    # Ensure tables exist
    init_lexicon_tables(conn)

    # Clear existing data for rebuild
    conn.execute("DELETE FROM lexicon")
    conn.execute("DELETE FROM word_collocations")
    conn.commit()

    # ── Step 1: Extract unique lemmas with Hebrew, English, morphology ──

    rows = conn.execute("""
        SELECT
            lemma,
            word_hebrew,
            word_english,
            morph,
            value_standard,
            COUNT(DISTINCT verse_id) as occurrence_count,
            COUNT(DISTINCT v.book_id) as book_count
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        WHERE lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
        ORDER BY occurrence_count DESC
    """).fetchall()

    batch = []
    for r in rows:
        raw_lemma = r["lemma"]
        base_lemma = normalize_lemma(raw_lemma)
        hebrew = (r["word_hebrew"] or "").strip()
        (r["word_english"] or "").strip()
        morph = (r["morph"] or "").strip()
        freq = r["occurrence_count"]
        r["book_count"]

        # Extract root from Hebrew
        root = extract_root(hebrew)

        batch.append((
            base_lemma, hebrew, "",    # lemma, hebrew, transliteration
            "",                        # part_of_speech
            root,                      # root_letters
            "",                        # semantic_domain
            "",                        # definition
            "algorithm",               # definition_source
            freq,                      # frequency
            "{}",                      # frequency_per_book
            "",                        # books_list
            morph,                     # morphology
            0,                         # ai_generated
            0,                         # reviewed
            "{}",                      # metadata
        ))

        if len(batch) >= 500:
            _insert_lexicon_batch(conn, batch)
            batch = []

    if batch:
        _insert_lexicon_batch(conn, batch)

    stats["lemmas"] = len(batch)  # approximate, actual count from SQL

    # ── Step 2: Count actual inserted lemmas ──
    stats["lemmas"] = conn.execute("SELECT COUNT(*) as c FROM lexicon").fetchone()["c"]

    # ── Step 3: Compute per-book frequency ──
    _update_book_frequencies(conn)

    # ── Step 4: Build collocations (co-occurring lemmas within verses) ──
    stats["collocations"] = _build_collocations(conn)

    conn.commit()
    return stats


def _insert_lexicon_batch(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO lexicon
            (lemma, hebrew, transliteration, part_of_speech, root_letters,
             semantic_domain, definition, definition_source,
             frequency, frequency_per_book, books_list, morphology,
             ai_generated, reviewed, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)


def _update_book_frequencies(conn):
    """Update per-book frequency for each lemma."""
    rows = conn.execute("""
        SELECT l.lemma, v.book_id, COUNT(*) as c
        FROM lexicon l
        JOIN gematria g ON g.lemma LIKE '%' || l.lemma || '%'
        JOIN verses v ON v.id = g.verse_id
        GROUP BY l.lemma, v.book_id
    """).fetchall()

    by_lemma = defaultdict(dict)
    books_by_lemma = defaultdict(set)
    for r in rows:
        by_lemma[r["lemma"]][r["book_id"]] = r["c"]
        books_by_lemma[r["lemma"]].add(r["book_id"])

    for lemma, book_counts in by_lemma.items():
        freq_json = json.dumps(book_counts)
        books_str = ",".join(sorted(books_by_lemma[lemma]))
        conn.execute(
            "UPDATE lexicon SET frequency_per_book = ?, books_list = ? WHERE lemma = ?",
            (freq_json, books_str, lemma)
        )


def _build_collocations(conn, min_cooccurrence=3):
    """Build word collocations — lemmas that co-occur in the same verse.

    Only includes co-occurrences that appear at least min_cooccurrence times
    to avoid noise.
    """
    count = 0

    # Find co-occurring lemma pairs within verses
    rows = conn.execute("""
        SELECT g1.lemma as lemma_a, g2.lemma as lemma_b,
               v.book_id, COUNT(*) as co_count
        FROM gematria g1
        JOIN gematria g2 ON g2.verse_id = g1.verse_id AND g2.lemma < g1.lemma
        JOIN verses v ON v.id = g1.verse_id
        WHERE g1.lemma IS NOT NULL AND g1.lemma != ''
          AND g2.lemma IS NOT NULL AND g2.lemma != ''
        GROUP BY g1.lemma, g2.lemma, v.book_id
        HAVING co_count >= ?
        ORDER BY co_count DESC
    """, (min_cooccurrence,)).fetchall()

    batch = []
    for r in rows:
        a = normalize_lemma(r["lemma_a"])
        b = normalize_lemma(r["lemma_b"])
        if a and b and a != b:
            # Store both directions for easier lookup
            batch.append((a, b, r["book_id"], r["co_count"], 1.0))
            count += 1
            if len(batch) >= 500:
                _insert_collocation_batch(conn, batch)
                batch = []

    if batch:
        _insert_collocation_batch(conn, batch)

    return count


def _insert_collocation_batch(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO word_collocations (word_a, word_b, book_id, frequency, strength)
        VALUES (?, ?, ?, ?, ?)
    """, batch)


def get_lexicon_entry(conn, lemma):
    """Get a full lexicon entry by lemma."""
    row = conn.execute("""
        SELECT * FROM lexicon WHERE lemma = ?
    """, (lemma,)).fetchone()
    if not row:
        return None

    entry = dict(row)
    try:
        entry["frequency_per_book"] = json.loads(entry.get("frequency_per_book", "{}"))
    except (json.JSONDecodeError, TypeError):
        entry["frequency_per_book"] = {}

    # Get collocations
    collocations = conn.execute("""
        SELECT word_a, word_b, book_id, frequency FROM word_collocations
        WHERE word_a = ? OR word_b = ?
        ORDER BY frequency DESC
        LIMIT 20
    """, (lemma, lemma)).fetchall()
    entry["collocations"] = [dict(r) for r in collocations]

    return entry


def search_lexicon(conn, query, limit=20):
    """Search lexicon by lemma (Strong's number), Hebrew text, or English word.

    Searches across:
    - Lemma number: '3068' → YHWH
    - Hebrew text: 'יהוה' → matches both niqqud and plain
    - English word: 'covenant' → finds H1285 (berith)
    """
    query = query.strip()
    if not query:
        return []

    # Try English search via lemma_gloss table first
    eng_rows = conn.execute("""
        SELECT l.lemma, l.hebrew, l.transliteration, l.part_of_speech,
               l.root_letters, l.frequency, l.semantic_domain,
               lg.english_gloss
        FROM lexicon l
        JOIN lemma_gloss lg ON lg.lemma = l.lemma
        WHERE LOWER(lg.english_gloss) LIKE ?
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()
    if eng_rows:
        return [dict(r) for r in eng_rows]

    # Search by lemma or Hebrew (including niqqud-stripped)
    rows = conn.execute("""
        SELECT l.lemma, l.hebrew, l.transliteration, l.part_of_speech,
               l.root_letters, l.frequency, l.semantic_domain,
               lg.english_gloss
        FROM lexicon l
        LEFT JOIN lemma_gloss lg ON lg.lemma = l.lemma
        WHERE l.lemma = ? OR l.hebrew LIKE ? OR l.hebrew_plain LIKE ? OR l.lemma LIKE ?
        LIMIT ?
    """, (query, f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()

    return [dict(r) for r in rows]


def get_domain_members(conn, domain_name):
    """Get all lemmas in a semantic domain."""
    rows = conn.execute("""
        SELECT l.lemma, l.hebrew, l.frequency
        FROM domain_members dm
        JOIN lexicon l ON l.lemma = dm.lemma
        JOIN semantic_domains sd ON sd.id = dm.domain_id
        WHERE sd.name = ?
        ORDER BY l.frequency DESC
    """, (domain_name,)).fetchall()
    return [dict(r) for r in rows]


def get_root_family(conn, root_letters):
    """Get all lemmas sharing a triconsonantal root."""
    rows = conn.execute("""
        SELECT lemma, hebrew, part_of_speech, frequency
        FROM lexicon
        WHERE root_letters = ?
        ORDER BY frequency DESC
    """, (root_letters,)).fetchall()
    return [dict(r) for r in rows]


def get_concordance(conn, lemma, limit=100):
    """Get all verses containing a lemma."""
    base = normalize_lemma(lemma)
    rows = conn.execute("""
        SELECT v.id as verse_id, v.text_english, v.chapter, v.verse,
               b.title as book_title, b.id as book_id,
               g.word_hebrew, g.word_index
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.lemma LIKE ?
        ORDER BY b.position, v.chapter, v.verse
        LIMIT ?
    """, (f"%{base}%", limit)).fetchall()
    return [dict(r) for r in rows]
