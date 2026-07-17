#!/usr/bin/env python3
"""
Build a minimal test database for CI and fast local testing.

Creates a ~500KB SQLite database at data/test/test.db with:
  - Full schema (tables, indexes, FTS5 virtual tables)
  - Minimal verse data (a few verses per test book)
  - Sample connections, entities, gematria, topics

Usage:
  python3 scripts/create_test_db.py                # Create fresh
  python3 scripts/create_test_db.py --reset        # Rebuild from scratch
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEST_DB_DIR = ROOT / "data" / "test"
TEST_DB_PATH = TEST_DB_DIR / "test.db"


# ── Schema DDL (subset of lib/db.py SCHEMA_SQL) ───────────────────────

# Load schema from production DB dump (kept in sync, includes all 105 tables)
SCHEMA_FILE = Path(__file__).parent.parent / "data" / "test" / "full_schema.sql"
if not SCHEMA_FILE.exists():
    print("Error: full_schema.sql not found. Run schema extraction script first.", file=sys.stderr)
    print("  python3 -c \"... extract from production DB ...\"", file=sys.stderr)
    sys.exit(1)

SCHEMA_SQL = SCHEMA_FILE.read_text()


# ── Test data ─────────────────────────────────────────────────────────

def insert_test_data(conn):
    """Insert minimal test data — enough for all tests to pass."""
    c = conn

    # Works
    c.execute("INSERT INTO works (id, title, position) VALUES ('ot', 'Old Testament', 1)")
    c.execute("INSERT INTO works (id, title, position) VALUES ('nt', 'New Testament', 2)")
    c.execute("INSERT INTO works (id, title, position) VALUES ('bom', 'Book of Mormon', 3)")
    c.execute("INSERT INTO works (id, title, position) VALUES ('dc', 'Doctrine and Covenants', 4)")

    # Books
    books = [
        ("gen", "ot", "Genesis", 1),
        ("exo", "ot", "Exodus", 2),
        ("lev", "ot", "Leviticus", 3),
        ("num", "ot", "Numbers", 4),
        ("deu", "ot", "Deuteronomy", 5),
        ("isa", "ot", "Isaiah", 23),
        ("psa", "ot", "Psalms", 19),
        ("matt", "nt", "Matthew", 40),
        ("mark", "nt", "Mark", 41),
        ("luke", "nt", "Luke", 42),
        ("john", "nt", "John", 43),
        ("acts", "nt", "Acts", 44),
        ("rom", "nt", "Romans", 45),
        ("1ne", "bom", "1 Nephi", 1),
    ]
    # D&C books
    for sec in [1, 10, 76, 138]:
        books.append((f"dc{sec}", "dc", f"D&C Section {sec}", 100 + sec))

    for bid, wid, title, pos in books:
        c.execute(
            "INSERT INTO books (id, work_id, title, position) VALUES (?, ?, ?, ?)",
            (bid, wid, title, pos),
        )

    # Verses — gen.1.1, john.1.1, isa.6.1, psa.23.1, matt.5.3
    verses_data = [
        # gen.1.1
        ("gen.1.1", "gen", 1, 1,
         "In the beginning God created the heaven and the earth.",
         "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ",
         "bereshit bara elohim et hashamayim ve'et ha'aretz",
         "", 1, 0),
        # gen.1.2
        ("gen.1.2", "gen", 1, 2,
         "And the earth was without form, and void; and darkness was upon the face of the deep.",
         "וְהָאָרֶץ הָיְתָה תֹהוּ וָבֹהוּ וְחֹשֶׁךְ עַל־פְּנֵי תְהוֹם",
         "veha'aretz hayetah tohu vavohu vechoshech al-penei tehom",
         "", 1, 0),
        # john.1.1
        ("john.1.1", "john", 1, 1,
         "In the beginning was the Word, and the Word was with God, and the Word was God.",
         "",
         "",
         "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν Θεόν, καὶ Θεὸς ἦν ὁ λόγος.",
         0, 1),
        # john.1.2
        ("john.1.2", "john", 1, 2,
         "The same was in the beginning with God.",
         "",
         "",
         "οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν Θεόν.",
         0, 1),
        # isa.6.1
        ("isa.6.1", "isa", 6, 1,
         "In the year that king Uzziah died I saw also the Lord sitting upon a throne, high and lifted up.",
         "בִּשְׁנַת־מוֹת הַמֶּלֶךְ עֻזִּיָּהוּ וָאֶרְאֶה אֶת־אֲדֹנָי יֹשֵׁב עַל־כִּסֵּא רָם וְנִשָּׂא",
         "bishnat-mot hamelech uziyahu va'er'eh et-adonai yoshev al-kise ram venisa",
         "", 1, 0),
        # psa.23.1
        ("psa.23.1", "psa", 23, 1,
         "The LORD is my shepherd; I shall not want.",
         "יְהוָה רֹעִי לֹא אֶחְסָר",
         "yhwh ro'i lo echsar",
         "", 1, 0),
        # matt.5.3
        ("matt.5.3", "matt", 5, 3,
         "Blessed are the poor in spirit: for theirs is the kingdom of heaven.",
         "",
         "",
         "Μακάριοι οἱ πτωχοὶ τῷ πνεύματι, ὅτι αὐτῶν ἐστιν ἡ βασιλεία τῶν οὐρανῶν.",
         0, 1),
        # Additional verses for connection targets
        ("gen.12.1", "gen", 12, 1,
         "Now the LORD had said unto Abram, Get thee out of thy country.",
         "וַיֹּאמֶר יְהוָה אֶל־אַבְרָם לֶךְ־לְךָ מֵאַרְצְךָ",
         "", "", 1, 0),
        ("gen.22.1", "gen", 22, 1,
         "And it came to pass after these things, that God did tempt Abraham.",
         "וַיְהִי אַחַר הַדְּבָרִים הָאֵלֶּה וְהָאֱלֹהִים נִסָּה אֶת־אַבְרָהָם",
         "", "", 1, 0),
        ("exo.3.14", "exo", 3, 14,
         "And God said unto Moses, I AM THAT I AM.",
         "וַיֹּאמֶר אֱלֹהִים אֶל־מֹשֶׁה אֶהְיֶה אֲשֶׁר אֶהְיֶה",
         "", "", 1, 0),
        ("isa.6.3", "isa", 6, 3,
         "And one cried unto another, and said, Holy, holy, holy, is the LORD of hosts.",
         "וְקָרָא זֶה אֶל־זֶה וְאָמַר קָדוֹשׁ קָדוֹשׁ קָדוֹשׁ יְהוָה צְבָאוֹת",
         "", "", 1, 0),
        ("matt.1.1", "matt", 1, 1,
         "The book of the generation of Jesus Christ, the son of David, the son of Abraham.",
         "",
         "",
         "Βίβλος γενέσεως Ἰησοῦ Χριστοῦ υἱοῦ Δαυὶδ υἱοῦ Ἀβραάμ.",
         0, 1),
        ("1ne.1.1", "1ne", 1, 1,
         "I, Nephi, having been born of goodly parents.",
         "",
         "",
         "", 0, 0),
        # D&C verses — chapter = section number
        ("dc1.1.1", "dc1", 1, 1,
         "Hearken, O ye people of my church, saith the Lord your God.",
         "", "", "", 0, 0),
        ("dc1.1.6", "dc1", 1, 6,
         "The voice of warning shall be unto all people.",
         "", "", "", 0, 0),
        ("dc138.138.1", "dc138", 138, 1,
         "Thus the heavens and the earth were finished.",
         "", "", "", 0, 0),
        ("dc138.138.60", "dc138", 138, 60,
         "For by the power of my Spirit created I them.",
         "", "", "", 0, 0),
    ]
    for row in verses_data:
        vid, bid, ch, vs, en, he, he_tr, gr, heb, grk = row
        c.execute(
            """INSERT INTO verses
               (id, book_id, chapter, verse, text_english, text_hebrew,
                text_hebrew_translit, text_greek, has_hebrew, has_greek)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vid, bid, ch, vs, en, he, he_tr, gr, heb, grk),
        )

    # Connections — a few sample connections
    sample_connections = [
        ("gen.1.1", "john.1.1", "intertextual", "parallel",
         "Both begin with 'In the beginning'", 0.9, 0.95),
        ("gen.1.1", "john.1.1", "linguistic", "same_root",
         "Hebrew bereshit / Greek archē — both mean beginning", 0.7, 0.8),
        ("isa.6.1", "isa.6.3", "structural", "parallelism",
         "Isaiah's vision — throne room scene", 0.8, 0.9),
        ("gen.1.1", "gen.12.1", "interpretive", "call",
         "God calls creation and Abraham into being", 0.5, 0.6),
        ("gen.22.1", "matt.1.1", "intertextual", "typology",
         "Abraham offering Isaac / God offering Jesus", 0.6, 0.7),
        ("exo.3.14", "john.1.1", "sod", "divine_name",
         "I AM / Word — divine self-identification", 0.7, 0.8),
        ("psa.23.1", "john.1.1", "interpretive", "shepherd",
         "The Lord is my shepherd / The Word was God", 0.4, 0.5),
        ("gen.1.2", "gen.1.1", "structural", "parallelism",
         "Creation account continues", 0.8, 0.9),
    ]
    for src, tgt, layer, ctype, subtype, strength, confidence in sample_connections:
        c.execute(
            """INSERT INTO connections
               (source_verse, target_verse, layer, type, subtype,
                strength, confidence, discovered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'test_fixture')""",
            (src, tgt, layer, ctype, subtype, strength, confidence),
        )

    # Gematria — sample Hebrew words
    gematria_data = [
        ("gen.1.1", 0, "בְּרֵאשִׁית", "beginning", "H7225", 913, 541, 4),
        ("gen.1.1", 1, "בָּרָא", "created", "H1254", 203, 205, 2),
        ("gen.1.1", 2, "אֱלֹהִים", "God", "H430", 86, 86, 4),
        ("psa.23.1", 0, "יְהוָה", "YHWH", "H3068", 26, 26, 1),
        ("isa.6.1", 1, "אֲדֹנָי", "Lord", "H136", 65, 65, 2),
    ]
    for vid, idx, word, eng, lemma, std, ord, red in gematria_data:
        c.execute(
            """INSERT INTO gematria
               (verse_id, word_index, word_hebrew, word_english, lemma,
                value_standard, value_ordinal, value_reduced, hebrew_plain)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vid, idx, word, eng, lemma, std, ord, red, word),
        )

    # Greek gematria
    greek_gematria = [
        ("john.1.1", 0, "λόγος", "G3056", 373, 373, 1),
        ("john.1.1", 1, "Θεόν", "G2316", 134, 134, 1),
    ]
    for vid, idx, word, lemma, std, ord, red in greek_gematria:
        c.execute(
            """INSERT INTO gematria_greek
               (verse_id, word_index, word_greek, lemma,
                value_standard, value_ordinal, value_reduced)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (vid, idx, word, lemma, std, ord, red),
        )

    # Entity links
    entities = [
        ("person.abraham", "person", "Abraham", "אַבְרָהָם", "H85", "", ""),
        ("person.moses", "person", "Moses", "מֹשֶׁה", "H4872", "", ""),
        ("person.jesus", "person", "Jesus", "", "", "", "G2424"),
        ("person.david", "person", "David", "דָּוִד", "H1732", "", ""),
        ("place.israel", "place", "Israel", "יִשְׂרָאֵל", "H3478", "", ""),
        ("place.egypt", "place", "Egypt", "מִצְרַיִם", "H4714", "", ""),
        ("place.jerusalem", "place", "Jerusalem", "יְרוּשָׁלַיִם", "H3389", "", ""),
        ("place.zion", "place", "Zion", "צִיּוֹן", "H6726", "", ""),
        ("concept.covenant", "concept", "Covenant", "בְּרִית", "H1285", "", ""),
        ("concept.atonement", "concept", "Atonement", "כִּפֻּר", "H3725", "", ""),
        ("concept.faith", "concept", "Faith", "", "", "G4102", ""),
        ("concept.temple", "concept", "Temple", "הֵיכָל", "H1964", "", ""),
    ]
    for eid, etype, en, he, hs, gn, gs in entities:
        gn = ""
        gs = ""
        if eid == "person.jesus":
            gn = "Ἰησοῦς"
            gs = "G2424"
        c.execute(
            """INSERT INTO entity_links
               (entity_id, entity_type, english_name, hebrew_name,
                hebrew_strongs, greek_name, greek_strongs)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (eid, etype, en, he, hs, gn, gs),
        )

    # Verse-entity links
    ve_links = [
        ("gen.1.1", "place.israel", "mentions"),
        ("gen.1.1", "concept.covenant", "mentions"),
        ("gen.12.1", "person.abraham", "mentions"),
        ("gen.12.1", "place.israel", "mentions"),
        ("gen.22.1", "person.abraham", "mentions"),
        ("exo.3.14", "person.moses", "mentions"),
        ("exo.3.14", "concept.covenant", "mentions"),
        ("isa.6.1", "place.jerusalem", "mentions"),
        ("isa.6.1", "concept.temple", "mentions"),
        ("matt.1.1", "person.abraham", "mentions"),
        ("matt.1.1", "person.david", "mentions"),
        ("matt.1.1", "person.jesus", "mentions"),
        ("john.1.1", "concept.temple", "mentions"),
        ("john.1.1", "concept.faith", "mentions"),
        ("psa.23.1", "place.zion", "mentions"),
        ("isa.6.3", "place.jerusalem", "mentions"),
    ]
    for vid, eid, rel in ve_links:
        c.execute(
            "INSERT OR IGNORE INTO verse_entities (verse_id, entity_id, relationship_type) VALUES (?, ?, ?)",
            (vid, eid, rel),
        )

    # Topics
    c.execute("INSERT INTO topics (name, description) VALUES ('Faith', 'Belief and trust in God')")
    c.execute("INSERT INTO topics (name, description) VALUES ('Covenant', 'Divine agreements')")

    # Topical guide
    c.execute(
        "INSERT INTO topical_guide (id, name, slug) VALUES ('tg:faith', 'Faith', 'faith')",
    )
    c.execute(
        "INSERT INTO topical_guide (id, name, slug) VALUES ('tg:covenant', 'Covenant', 'covenant')",
    )

    # Bible dictionary
    c.execute(
        "INSERT INTO bible_dictionary (id, name, slug, entry_text) VALUES ('bd:faith', 'Faith', 'faith', 'Faith is the substance of things hoped for, the evidence of things not seen.')",
    )
    c.execute(
        "INSERT INTO bible_dictionary (id, name, slug, entry_text) VALUES ('bd:grace', 'Grace', 'grace', 'Grace is the divine means of salvation.')",
    )

    # Assessment items — note column names differ from schema (question_text, correct_answer)
    try:
        c.execute(
            "INSERT INTO assessment_items (question_type, question_text, correct_answer, layer, tier) VALUES (?, ?, ?, ?, ?)",
            ("direct", "What did God create in the beginning?", "the heaven and the earth", "textual", "text"),
        )
        c.execute(
            "INSERT INTO assessment_items (question_type, question_text, correct_answer, layer, tier) VALUES (?, ?, ?, ?, ?)",
            ("direct", "What does John 1:1 say about the Word?", "it was with God and was God", "intertextual", "analysis"),
        )
        # Consistency tier — compares two verses
        c.execute(
            "INSERT INTO assessment_items (question_type, question_text, correct_answer, layer, tier) VALUES (?, ?, ?, ?, ?)",
            ("direct", "How does the creation account in Genesis relate to John's prologue?", "Both begin 'In the beginning' and speak of divine creation", "intertextual", "consistency"),
        )
        # Quiz with verse text formatting (for the verse text test)
        c.execute(
            "INSERT INTO assessment_items (question_type, question_text, correct_answer, layer, tier) VALUES (?, ?, ?, ?, ?)",
            ("direct", "**Genesis 1:1** says: \"In the beginning God created the heaven and the earth.\" What does this teach?", "God created everything", "textual", "text"),
        )
        c.execute(
            "INSERT INTO assessment_items (question_type, question_text, correct_answer, layer, tier) VALUES (?, ?, ?, ?, ?)",
            ("direct", "**John 1:1** says: \"In the beginning was the Word.\" Who is the Word?", "Jesus Christ", "textual", "text"),
        )
    except Exception as e:
        print(f"  ⚠ Could not insert assessment items: {e}")

    conn.commit()


def create_fts_index(conn):
    """Create trigram FTS5 virtual table and populate it."""
    try:
        conn.execute("DROP TABLE IF EXISTS verses_fts_trigram")
        conn.execute("DROP TABLE IF EXISTS verses_fts_trigram_config")
        conn.execute("DROP TABLE IF EXISTS verses_fts_trigram_data")
        conn.execute("DROP TABLE IF EXISTS verses_fts_trigram_idx")
        conn.execute("DROP TABLE IF EXISTS verses_fts_trigram_docsize")
    except Exception:
        pass

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts_trigram USING fts5(
            verse_id UNINDEXED,
            book_id UNINDEXED,
            search_text,
            tokenize='trigram'
        )
    """)

    rows = conn.execute("""
        SELECT id, book_id, text_english, text_hebrew, text_greek
        FROM verses
        WHERE text_english != '' OR text_hebrew != '' OR text_greek != ''
    """).fetchall()

    for r in rows:
        parts = []
        if r["text_hebrew"]:
            parts.append(f"hebrew: {r['text_hebrew']}")
        if r["text_greek"]:
            parts.append(f"greek: {r['text_greek']}")
        if r["text_english"]:
            parts.append(f"english: {r['text_english']}")
        search_text = "  ".join(parts)
        if search_text:
            conn.execute(
                "INSERT INTO verses_fts_trigram (verse_id, book_id, search_text) VALUES (?, ?, ?)",
                (r["id"], r["book_id"], search_text),
            )

    conn.commit()


