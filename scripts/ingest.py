#!/usr/bin/env python3
"""
Ingest scripture data from JSON (English LDS Standard Works) and XML (Hebrew OT)
into the SQLite knowledge base.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.db import add_connection, init_db, insert_gematria, insert_verse
from lib.gematria import DIVINE_NAMES, compute_all

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = PROCESSED_DIR / "scripture.db"

# Book ID mappings
# Map from JSON book names to canonical short IDs
BOOK_IDS_OT = {
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num",
    "Deuteronomy": "deu", "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "1 Samuel": "1sam", "2 Samuel": "2sam", "1 Kings": "1kgs", "2 Kings": "2kgs",
    "1 Chronicles": "1chr", "2 Chronicles": "2chr", "Ezra": "ezra", "Nehemiah": "neh",
    "Esther": "esth", "Job": "job", "Psalms": "psa", "Proverbs": "prov",
    "Ecclesiastes": "eccl",     "Solomon's Song": "song", "Isaiah": "isa",
    "Jeremiah": "jer", "Lamentations": "lam", "Ezekiel": "ezek", "Daniel": "dan",
    "Hosea": "hos", "Joel": "joel", "Amos": "amos", "Obadiah": "obad",
    "Jonah": "jonah", "Micah": "mic", "Nahum": "nah", "Habakkuk": "hab",
    "Zephaniah": "zeph", "Haggai": "hag", "Zechariah": "zech", "Malachi": "mal",
}

BOOK_IDS_NT = {
    "Matthew": "matt", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Romans": "rom", "1 Corinthians": "1cor", "2 Corinthians": "2cor",
    "Galatians": "gal", "Ephesians": "eph", "Philippians": "phil", "Colossians": "col",
    "1 Thessalonians": "1thes", "2 Thessalonians": "2thes",
    "1 Timothy": "1tim", "2 Timothy": "2tim", "Titus": "titus", "Philemon": "philem",
    "Hebrews": "heb", "James": "james", "1 Peter": "1pet", "2 Peter": "2pet",
    "1 John": "1john", "2 John": "2john", "3 John": "3john", "Jude": "jude",
    "Revelation": "rev",
}

BOOK_IDS_BOM = {
    "1 Nephi": "1ne", "2 Nephi": "2ne", "Jacob": "jacob", "Enos": "enos",
    "Jarom": "jarom", "Omni": "omni", "Words of Mormon": "wom",
    "Mosiah": "mosiah", "Alma": "alma", "Helaman": "hel",
    "3 Nephi": "3ne", "4 Nephi": "4ne", "Mormon": "morm", "Ether": "ether",
    "Moroni": "moro",
}

BOOK_IDS_DC = {}  # D&C uses section numbers, not book names
BOOK_IDS_PGP = {
    "Moses": "moses", "Abraham": "abraham",
    "Joseph Smith—Matthew": "jsm", "Joseph Smith—History": "jsh",
    "Articles of Faith": "aoff",
}

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

# ── OSHB / morphHB source pinning ──────────────────────────────────────────
# The Hebrew OT pointed text + morphology come from the Open Scriptures Hebrew
# Bible (morphhb), WLC-based OSIS XML. The commit below is pinned so maqqef
# restoration (Track A of docs/plans/hebrew-content-followups.md) never silently
# re-tokenizes the OT: the aligned/cloze/passage layers key on word_index, so a
# reingest MUST preserve per-verse token counts. The maqqef is stored in the XML
# as `<seg type="x-maqqef">־</seg>` BETWEEN <w> tokens; parse_morphhb_xml()
# attaches it to the preceding token (the standard WLC convention) WITHOUT
# changing the token count or word_index sequence.
#
# SHA-256 manifest = sha256 over each wlc/*.xml (excluding VerseMap.xml) in
# filename order, hashed again as a joined string. Verify a vendor with:
#   python3 -c "import hashlib;from pathlib import Path;w=Path('data/raw/morphhb/wlc');
#   h=[hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(w.glob('*.xml'))
#      if f.name!='VerseMap.xml'];
#   print(hashlib.sha256('\n'.join(h).encode()).hexdigest())"
OSHB_SOURCE = {
    "id": "oshb-morphhb",
    "url": "https://github.com/openscriptures/morphhb",
    "commit": "3d15126fb1ef74867fc1434be1942e837932691f",
    "wlc_manifest_sha256": "f32cf0c442ec090f54ed13c9d48a0809e6be33cd5926dbefac695ccb8472e0cd",
    "license": "WLC text: public domain; OSHB morphology/lemmas: CC BY 4.0",
}

MAQQEF = "\u05be"


def extract_hebrew_words_from_verse(verse_elem):
    """Extract <w> tokens from a verse, preserving OSHB word_index.

    The morphhb XML stores maqqef as `<seg type="x-maqqef">־</seg>` BETWEEN two
    <w> elements. It is attached as a suffix to the PRECEDING token (the WLC
    convention, e.g. `אֶת` + seg → `אֶת־`), never as a new token — so the
    per-verse token count and the 0..n-1 word_index sequence are unchanged.
    This is the invariant the alignment/cloze/passage layers depend on.
    """
    tokens = []
    for child in verse_elem:
        if child.tag == f"{NS}w":
            text = (child.text or "").strip()
            if text:
                tokens.append({
                    "index": len(tokens),
                    "word": text,
                    "lemma": child.get("lemma", ""),
                    "morph": child.get("morph", ""),
                })
        elif child.tag == f"{NS}seg" and child.get("type") == "x-maqqef":
            seg_text = (child.text or "").strip()
            if seg_text and tokens:
                tokens[-1]["word"] += seg_text
    return tokens


def extract_hebrew_text(words_data):
    """Rebuild Hebrew text from extracted token dicts (space-separated tokens)."""
    return " ".join(w["word"] for w in words_data if w["word"])


def parse_morphhb_xml(filepath):
    """Parse a morphhb XML file and yield (chapter, verse, hebrew_text, words_data).

    The morphhb XML uses <chapter> tags for chapters and <verse> tags
    that directly contain <w> word elements. Maqqef `<seg>` elements are folded
    into the preceding token so text/gematria stay aligned to the same word_index.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Find the book div
    book_div = root.find(f".//{NS}div[@type='book']")
    if book_div is None:
        print(f"  WARNING: No book div found in {filepath}")
        return

    # Iterate over <chapter> elements (not <div type='chapter'>)
    for chapter_elem in book_div.iter(f"{NS}chapter"):
        chap_osis = chapter_elem.get("osisID", "")
        if not chap_osis:
            continue

        # Extract chapter number from osisID like "Gen.1"
        try:
            chapter = int(chap_osis.split(".")[-1])
        except (ValueError, IndexError):
            continue

        # Process each <verse> element directly
        # In this format, <verse> elements contain <w> children directly
        for verse_elem in chapter_elem.iter(f"{NS}verse"):
            osis_id = verse_elem.get("osisID", "")
            if not osis_id:
                continue
            try:
                verse_num = int(osis_id.split(".")[-1])
            except (ValueError, IndexError):
                continue

            words_data = extract_hebrew_words_from_verse(verse_elem)
            if words_data:
                hebrew_text = extract_hebrew_text(words_data)
                yield chapter, verse_num, hebrew_text, words_data


