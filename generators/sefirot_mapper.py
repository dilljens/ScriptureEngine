"""Sefirotic Mapping Generator.

Maps verses/words to the 10 sefirot (Kabbalistic tree of life) using
keyword matching. Creates connections between verses that share a sefirah label.

The 10 Sefirot:
  Keter (Crown)      — will, crown, head, divine will
  Chokhmah (Wisdom)  — wisdom, beginning, father, point
  Binah (Understanding) — understanding, mother, return, palace
  Chesed (Mercy)     — mercy, lovingkindness, right, great
  Gevurah (Judgment) — judgment, power, fear, left, might
  Tiferet (Beauty)   — beauty, truth, compassion, glory
  Netzach (Victory)  — victory, eternity, prophecy, strength
  Hod (Splendor)     — splendor, glory, thanksgiving, majesty
  Yesod (Foundation) — foundation, covenant, righteous, tzaddik
  Malkhut (Kingdom)  — kingdom, shekinah, bride, sovereignty

Phase 1: Algorithmic keyword seeding (this module).
Phase 2: Agent refinement (reads verses, judges classifications).
"""

import json
import logging

logger = logging.getLogger(__name__)

SEFIROT = {
    "keter": {
        "name": "Keter",
        "hebrew_name": "כֶּתֶר",
        "meaning": "Crown",
        "keywords_he": ["כתר", "ראשׁ", "עליון", "רצון"],
        "keywords_en": ["crown", "head", "will", "most high", "supreme"],
        "description": "Divine will — the highest, unknowable sefirah",
        "color": "white",
    },
    "chokhmah": {
        "name": "Chokhmah",
        "hebrew_name": "חָכְמָה",
        "meaning": "Wisdom",
        "keywords_he": ["חכמה", "תחלה", "אב", "ראשית"],
        "keywords_en": ["wisdom", "beginning", "father", "first", "point"],
        "description": "Primordial wisdom — the first flash of insight",
        "color": "grey",
    },
    "binah": {
        "name": "Binah",
        "hebrew_name": "בִּינָה",
        "meaning": "Understanding",
        "keywords_he": ["בינה", "אם", "תבונה", "שוב", "היכל"],
        "keywords_en": ["understanding", "mother", "return", "palace", "insight"],
        "description": "Analytical understanding — the palace of wisdom",
        "color": "black",
    },
    "chesed": {
        "name": "Chesed",
        "hebrew_name": "חֶסֶד",
        "meaning": "Mercy",
        "keywords_he": ["חסד", "רחמים", "ימין", "גדל", "אהבה"],
        "keywords_en": ["mercy", "lovingkindness", "right hand", "great", "love"],
        "description": "Unbounded love and mercy — the right arm of God",
        "color": "blue",
    },
    "gevurah": {
        "name": "Gevurah",
        "hebrew_name": "גְּבוּרָה",
        "meaning": "Judgment",
        "keywords_he": ["גבורה", "דין", "יראה", "שמאל", "כח"],
        "keywords_en": ["judgment", "power", "fear", "left", "might", "strength"],
        "description": "Divine judgment and discipline — the left arm of God",
        "color": "red",
    },
    "tiferet": {
        "name": "Tiferet",
        "hebrew_name": "תִּפְאֶרֶת",
        "meaning": "Beauty",
        "keywords_he": ["תפארת", "אמת", "רחמים", "כבוד", "חמלה"],
        "keywords_en": ["beauty", "truth", "compassion", "glory", "harmony"],
        "description": "Harmonious balance between mercy and judgment — the heart",
        "color": "gold",
    },
    "netzach": {
        "name": "Netzach",
        "hebrew_name": "נֶצַח",
        "meaning": "Victory",
        "keywords_he": ["נצח", "נבואה", "עד", "תקיף"],
        "keywords_en": ["victory", "eternity", "prophecy", "endurance", "perpetual"],
        "description": "Eternal triumph and prophetic inspiration — the right leg",
        "color": "green",
    },
    "hod": {
        "name": "Hod",
        "hebrew_name": "הוֹד",
        "meaning": "Splendor",
        "keywords_he": ["הוד", "תודה", "הדר", "תהילה"],
        "keywords_en": ["splendor", "glory", "thanksgiving", "majesty", "praise"],
        "description": "Radiant splendor and gratitude — the left leg",
        "color": "orange",
    },
    "yesod": {
        "name": "Yesod",
        "hebrew_name": "יְסוֹד",
        "meaning": "Foundation",
        "keywords_he": ["יסוד", "ברית", "צדיק", "קדש"],
        "keywords_en": ["foundation", "covenant", "righteous", "holy", "tzaddik"],
        "description": "The foundation that channels divine energy — the covenant",
        "color": "purple",
    },
    "malkhut": {
        "name": "Malkhut",
        "hebrew_name": "מַלְכוּת",
        "meaning": "Kingdom",
        "keywords_he": ["מלכות", "שכינה", "כלה", "ממשלה"],
        "keywords_en": ["kingdom", "shekinah", "bride", "sovereignty", "queen"],
        "description": "The divine presence dwelling in the world — the bride",
        "color": "blue-violet",
    },
}


