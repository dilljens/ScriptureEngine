#!/usr/bin/env python3
"""Import Dead Sea Scrolls data — text variants + sectarian connections."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import init_db

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSS_JSON = os.path.join(BASE, "data/dss/biblical_dss_unicode.json")
DSS_ETCBC = os.path.join(BASE, "data/dss/etcbc/tf")

BOOK_MAP = {
    "gen": "gen", "exo": "exo", "lev": "lev", "num": "num", "deu": "deu",
    "josh": "josh", "judg": "judg", "ruth": "ruth",
    "1sam": "1sam", "2sam": "2sam", "1kgs": "1kgs", "2kgs": "2kgs",
    "1chr": "1chr", "2chr": "2chr", "ezra": "ezra", "neh": "neh",
    "esth": "esth", "job": "job", "psa": "psa", "prov": "prov", "eccl": "eccl",
    "song": "song", "isa": "isa", "jer": "jer", "lam": "lam", "ezek": "ezek",
    "dan": "dan", "hos": "hos", "joel": "joel", "amos": "amos", "obad": "obad",
    "jonah": "jonah", "mic": "mic", "nah": "nah", "hab": "hab", "zeph": "zeph",
    "hag": "hag", "zech": "zech", "mal": "mal",
    "genesis": "gen", "exodus": "exo", "leviticus": "lev", "numbers": "num",
    "deuteronomy": "deu", "joshua": "josh", "judges": "judg", "1_samuel": "1sam", "2_samuel": "2sam",
    "1_kings": "1kgs", "2_kings": "2kgs",
    "1_chronicles": "1chr", "2_chronicles": "2chr", "nehemiah": "neh", "esther": "esth", "psalms": "psa", "proverbs": "prov",
    "ecclesiastes": "eccl", "song_of_solomon": "song",
    "isaiah": "isa", "jeremiah": "jer", "lamentations": "lam",
    "ezekiel": "ezek", "daniel": "dan", "hosea": "hos", "obadiah": "obad", "micah": "mic",
    "nahum": "nah", "habakkuk": "hab", "zephaniah": "zeph",
    "haggai": "hag", "zechariah": "zech", "malachi": "mal", "song_of_songs": "song",
}

REF_PAT = re.compile(r'(\w+)\s*[. :]?\s*(\d+)\s*[. :]?\s*(\d+)')


def normalize_ref(ref_str, conn):
    """Parse a ref like 'Num 23:5' or 'Gen.1.1' into bible_ref."""
    m = REF_PAT.match(ref_str.strip())
    if not m:
        return ""
    raw_book = m.group(1).lower()
    book_id = BOOK_MAP.get(raw_book, raw_book)
    try:
        ch = int(m.group(2))
        vs = int(m.group(3))
    except ValueError:
        return ""
    bible_ref = f"{book_id}.{ch}.{vs}"
    return bible_ref


def get_mt_text(bible_ref, conn):
    """Look up MT Hebrew from verses table."""
    row = conn.execute(
        "SELECT text_hebrew FROM verses WHERE id = ?", (bible_ref,)
    ).fetchone()
    return row["text_hebrew"] or "" if row else ""


def scroll_exists(conn, scroll_id):
    return conn.execute(
        "SELECT COUNT(*) FROM dss_texts WHERE scroll_id = ?", (scroll_id,)
    ).fetchone()[0] > 0


def import_biblical():
    """Import Biblical DSS texts from JSON."""
    conn = init_db()
    if not os.path.exists(DSS_JSON):
        print(f"DSS JSON not found at {DSS_JSON}")
        return

    with open(DSS_JSON) as f:
        data = json.load(f)

    count = 0
    for entry in data:
        scroll = entry.get("scroll", "")
        if scroll_exists(conn, scroll):
            continue

        for verse_entry in entry.get("verses", []):
            if not isinstance(verse_entry, (list, tuple)) or len(verse_entry) < 2:
                continue
            ref_str, dss_text = verse_entry[0], verse_entry[1]

            bible_ref = normalize_ref(ref_str, conn)
            mt_text = get_mt_text(bible_ref, conn) if bible_ref else ""

            # Normalize for comparison: remove spaces, maqqeps, etc.
            dss_clean = re.sub(r'[\s\-]', '', dss_text or '')
            mt_clean = re.sub(r'[\s\-/]', '', mt_text or '')

            has_var = 1 if (dss_clean and mt_clean and dss_clean != mt_clean) else 0
            if not dss_text:
                has_var = 0

            conn.execute(
                """INSERT OR IGNORE INTO dss_texts
                   (scroll_id, document_type, bible_ref, dss_hebrew, mt_hebrew,
                    variant_description, has_variant)
                   VALUES (?, 'biblical', ?, ?, ?, ?, ?)""",
                (scroll, bible_ref, dss_text[:500], mt_text[:500],
                 f"DSS variant: {scroll} at {ref_str}" if has_var else "Agrees with MT",
                 has_var)
            )
            count += 1

    conn.commit()
    print(f"Biblical DSS: {count} verses imported ({len(data)} scrolls)")


def create_variant_connections():
    """Create dead_sea_scrolls_variant connections where DSS differs from MT."""
    conn = init_db()
    rows = conn.execute(
        """SELECT scroll_id, bible_ref, dss_hebrew, mt_hebrew
           FROM dss_texts
           WHERE has_variant = 1 AND bible_ref != ''"""
    ).fetchall()

    var_count = 0
    for r in rows:
        existing = conn.execute(
            """SELECT COUNT(*) FROM connections
               WHERE source_verse = ? AND type = 'dead_sea_scrolls_variant'
               AND subtype = ?""",
            (r["bible_ref"], r["scroll_id"])
        ).fetchone()[0]
        if existing > 0:
            continue

        ref = r["bible_ref"]
        note = f"DSS {r['scroll_id']}: {r['dss_hebrew'][:80]} vs MT: {r['mt_hebrew'][:80]}"
        try:
            conn.execute(
                """INSERT INTO connections
                   (source_verse, target_verse, layer, type, subtype,
                    strength, confidence, discovered_by, metadata)
                   VALUES (?, ?, 'textual', 'dead_sea_scrolls_variant', ?,
                           0.9, 0.85, 'text', ?)""",
                (ref, ref, r["scroll_id"],
                 json.dumps({
                     "note": note[:200],
                     "dss_text": r["dss_hebrew"][:200],
                     "source": "BiblicalDSS"
                 }))
            )
            var_count += 1
        except Exception:
            pass

    conn.commit()
    print(f"Variant connections: {var_count}")


def load_etcbc_book_map():
    """Build {node_id -> scroll_id} from the latest ETCBC book.tf."""
    if not os.path.exists(DSS_ETCBC):
        return {}
    versions = sorted(os.listdir(DSS_ETCBC))
    if not versions:
        return {}
    latest = versions[-1]
    book_path = os.path.join(DSS_ETCBC, latest, "book.tf")
    if not os.path.exists(book_path):
        return {}
    mapping = {}
    with open(book_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("@"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                node_id, book = parts
                mapping[node_id] = book
    return mapping


def import_etcbc_biblical():
    """Import additional ETCBC biblical DSS scrolls (not in JSON)."""
    conn = init_db()
    book_map = load_etcbc_book_map()
    if not book_map:
        print("ETCBC data not available, skipping")
        return

    versions = sorted(os.listdir(DSS_ETCBC))
    latest = versions[-1]
    gcons_path = os.path.join(DSS_ETCBC, latest, "g_cons.tf")
    if not os.path.exists(gcons_path):
        return

    # Identify DSS scrolls (non-MT books)
    dss_books = set()
    for _node_id, book in book_map.items():
        if book and not BOOK_MAP.get(book.lower()):
            # Also filter out node IDs that are obviously MT (numbered lines)
            try:
                int(book)
                continue  # skip numeric entries (MT node IDs)
            except ValueError:
                pass
            dss_books.add(book)

    if not dss_books:
        print("No DSS scrolls found in ETCBC data")
        return

    # Read g_cons to map node_id -> consonantal text
    text_map = {}
    with open(gcons_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("@"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                text_map[parts[0]] = parts[1]

    # Group nodes by scroll
    scroll_nodes = {}
    for node_id, book in book_map.items():
        if book in dss_books:
            scroll_nodes.setdefault(book, []).append(node_id)

    count = 0
    for scroll_id, nodes in scroll_nodes.items():
        if scroll_exists(conn, scroll_id):
            continue
        # Collect text for this scroll
        texts = []
        for nid in nodes:
            txt = text_map.get(nid, "")
            if txt:
                texts.append(txt)
        if not texts:
            continue

        combined = " ".join(texts)
        conn.execute(
            """INSERT OR IGNORE INTO dss_texts
               (scroll_id, document_type, dss_hebrew, variant_description, has_variant)
               VALUES (?, 'biblical', ?, 'ETCBC transcription', 0)""",
            (scroll_id, combined[:500])
        )
        count += 1

    conn.commit()
    print(f"ETCBC scrolls: {count}")


def import_sectarian():
    """Import DSS sectarian texts — from the DSS JSON data (some sectarian
    scrolls like 1QHa are not in the dataset, so we seed known scrolls)."""
    conn = init_db()

    # Known sectarian scroll IDs and their descriptions
    # These are documented historical texts with known content
    seed_sectarian = {
        "1QS":    ("Community Rule (Serek ha-Yahad)", "hebrew",
                   "Rules for the yahad community — dualism of light/darkness, "
                   "initiation, communal life, penal code"),
        "1QSa":   ("Rule of the Congregation", "hebrew",
                   "Messianic rule for the end-time congregation of Israel"),
        "1QSb":   ("Rule of the Blessings", "hebrew",
                   "Liturgical blessings for the eschatological community"),
        "1QM":    ("War Scroll (Milhamah)", "hebrew",
                   "Eschatological war between Sons of Light and Sons of Darkness"),
        "1QHa":   ("Hodayot (Thanksgiving Hymns)", "hebrew",
                   "Thanksgiving hymns attributed to the Teacher of Righteousness"),
        "1QpHab": ("Pesher Habakkuk", "hebrew",
                   "Verse-by-verse interpretation of Habakkuk applied to the Qumran community"),
        "11Q13":  ("Melchizedek Scroll", "hebrew",
                   "Melchizedek as heavenly deliverer in the eschatological jubilee"),
        "11Q19":  ("Temple Scroll (11Q19)", "hebrew",
                   "Expanded temple law — building, purity, festivals"),
        "11Q20":  ("Temple Scroll (11Q20 frag.)", "hebrew",
                   "Fragmentary copy of the Temple Scroll"),
        "4Q400":  ("Songs of Sabbath Sacrifice", "hebrew",
                   "Angel liturgy and heavenly temple for the 13 Sabbaths"),
        "4Q401":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q402":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q403":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q404":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q405":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q406":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "4Q407":  ("Songs of Sabbath Sacrifice", "hebrew", "Angel liturgy"),
        "CD":     ("Damascus Document (Cairo Genizah)", "hebrew",
                   "New covenant community in Damascus — laws, admonitions, midrash"),
        "4Q266":  ("Damascus Document (4QDᵃ)", "hebrew", "CD copy from Cave 4"),
        "4Q267":  ("Damascus Document (4QDᵇ)", "hebrew", "CD copy from Cave 4"),
        "4Q268":  ("Damascus Document (4QDᶜ)", "hebrew", "CD copy from Cave 4"),
        "4Q269":  ("Damascus Document (4QDᵈ)", "hebrew", "CD copy from Cave 4"),
        "4Q270":  ("Damascus Document (4QDᵉ)", "hebrew", "CD copy from Cave 4"),
        "4Q271":  ("Damascus Document (4QDᶠ)", "hebrew", "CD copy from Cave 4"),
        "4Q272":  ("Damascus Document (4QDᵍ)", "hebrew", "CD copy from Cave 4"),
        "4Q273":  ("Damascus Document (4QDʰ)", "hebrew", "CD copy from Cave 4"),
        "4Q394":  ("4QMMT (Miqtsat Ma'asei ha-Torah)", "hebrew",
                   "Halakhic letter — some precepts of the Torah"),
        "4Q395":  ("4QMMT", "hebrew", "Halakhic letter"),
        "4Q396":  ("4QMMT", "hebrew", "Halakhic letter"),
        "4Q397":  ("4QMMT", "hebrew", "Halakhic letter"),
        "4Q398":  ("4QMMT", "hebrew", "Halakhic letter"),
        "4Q399":  ("4QMMT", "hebrew", "Halakhic letter"),
        "4Q246":  ("Son of God / Aramaic Apocalypse", "aramaic",
                   "A messianic figure called 'Son of God' and 'Son of the Most High' — "
                   "parallels Luke 1:32-35 and Daniel 7's 'one like a son of man'"),
        "4Q174":  ("Florilegium (4QMidrEschat)", "hebrew",
                   "Eschatological midrash collecting texts about the Davidic Messiah, "
                   "the sanctuary, and the end-time community — interprets 2 Samuel 7 as messianic"),
        "4Q521":  ("Messianic Apocalypse", "hebrew",
                   "A messianic text describing what the Messiah will do: heal the sick, "
                   "raise the dead, preach to the poor — parallels Matthew 11:5/Luke 7:22"),
    }

    count = 0
    for scroll_id, (name, ctype, topic) in seed_sectarian.items():
        existing = conn.execute(
            "SELECT COUNT(*) FROM dss_sectarian WHERE scroll_id = ?",
            (scroll_id,)
        ).fetchone()[0]
        if existing > 0:
            continue

        conn.execute(
            """INSERT OR IGNORE INTO dss_sectarian
               (scroll_id, section, content, content_type, topic)
               VALUES (?, ?, ?, ?, ?)""",
            (scroll_id, "seed",
             f"Known DSS sectarian text: {name}. {topic}",
             ctype, name)
        )
        count += 1

    conn.commit()
    print(f"Sectarian texts: {count}")


def create_sectarian_connections():
    """Create sod-layer connections from DSS sectarian texts to Bible verses."""
    conn = init_db()

    parallels = [
        ("4Q400", "rev.4.1", "sod", "dss_sectarian",
         "Songs of Sabbath Sacrifice — angelic liturgy parallels Revelation's heavenly temple scenes"),
        ("4Q405", "ezek.1.1", "sod", "dss_sectarian",
         "Songs of Sabbath Sacrifice — chariot throne visions parallel Ezekiel's merkabah"),
        ("4Q403", "isa.6.1", "sod", "dss_sectarian",
         "Songs of Sabbath Sacrifice — 'Holy, holy, holy' liturgy parallels Isaiah's temple vision"),
        ("11Q13", "heb.7.1", "sod", "dss_sectarian",
         "Melchizedek Scroll — Melchizedek as heavenly high priest, parallels Hebrews 7"),
        ("11Q13", "psa.110.4", "sod", "dss_sectarian",
         "Melchizedek Scroll — interprets Psalm 110:4 as Melchizedek's eternal priesthood"),
        ("11Q13", "lev.25.1", "sod", "dss_sectarian",
         "Melchizedek Scroll — connects Melchizedek to the jubilee release"),
        ("11Q19", "exo.25.1", "sod", "dss_sectarian",
         "Temple Scroll — expanded temple law paralleling Exodus tabernacle instructions"),
        ("11Q19", "deu.12.1", "sod", "dss_sectarian",
         "Temple Scroll — temple centralization laws expanding Deuteronomy 12"),
        ("11Q19", "ezek.40.1", "sod", "dss_sectarian",
         "Temple Scroll — temple measurements and layout parallel Ezekiel's temple vision"),
        ("1QS", "1cor.3.16", "sod", "dss_sectarian",
         "Community Rule — community as spiritual temple, parallels Paul's 'you are the temple of God'"),
        ("1QS", "eph.2.21", "sod", "dss_sectarian",
         "Community Rule — the community as a holy house built for God, parallels Ephesians"),
        ("1QS", "john.17.1", "sod", "dss_sectarian",
         "Community Rule — unity of the community as a reflection of divine unity"),
        ("1QM", "rev.19.11", "sod", "dss_sectarian",
         "War Scroll — eschatological war between sons of light and sons of darkness parallels Revelation"),
        ("1QM", "rev.12.7", "sod", "dss_sectarian",
         "War Scroll — heavenly war and angelic combat parallels Revelation's war in heaven"),
        ("1QpHab", "hab.2.4", "sod", "dss_sectarian",
         "Pesher Habakkuk — interprets 'the just shall live by his faith' as faithful community"),
        ("1QpHab", "rom.1.17", "sod", "dss_sectarian",
         "Pesher Habakkuk — Paul's use of 'the just shall live by faith' has DSS interpretive parallels"),
        ("CD", "jer.31.31", "sod", "dss_sectarian",
         "Damascus Document — New Covenant in the land of Damascus, parallels Jeremiah's new covenant"),
        ("CD", "heb.8.8", "sod", "dss_sectarian",
         "Damascus Document — new covenant community in exile, parallels Hebrews' new covenant"),
        ("1QHa", "phil.2.5", "sod", "dss_sectarian",
         "Hodayot — self-humbling exaltation pattern parallels the Christ hymn in Philippians 2"),
        ("1QHa", "col.1.15", "sod", "dss_sectarian",
         "Hodayot — creation through wisdom/word parallels Colossians' Christ hymn"),
        ("4Q246", "luke.1.32", "sod", "dss_sectarian",
         "Son of God text — 'He shall be called Son of God, and they shall call him Son of the Most High' "
         "directly parallels Gabriel's annunciation: 'He shall be called the Son of the Highest'"),
        ("4Q246", "luke.1.35", "sod", "dss_sectarian",
         "Son of God text — the title 'Son of God' applied to a messianic figure in DSS "
         "parallels the angel Gabriel's declaration to Mary"),
        ("4Q246", "dan.7.13", "sod", "dss_sectarian",
         "Son of God text — the figure who receives eternal dominion and is called 'Son of God' "
         "parallels Daniel's 'one like a son of man' who receives dominion"),
        ("4Q174", "2sam.7.14", "sod", "dss_sectarian",
         "Florilegium — interprets the Davidic covenant as messianic: 'I will be his father "
         "and he shall be my son' applied to the Davidic Messiah"),
        ("4Q174", "psa.2.7", "sod", "dss_sectarian",
         "Florilegium — collects messianic prooftexts including Psalm 2's 'Thou art my Son'"),
        ("4Q521", "matt.11.5", "sod", "dss_sectarian",
         "Messianic Apocalypse — the works of the Messiah: heal the sick, raise the dead, "
         "preach to the poor directly parallels Jesus' response to John the Baptist"),
        ("4Q521", "luke.7.22", "sod", "dss_sectarian",
         "Messianic Apocalypse — same list of messianic works paralleling Jesus' ministry"),
    ]

    # sectarian scroll IDs don't exist in verses table, so disable FK temporarily
    conn.execute("PRAGMA foreign_keys=OFF")

    count = 0
    for scroll_id, target_verse, layer, typ, note in parallels:
        existing = conn.execute(
            """SELECT COUNT(*) FROM connections
               WHERE type = ? AND subtype = ? AND target_verse = ?""",
            (typ, scroll_id, target_verse)
        ).fetchone()[0]
        if existing > 0:
            continue

        conn.execute(
            """INSERT INTO connections
               (source_verse, target_verse, layer, type, subtype,
                strength, confidence, discovered_by, metadata)
               VALUES (?, ?, ?, ?, ?, 0.65, 0.55, 'human', ?)""",
            (f"dss.{scroll_id}", target_verse, layer, typ, scroll_id,
             json.dumps({
                 "note": note[:200],
                 "scholar": "Barker/ETCBC",
                 "dss_scroll": scroll_id
             }))
        )
        count += 1

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    print(f"Sectarian connections: {count}")


def summary():
    conn = init_db()
    texts = conn.execute("SELECT COUNT(*) FROM dss_texts").fetchone()[0]
    sect = conn.execute("SELECT COUNT(*) FROM dss_sectarian").fetchone()[0]
    conns = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE type IN ('dead_sea_scrolls_variant', 'dss_sectarian')"
    ).fetchone()[0]
    variants = conn.execute(
        "SELECT COUNT(*) FROM dss_texts WHERE has_variant = 1"
    ).fetchone()[0]
    conn.close()
    print("\nSummary:")
    print(f"  dss_texts entries:       {texts}")
    print(f"  dss_texts with variants: {variants}")
    print(f"  dss_sectarian entries:   {sect}")
    print(f"  DSS connections:         {conns}")


if __name__ == "__main__":
    print("╔════════════════════════════╗")
    print("║  Dead Sea Scrolls Import   ║")
    print("╚════════════════════════════╝")
    print()
    print("Step 1: Biblical DSS (from JSON)")
    import_biblical()
    print()
    print("Step 2: ETCBC DSS scrolls (from TF)")
    import_etcbc_biblical()
    print()
    print("Step 3: Sectarian texts")
    import_sectarian()
    print()
    print("Step 4: Variant connections")
    create_variant_connections()
    print()
    print("Step 5: Sectarian connections")
    create_sectarian_connections()
    print()
    summary()