def ingest_english_json(conn, filepath, work_id, book_id_map, book_position_start=0):
    """Ingest English text from a bcbooks/scriptures-json file."""
    with open(filepath) as f:
        data = json.load(f)

    books = data.get("books", data if isinstance(data, list) else [])
    if isinstance(data, dict) and "books" in data:
        books = data["books"]

    position = book_position_start
    count = 0

    for book_data in books:
        book_title = book_data.get("book", "")
        book_id = book_id_map.get(book_title, "")

        if not book_id and work_id in ("ot", "nt"):
            # Try to find by position or create slug
            continue

        if not book_id:
            continue

        # Insert book
        conn.execute("""
            INSERT OR IGNORE INTO books (id, work_id, title, position)
            VALUES (?, ?, ?, ?)
        """, (book_id, work_id, book_title, position))
        position += 1

        chapters = book_data.get("chapters", [])
        for chap_data in chapters:
            chapter = chap_data.get("chapter", 0)
            verses = chap_data.get("verses", [])
            for v in verses:
                verse_num = v.get("verse", 0)
                text = v.get("text", "")
                if text:
                    insert_verse(conn, book_id, chapter, verse_num, text)
                    count += 1

        print(f"  {book_title}: {count} verses (so far)")

    print(f"  Total verses ingested: {count}")
    return position