def run(conn, book_ids=None) -> int:
    """Tag verses with sefirah labels and create connections between them.

    1. Create the sefirah_keywords table
    2. For each verse, check if it matches any sefirah's keywords
    3. Create sefirah_verse_labels linking verses to sefirot
    4. Create connections between verses sharing a sefirah label
    5. Report counts

    Returns:
        int: Number of connections created
    """
    _ensure_schema(conn)

    # Step 1: Populate keyword table if empty
    _seed_keywords(conn)

    # Step 2: Match verses to sefirot via Hebrew keywords
    verse_labels = _match_verses(conn, book_ids)

    # Step 3: Create connections between verses sharing a sefirah
    connections = _create_sefirah_connections(conn, verse_labels, book_ids)

    logger.info(
        "Sefirot mapping complete",
        verses_tagged=len(verse_labels),
        connections=connections,
    )
    return connections


def _ensure_schema(conn):
    """Create the sefirah_keywords and sefirah_verse_labels tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sefirah_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sefirah TEXT NOT NULL,
            keyword TEXT NOT NULL,
            language TEXT DEFAULT 'hebrew',
            UNIQUE(sefirah, keyword)
        );
        CREATE TABLE IF NOT EXISTS sefirah_verse_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT NOT NULL,
            sefirah TEXT NOT NULL,
            matched_keyword TEXT,
            strength REAL DEFAULT 0.5,
            UNIQUE(verse_id, sefirah)
        );
        CREATE INDEX IF NOT EXISTS idx_svl_sefirah ON sefirah_verse_labels(sefirah);
        CREATE INDEX IF NOT EXISTS idx_svl_verse ON sefirah_verse_labels(verse_id);
    """)
    conn.commit()


def _seed_keywords(conn):
    """Insert sefirah keywords if the table is empty."""
    existing = conn.execute("SELECT COUNT(*) as c FROM sefirah_keywords").fetchone()
    if existing and existing["c"] > 0:
        return

    count = 0
    for sefirah, data in SEFIROT.items():
        for kw in data["keywords_he"]:
            conn.execute(
                "INSERT OR IGNORE INTO sefirah_keywords (sefirah, keyword, language) VALUES (?, ?, 'hebrew')",
                (sefirah, kw),
            )
            count += 1
        for kw in data["keywords_en"]:
            conn.execute(
                "INSERT OR IGNORE INTO sefirah_keywords (sefirah, keyword, language) VALUES (?, ?, 'english')",
                (sefirah, kw),
            )
            count += 1

    conn.commit()
    logger.info("Seeded sefirah keywords", count=count)