def create_vec_table(conn):
    """Create vec_verses virtual table if sqlite-vec is available."""
    try:
        import sqlite_vec
        conn.execute("PRAGMA trusted_schema=ON")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_verses USING vec0(
                verse_id TEXT PRIMARY KEY,
                embedding float[384] distance_metric=cosine
            )
        """)
        conn.commit()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Build test database")
    parser.add_argument("--reset", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--no-fts", action="store_true", help="Skip FTS5 index creation")
    args = parser.parse_args()

    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)

    if args.reset and TEST_DB_PATH.exists():
        # Must close all connections first
        try:
            conn.close()
        except Exception:
            pass
        TEST_DB_PATH.unlink()
        # Remove all FTS shadow tables and WAL/SHM
        for suffix in ("-wal", "-shm"):
            p = TEST_DB_PATH.with_suffix(TEST_DB_PATH.suffix + suffix)
            if p.exists():
                p.unlink()

    start = time.time()
    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-8000")

    print("Creating schema...")
    # Split into individual statements, filtering out FTS5 shadow tables
    # that are auto-created by CREATE VIRTUAL TABLE
    stmts = []
    current = ''
    for line in SCHEMA_SQL.split('\n'):
        current += line + '\n'
        if line.strip().endswith(';') and not line.strip().startswith('--'):
            stmts.append(current.strip())
            current = ''
    if current.strip():
        stmts.append(current.strip())

    success = 0
    for stmt in stmts:
        lower = stmt.lower()
        # Skip FTS5 shadow table DDL (auto-created by VIRTUAL TABLE)
        if 'create table' in lower:
            tbl_name = stmt.split('(')[0].strip().split()[-1].strip('"\'`')
            if any(tbl_name.endswith(s) for s in ('_config', '_content', '_data', '_docsize', '_idx')):
                if any(x in tbl_name for x in ('_fts', 'js_sources', 'js_texts')):
                    continue
        try:
            conn.execute(stmt)
            success += 1
        except Exception as e:
            msg = str(e)
            if 'no such module' in msg.lower() or 'already exists' in msg.lower():
                continue
            print(f"  ⚠ Schema stmt {success}: {msg[:80]}")
    conn.commit()
    print(f"  Executed {success} schema statements")

    print("Inserting test data...")
    insert_test_data(conn)

    print("Creating FTS5 trigram index...")
    create_fts_index(conn)

    conn.execute("PRAGMA synchronous=NORMAL")
    conn.commit()

    elapsed = time.time() - start
    size = TEST_DB_PATH.stat().st_size
    verse_count = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    conn_count = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    # Check trigram FTS
    try:
        fts_count = conn.execute("SELECT COUNT(*) FROM verses_fts_trigram").fetchone()[0]
    except Exception:
        fts_count = 0
    print(f"\nDone: {size / 1024:.0f} KB, {verse_count} verses, {conn_count} connections, {fts_count} FTS entries, {elapsed:.1f}s")
    print(f"Path: {TEST_DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