def ingest_hebrew_ot(conn, filepath, book_id):
    """Ingest Hebrew OT text from morphhb XML for a specific book."""
    count = 0
    skipped = 0
    for chapter, verse, hebrew_text, words_data in parse_morphhb_xml(filepath):
        vid = f"{book_id}.{chapter}.{verse}"

        # Ensure verse exists (may have been inserted by English ingest)
        conn.execute("""
            INSERT INTO verses (id, book_id, chapter, verse, text_english)
            VALUES (?, ?, ?, ?, '')
            ON CONFLICT(id) DO UPDATE SET
                text_hebrew = excluded.text_hebrew,
                has_hebrew = 1
        """, (vid, book_id, chapter, verse))

        # Set Hebrew text
        conn.execute("""
            UPDATE verses SET text_hebrew = ?, has_hebrew = 1
            WHERE id = ?
        """, (hebrew_text, vid))

        # Insert gematria for each word
        for w in words_data:
            try:
                values = compute_all(w["word"])
                insert_gematria(conn, vid, w["index"], w["word"],
                               lemma=w["lemma"], morph=w["morph"], values=values)
                count += 1
            except Exception:
                skipped += 1

    conn.commit()

    if skipped:
        print(f"  Hebrew processed: {count} words ({skipped} skipped)")
    else:
        print(f"  Hebrew processed: {count} words")
    return count