def _match_verses(conn, book_ids=None) -> dict:
    """Match verses to sefirot by Hebrew keyword occurrences.

    Uses the gematria table for Hebrew word-level matching against
    sefirah keywords. For English, uses the verses text.

    Returns:
        dict: {sefirah: set(verse_id, ...)}
    """
    # Clear existing labels for selective rebuild
    if book_ids:
        for book_id in book_ids:
            conn.execute(
                """DELETE FROM sefirah_verse_labels WHERE verse_id LIKE ?""",
                (f"{book_id}.%",),
            )
    else:
        conn.execute("DELETE FROM sefirah_verse_labels")
    conn.commit()

    # Get all keywords
    keywords = conn.execute(
        "SELECT sefirah, keyword, language FROM sefirah_keywords"
    ).fetchall()

    verse_labels = {}  # sefirah → set of verse_ids

    for kw in keywords:
        sefirah = kw["sefirah"]
        keyword = kw["keyword"]
        lang = kw["language"]

        if sefirah not in verse_labels:
            verse_labels[sefirah] = set()

        if lang == "hebrew":
            # Match Hebrew keywords via gematria table
            try:
                rows = conn.execute(
                    """
                    SELECT DISTINCT g.verse_id
                    FROM gematria g
                    WHERE g.word_hebrew LIKE ?
                    LIMIT 500
                """,
                    (f"%{keyword}%",),
                ).fetchall()
                for r in rows:
                    verse_labels[sefirah].add(r["verse_id"])
                    conn.execute(
                        "INSERT OR IGNORE INTO sefirah_verse_labels (verse_id, sefirah, matched_keyword, strength) VALUES (?, ?, ?, 0.5)",
                        (r["verse_id"], sefirah, keyword),
                    )
            except Exception:
                pass
        else:
            # Match English keywords via verses text
            try:
                rows = conn.execute(
                    """
                    SELECT DISTINCT v.id
                    FROM verses v
                    WHERE LOWER(v.text_english) LIKE LOWER(?)
                    LIMIT 500
                """,
                    (f"%{keyword}%",),
                ).fetchall()
                for r in rows:
                    verse_labels[sefirah].add(r["id"])
                    conn.execute(
                        "INSERT OR IGNORE INTO sefirah_verse_labels (verse_id, sefirah, matched_keyword, strength) VALUES (?, ?, ?, 0.4)",
                        (r["id"], sefirah, keyword),
                    )
            except Exception:
                pass

    conn.commit()
    return verse_labels


def _create_sefirah_connections(conn, verse_labels, book_ids=None) -> int:
    """Create connections between verses sharing a sefirah label.

    For each sefirah, connects up to MAX_VERSES most-connected verses
    to avoid O(n²) explosion for sefirot with thousands of tagged verses.
    """
    MAX_VERSE = 100  # max verses per sefirah to pairwise-connect
    count = 0

    for sefirah, verses in verse_labels.items():
        verse_list = list(verses)
        if len(verse_list) < 2:
            continue

        data = SEFIROT.get(sefirah, {})
        subtype = sefirah
        metadata = json.dumps({
            "sefirah": sefirah,
            "sefirah_name": data.get("name", sefirah),
            "sefirah_meaning": data.get("meaning", ""),
            "description": data.get("description", ""),
        })

        # Limit to top N most-connected verses per sefirah
        # using a temp table for safe parameter binding
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS _sef_verses (id TEXT PRIMARY KEY)")
        conn.execute("DELETE FROM _sef_verses")
        for vid in verse_list:
            conn.execute("INSERT OR IGNORE INTO _sef_verses (id) VALUES (?)", (vid,))

        ranked = conn.execute(
            """SELECT sv.id, COUNT(c.id) as degree
               FROM _sef_verses sv
               LEFT JOIN connections c ON (c.source_verse = sv.id OR c.target_verse = sv.id)
                 AND c.deprecated = 0
               GROUP BY sv.id ORDER BY degree DESC LIMIT ?""",
            (MAX_VERSE,),
        ).fetchall()
        conn.execute("DELETE FROM _sef_verses")
        top_verses = [r["id"] for r in ranked]

        # Connect top-ranked verses pairwise
        for i in range(len(top_verses)):
            for j in range(i + 1, len(top_verses)):
                src, tgt = top_verses[i], top_verses[j]
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO connections
                           (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                           VALUES (?, ?, 'symbolic', 'sefirah_mapping', ?, 0.6, 0.5, 'algorithm', ?)""",
                        (src, tgt, subtype, metadata),
                    )
                    count += 1
                    if count % 5000 == 0:
                        conn.commit()
                except Exception:
                    continue

    conn.commit()
    return count