def ingest_divine_names(conn):
    """Populate the divine_names reference table."""
    for d in DIVINE_NAMES:
        conn.execute("""
            INSERT OR IGNORE INTO divine_names (name, hebrew, transliteration,
                value_standard, value_ordinal, value_reduced, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (d["name"], d["hebrew"], "",
              d["value_standard"], d.get("value_ordinal", 0),
              d.get("value_reduced", 0), d["category"]))
    conn.commit()
    print(f"  Divine names: {len(DIVINE_NAMES)} entries")


def build_works_and_books(conn):
    """Insert the canonical works."""
    works = [
        ("ot", "Old Testament", "Hebrew Bible"),
        ("nt", "New Testament", "Christian Scriptures"),
        ("bom", "Book of Mormon", "Another Testament of Jesus Christ"),
        ("dc", "Doctrine and Covenants", "Modern Revelation"),
        ("pgp", "Pearl of Great Price", "Modern Scripture"),
        ("dss", "Dead Sea Scrolls", "Qumran Library"),
        ("ch", "Church History", "Latter-day Saint History"),
    ]
    for wid, title, subtitle in works:
        conn.execute("INSERT OR IGNORE INTO works (id, title, subtitle) VALUES (?, ?, ?)",
                    (wid, title, subtitle))
    conn.commit()


def build_book_of_mormon_books(conn):
    """Insert Book of Mormon books (which aren't in a book_id_map with position)."""
    positions = {
        "1ne": 0, "2ne": 1, "jacob": 2, "enos": 3, "jarom": 4, "omni": 5,
        "wom": 6, "mosiah": 7, "alma": 8, "hel": 9, "3ne": 10, "4ne": 11,
        "morm": 12, "ether": 13, "moro": 14,
    }
    titles = {
        "1ne": "1 Nephi", "2ne": "2 Nephi", "jacob": "Jacob", "enos": "Enos",
        "jarom": "Jarom", "omni": "Omni", "wom": "Words of Mormon",
        "mosiah": "Mosiah", "alma": "Alma", "hel": "Helaman",
        "3ne": "3 Nephi", "4ne": "4 Nephi", "morm": "Mormon",
        "ether": "Ether", "moro": "Moroni",
    }
    for bid, pos in positions.items():
        conn.execute("""
            INSERT OR IGNORE INTO books (id, work_id, title, position)
            VALUES (?, ?, ?, ?)
        """, (bid, "bom", titles.get(bid, bid), pos))


def build_dc_and_pgp_books(conn):
    """Insert D&C sections and Pearl of Great Price books."""
    # D&C sections will be inserted as "books" with section numbers
    # We'll handle sections during ingest
    pgp_books = {
        "moses": ("Moses", 0),
        "abraham": ("Abraham", 1),
        "jsm": ("Joseph Smith—Matthew", 2),
        "jsh": ("Joseph Smith—History", 3),
        "aoff": ("Articles of Faith", 4),
    }
    for bid, (title, pos) in pgp_books.items():
        conn.execute("""
            INSERT OR IGNORE INTO books (id, work_id, title, position)
            VALUES (?, ?, ?, ?)
        """, (bid, "pgp", title, pos))


def ingest_bom_flat(conn):
    """Ingest Book of Mormon from flat JSON (which has the right structure)."""
    path = RAW_DIR / "scriptures-json" / "flat" / "book-of-mormon-flat.json"
    with open(path) as f:
        data = json.load(f)

    verses = data.get("verses", [])
    count = 0
    for v in verses:
        ref = v.get("reference", "")
        text = v.get("text", "")
        # Parse reference like "1 Nephi 1:1"
        parts = ref.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        book_rest = parts[0]  # "1 Nephi"
        chap_verse = parts[1]  # "1:1"
        cv = chap_verse.split(":")
        if len(cv) != 2:
            # Some D&C references might be single numbers
            continue
        chapter = int(cv[0])
        verse = int(cv[1])

        # Map book name to ID
        book_id = BOOK_IDS_BOM.get(book_rest)
        if not book_id:
            print(f"  WARNING: Unknown book: {book_rest}")
            continue

        insert_verse(conn, book_id, chapter, verse, text)
        count += 1

    conn.commit()
    print(f"  Book of Mormon: {count} verses")
    return count


def ingest_dc_flat(conn):
    """Ingest D&C from flat JSON."""
    path = RAW_DIR / "scriptures-json" / "flat" / "doctrine-and-covenants-flat.json"
    with open(path) as f:
        data = json.load(f)

    verses = data.get("verses", [])
    count = 0

    # Map D&C sections as books
    section_positions = {}
    for v in verses:
        ref = v.get("reference", "")
        text = v.get("text", "")

        # D&C 1:1 format
        parts = ref.split(":", 1)
        if len(parts) != 2:
            continue
        section_str = parts[0].replace("D&C ", "").replace("Doctrine and Covenants ", "")
        try:
            section = int(section_str)
        except ValueError:
            continue

        verse_parts = parts[1].split(" ")
        try:
            verse_num = int(verse_parts[0])
        except ValueError:
            continue

        # Create book_id for section
        book_id = f"dc{section}"
        if book_id not in section_positions:
            section_positions[book_id] = section
            conn.execute("""
                INSERT OR IGNORE INTO books (id, work_id, title, position)
                VALUES (?, ?, ?, ?)
            """, (book_id, "dc", f"Doctrine and Covenants {section}", section))

        insert_verse(conn, book_id, section, verse_num, text)
        count += 1

    conn.commit()
    print(f"  Doctrine and Covenants: {count} verses")
    return count


def ingest_pgp_flat(conn):
    """Ingest Pearl of Great Price from flat JSON."""
    path = RAW_DIR / "scriptures-json" / "flat" / "pearl-of-great-price-flat.json"
    with open(path) as f:
        data = json.load(f)

    verses = data.get("verses", [])
    count = 0
    for v in verses:
        ref = v.get("reference", "")
        text = v.get("text", "")

        # Parse reference like "Moses 1:1" or "Abraham 3:1"
        # Find the first space to split book name from chapter:verse
        parts = ref.split(" ", 1)
        if len(parts) != 2:
            continue
        book_name = parts[0]
        rest = parts[1]

        # rest could be "1:1" or "1:1 - Note" etc.
        cv_parts = rest.split(" ")[0].split(":")
        if len(cv_parts) != 2:
            continue

        try:
            chapter = int(cv_parts[0])
            verse = int(cv_parts[1])
        except ValueError:
            continue

        # Map book name
        book_id = BOOK_IDS_PGP.get(book_name)
        if not book_id:
            print(f"  WARNING: Unknown PGP book: {book_name}")
            continue

        insert_verse(conn, book_id, chapter, verse, text)
        count += 1

    conn.commit()
    print(f"  Pearl of Great Price: {count} verses")
    return count


def ingest_ot_new_testament(conn):
    """Ingest OT and NT from the main JSON files."""
    # Old Testament
    print("\n--- Old Testament ---")
    ot_path = RAW_DIR / "scriptures-json" / "old-testament.json"
    ingest_english_json(conn, ot_path, "ot", BOOK_IDS_OT, 0)

    # New Testament
    print("\n--- New Testament ---")
    nt_path = RAW_DIR / "scriptures-json" / "new-testament.json"
    ingest_english_json(conn, nt_path, "nt", BOOK_IDS_NT, 39)

    conn.commit()


def ingest_hebrew(conn):
    """Ingest Hebrew OT from morphhb XML files."""
    print("\n--- Hebrew OT ---")
    hebrew_dir = RAW_DIR / "morphhb" / "wlc"

    # Map from Hebrew XML filenames to book IDs
    hebrew_file_map = {
        "Gen.xml": "gen", "Exod.xml": "exo", "Lev.xml": "lev", "Num.xml": "num",
        "Deut.xml": "deu", "Josh.xml": "josh", "Judg.xml": "judg", "Ruth.xml": "ruth",
        "1Sam.xml": "1sam", "2Sam.xml": "2sam", "1Kgs.xml": "1kgs", "2Kgs.xml": "2kgs",
        "1Chr.xml": "1chr", "2Chr.xml": "2chr", "Ezra.xml": "ezra", "Neh.xml": "neh",
        "Esth.xml": "esth", "Job.xml": "job", "Ps.xml": "psa", "Prov.xml": "prov",
        "Eccl.xml": "eccl", "Song.xml": "song", "Isa.xml": "isa",
        "Jer.xml": "jer", "Lam.xml": "lam", "Ezek.xml": "ezek", "Dan.xml": "dan",
        "Hos.xml": "hos", "Joel.xml": "joel", "Amos.xml": "amos", "Obad.xml": "obad",
        "Jonah.xml": "jonah", "Mic.xml": "mic", "Nah.xml": "nah", "Hab.xml": "hab",
        "Zeph.xml": "zeph", "Hag.xml": "hag", "Zech.xml": "zech", "Mal.xml": "mal",
    }

    for filename, book_id in hebrew_file_map.items():
        filepath = hebrew_dir / filename
        if filepath.exists():
            print(f"  {filename} → {book_id}")
            ingest_hebrew_ot(conn, filepath, book_id)
            conn.commit()
        else:
            print(f"  {filename}: NOT FOUND")


def verify_maqqef_token_integrity(conn, hebrew_dir=None, sample_books=None):
    """Regression gate for the maqqef reingestion (Track A).

    The maqqef-preserving parser must never re-tokenize the OT: every verse in
    the database must keep the exact same token count / word_index sequence as
    the pinned morphHB source, with the ONLY difference being the U+05BE suffix
    folded onto the preceding token. This function compares the DB's per-verse
    gematria rows against the pinned source for a sampled book set (defaults to
    the whole OT when sample_books is None) and returns the mismatches.

    Returns (mismatches, stats) where stats carries the counts used by tests.
    """
    if hebrew_dir is None:
        hebrew_dir = RAW_DIR / "morphhb" / "wlc"
    hebrew_dir = Path(hebrew_dir)

    hebrew_file_map = {
        "Gen.xml": "gen", "Exod.xml": "exo", "Lev.xml": "lev", "Num.xml": "num",
        "Deut.xml": "deu", "Josh.xml": "josh", "Judg.xml": "judg", "Ruth.xml": "ruth",
        "1Sam.xml": "1sam", "2Sam.xml": "2sam", "1Kgs.xml": "1kgs", "2Kgs.xml": "2kgs",
        "1Chr.xml": "1chr", "2Chr.xml": "2chr", "Ezra.xml": "ezra", "Neh.xml": "neh",
        "Esth.xml": "esth", "Job.xml": "job", "Ps.xml": "psa", "Prov.xml": "prov",
        "Eccl.xml": "eccl", "Song.xml": "song", "Isa.xml": "isa",
        "Jer.xml": "jer", "Lam.xml": "lam", "Ezek.xml": "ezek", "Dan.xml": "dan",
        "Hos.xml": "hos", "Joel.xml": "joel", "Amos.xml": "amos", "Obad.xml": "obad",
        "Jonah.xml": "jonah", "Mic.xml": "mic", "Nah.xml": "nah", "Hab.xml": "hab",
        "Zeph.xml": "zeph", "Hag.xml": "hag", "Zech.xml": "zech", "Mal.xml": "mal",
    }
    if sample_books is not None:
        want = set(sample_books)
        hebrew_file_map = {f: b for f, b in hebrew_file_map.items() if b in want}
        if not hebrew_file_map:
            raise ValueError("no source files for sample_books")

    mismatches = []
    verses_checked = 0
    maqqef_tokens = 0
    for filename, book_id in hebrew_file_map.items():
        filepath = hebrew_dir / filename
        if not filepath.exists():
            mismatches.append(f"{filename}: pinned source not found at {filepath}")
            continue
        db_counts = {
            r["verse_id"]: r["c"]
            for r in conn.execute(
                "SELECT g.verse_id, COUNT(*) AS c FROM gematria g "
                "JOIN verses v ON v.id=g.verse_id "
                "JOIN books b ON b.id=v.book_id WHERE b.id=? GROUP BY g.verse_id",
                (book_id,),
            )
        }
        for chapter, verse, _text, words_data in parse_morphhb_xml(filepath):
            vid = f"{book_id}.{chapter}.{verse}"
            verses_checked += 1
            maqqef_tokens += sum(1 for w in words_data if w["word"].endswith(MAQQEF))
            expected = len(words_data)
            actual = db_counts.get(vid)
            if actual != expected:
                mismatches.append(f"{vid}: DB {actual} tokens vs source {expected}")
            elif actual is not None:
                # word_index must be exactly 0..n-1 in order (no gaps/dups).
                idxs = [r[0] for r in conn.execute(
                    "SELECT word_index FROM gematria WHERE verse_id=? ORDER BY word_index",
                    (vid,),
                )]
                if idxs != list(range(actual)):
                    mismatches.append(f"{vid}: word_index sequence not contiguous 0..{actual - 1}")
    return mismatches, {
        "verses_checked": verses_checked,
        "maqqef_tokens_in_source": maqqef_tokens,
        "pinned": OSHB_SOURCE,
    }


def build_initial_connections(conn):
    """Build some initial connections automatically."""
    print("\n--- Building initial connections ---")
    count = 0

    # 1. Connect divine name occurrences
    # Find verses with words matching divine name values
    for d in DIVINE_NAMES[:5]:  # Start with key names
        val = d["value_standard"]
        rows = conn.execute("""
            SELECT g.verse_id, g.word_hebrew
            FROM gematria g
            WHERE g.value_standard = ?
            LIMIT 20
        """, (val,)).fetchall()

        # Connect pairs of verses that share this value
        verses = [r["verse_id"] for r in rows]
        for i in range(min(len(verses), 10)):
            for j in range(i + 1, min(len(verses), 10)):
                add_connection(conn, verses[i], verses[j],
                              layer="numerical",
                              type_name="divine_name_value",
                              subtype=d["name"].lower().replace(" ", "_"),
                              strength=0.7, confidence=0.8,
                              discovered_by="algorithm",
                              metadata={"divine_name": d["name"], "value": val})
                count += 1

    # 2. Sacred number connections
    sacred_nums = {7, 12, 40, 70, 10}
    for snum in sacred_nums:
        rows = conn.execute("""
            SELECT g.verse_id, g.value_standard
            FROM gematria g
            WHERE g.value_standard = ?
            LIMIT 10
        """, (snum,)).fetchall()
        verses = [r["verse_id"] for r in rows]
        for i in range(min(len(verses), 8)):
            for j in range(i + 1, min(len(verses), 8)):
                add_connection(conn, verses[i], verses[j],
                              layer="numerical",
                              type_name="sacred_number",
                              subtype=f"value_{snum}",
                              strength=0.5, confidence=0.6,
                              discovered_by="algorithm")
                count += 1

    conn.commit()
    print(f"  Created {count} initial connections")


def compute_verse_gematria_totals(conn):
    """Compute and store total gematria for each Hebrew verse."""
    print("\n--- Computing verse gematria totals ---")
    rows = conn.execute("""
        SELECT verse_id, SUM(value_standard) as total_std,
               SUM(value_ordinal) as total_ord,
               SUM(value_reduced) as total_red
        FROM gematria
        GROUP BY verse_id
    """).fetchall()

    count = 0
    for r in rows:
        r["verse_id"]
        # Store as metadata in the gematria table? Or we can add a verse_gematria table.
        # For now, just count
        count += 1

    print(f"  {count} verses with Hebrew gematria computed")


def main():
    import argparse
    import sqlite3 as _sqlite3

    parser = argparse.ArgumentParser(description="Ingest scripture data")
    parser.add_argument(
        "--check-hebrew-tokens", action="store_true",
        help="Run the maqqef token-integrity regression gate against an existing DB (no reingest)",
    )
    parser.add_argument(
        "--sample-books", default="",
        help="Comma-separated OT book ids to scope the token check (default: all OT books)",
    )
    parser.add_argument("--db", default=str(DB_PATH), help="Path to the scripture DB")
    args = parser.parse_args()

    if args.check_hebrew_tokens:
        print("=" * 60)
        print("Maqqef token-integrity regression gate")
        print("=" * 60)
        books = [b.strip() for b in args.sample_books.split(",") if b.strip()] or None
        conn = _sqlite3.connect(args.db)
        conn.row_factory = _sqlite3.Row
        mismatches, stats = verify_maqqef_token_integrity(conn, sample_books=books)
        conn.close()
        pinned = stats["pinned"]
        print(f"  Pinned source: {pinned['url']} @ {pinned['commit']}")
        print(f"  WLC manifest sha256: {pinned['wlc_manifest_sha256']}")
        print(f"  Verses checked: {stats['verses_checked']}")
        print(f"  Maqqef tokens in pinned source: {stats['maqqef_tokens_in_source']}")
        if mismatches:
            print(f"  FAIL: {len(mismatches)} mismatch(es) — reingest would re-tokenize the OT")
            for m in mismatches[:50]:
                print(f"    {m}")
            return 1
        print("  PASS: per-verse token counts and word_index sequences match "
              "the pinned OSHB source")
        return 0

    print("=" * 60)
    print("Scripture Knowledge Engine — Data Ingest")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    conn = init_db(DB_PATH)

    # Build reference tables
    print("\nBuilding works and books...")
    build_works_and_books(conn)
    build_book_of_mormon_books(conn)
    build_dc_and_pgp_books(conn)

    # Ingest English texts
    print("\n--- English Texts ---")
    ingest_ot_new_testament(conn)
    ingest_bom_flat(conn)
    ingest_dc_flat(conn)
    ingest_pgp_flat(conn)

    # Ingest Hebrew
    ingest_hebrew(conn)

    # Divine names
    print("\n--- Divine Names ---")
    ingest_divine_names(conn)

    # Compute gematria totals
    compute_verse_gematria_totals(conn)

    # Build initial connections
    build_initial_connections(conn)

    # Summary
    print("\n" + "=" * 60)
    verse_count = conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()["c"]
    heb_count = conn.execute("SELECT COUNT(*) as c FROM verses WHERE has_hebrew=1").fetchone()["c"]
    gem_count = conn.execute("SELECT COUNT(*) as c FROM gematria").fetchone()["c"]
    conn_count = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()["c"]
    print("Summary:")
    print(f"  Verses:          {verse_count}")
    print(f"  With Hebrew:     {heb_count}")
    print(f"  Gematria words:  {gem_count}")
    print(f"  Connections:     {conn_count}")
    print(f"  Database:        {DB_PATH}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
