#!/usr/bin/env python3
"""Import Brenton's 1851 English Septuagint into the scripture DB as work 'lxx'.

Source: research/scholarship-private/lxx/brenton-lxx-1851.txt (public domain,
English only, no Greek). Format notes (verified against the file):
  - Book headers are standalone lines with 1-3 leading spaces, e.g. ' Genesis',
    '  Leviticus', '  Kings I (I Samuel)'. Page running heads look identical
    but have NO leading space, so the indent is load-bearing.
  - Chapters: ' Chapter N' lines; Psalms use ' Psalm N' lines (1-151).
    A ' Psalm 152' header is really the Prayer of Manasses (verses '1:1...').
  - Verses: first marker in a chapter is 'C:V' (e.g. '1:1 ...'); subsequent
    verses in the same chapter are bare numbers ('...water. 2 But...'), sometimes
    mid-line, sometimes at line starts, occasionally with the space dropped
    ('54And', '13They', '24All'). Brenton spells out prose numbers, so every
    digit run in the body is a verse marker — except '(5:16A)' (a gloss inside
    Kings II 5:16), which the parser explicitly excludes.
  - Noise: blank lines, page-number-only lines, ORDER OF BOOKS front matter
    (skipped: parsing starts at the first book header), 'Alleluia.' psalm
    epigraphs, psalm titles, the Sirach prologue (unversified -> skipped).
  - Known source anomalies: Ps 151 skips v4 then prints two v5s; duplicate
    verse numbers are merged into one row and logged.

ID scheme: work 'lxx'; books 'lxx_gen', 'lxx_psa', ... (namespaced per work,
since book id is a global PK already used by 'ot'/'apoc' rows); verse ids
'lxx_gen.1.1' via the standard {book}.{chapter}.{verse} pattern (cf. DSS
'dss.1QS.72' namespacing precedent). All writes are INSERT OR IGNORE /
DELETE+re-INSERT into FTS only — existing rows are never touched.

FTS: there are NO triggers on verses, so new rows are mirrored the same way
scripts/import_jsh.py does (verses_fts porter table) plus the live trigram
index format from scripts/build_fts_index.py ('english: ...' search_text).

Usage:
  python3 scripts/import_lxx_brenton.py --dry-run   # parse + report, no writes
  python3 scripts/import_lxx_brenton.py             # write to live DB
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

SOURCE = os.path.join(
    os.path.dirname(__file__), "..", "research", "scholarship-private",
    "lxx", "brenton-lxx-1851.txt",
)

# (Brenton header stripped, book_id, display title) in Brenton's order.
BOOKS = [
    ("Genesis", "lxx_gen", "Genesis"),
    ("Exodus", "lxx_exo", "Exodus"),
    ("Leviticus", "lxx_lev", "Leviticus"),
    ("Numbers", "lxx_num", "Numbers"),
    ("Deuteronomy", "lxx_deu", "Deuteronomy"),
    ("Joshua", "lxx_josh", "Joshua"),
    ("Judges", "lxx_judg", "Judges"),
    ("Ruth", "lxx_ruth", "Ruth"),
    ("Kings I (I Samuel)", "lxx_1sam", "1 Samuel (Kings I)"),
    ("Kings II (II Samuel)", "lxx_2sam", "2 Samuel (Kings II)"),
    ("Kings III (I Kings)", "lxx_1kgs", "1 Kings (Kings III)"),
    ("Kings IV (II Kings)", "lxx_2kgs", "2 Kings (Kings IV)"),
    ("Chronicles I", "lxx_1chr", "1 Chronicles"),
    ("Chronicles II", "lxx_2chr", "2 Chronicles"),
    ("Ezra", "lxx_ezra", "Ezra"),
    ("I Esdras", "lxx_1esd", "1 Esdras"),
    ("Nehemiah", "lxx_neh", "Nehemiah"),
    ("Tobit", "lxx_tob", "Tobit"),
    ("Judith", "lxx_jdt", "Judith"),
    ("Esther", "lxx_esth", "Esther"),
    ("I Maccabees", "lxx_1ma", "1 Maccabees"),
    ("II Maccabees", "lxx_2ma", "2 Maccabees"),
    ("III Maccabees", "lxx_3ma", "3 Maccabees"),
    ("IV Maccabees", "lxx_4ma", "4 Maccabees"),
    ("Job", "lxx_job", "Job"),
    ("Psalms", "lxx_psa", "Psalms"),
    ("Proverbs", "lxx_prov", "Proverbs"),
    ("Ecclesiastes", "lxx_eccl", "Ecclesiastes"),
    ("Song of Songs (Song of Solomon)", "lxx_song", "Song of Songs"),
    ("Wisdom", "lxx_wis", "Wisdom of Solomon"),
    ("Sirach (Ecclesiasticus)", "lxx_sir", "Sirach (Ecclesiasticus)"),
    ("Esaias (Isaiah)", "lxx_isa", "Isaiah (Esaias)"),
    ("Jeremias (Jeremiah)", "lxx_jer", "Jeremiah (Jeremias)"),
    ("Lamentations", "lxx_lam", "Lamentations"),
    ("Baruch", "lxx_bar", "Baruch"),
    ("Jezekiel (Ezekiel)", "lxx_ezek", "Ezekiel (Jezekiel)"),
    ("Daniel", "lxx_dan", "Daniel"),
    # Titled insertion inside Daniel 3 (own 1-67 numbering); mirrors the
    # existing apoc 's3y' split. Extracted via the in-text sub-header.
    ("Song of the Three Children", "lxx_s3y", "Song of the Three Children"),
    ("Osee (Hosea)", "lxx_hos", "Hosea (Osee)"),
    ("Joel", "lxx_joel", "Joel"),
    ("Amos", "lxx_amos", "Amos"),
    ("Obdias (Obadiah)", "lxx_obad", "Obadiah (Obdias)"),
    ("Jonas (Jonah)", "lxx_jonah", "Jonah (Jonas)"),
    ("Michaeas (Micah)", "lxx_mic", "Micah (Michaeas)"),
    ("Naum (Nahum)", "lxx_nah", "Nahum (Naum)"),
    ("Ambacum (Habakkuk)", "lxx_hab", "Habakkuk (Ambacum)"),
    ("Sophonias (Zephaniah)", "lxx_zeph", "Zephaniah (Sophonias)"),
    ("Aggaeus (Haggai)", "lxx_hag", "Haggai (Aggaeus)"),
    ("Zacharias (Zechariah)", "lxx_zech", "Zechariah (Zacharias)"),
    ("Malachias (Malachi)", "lxx_mal", "Malachi (Malachias)"),
    # Not a real header: filed under ' Psalm 152' in Brenton; handled specially.
    ("Prayer of Manasses", "lxx_man", "Prayer of Manasses"),
]

CHAP_RE = re.compile(r"^\s*(Chapter|Psalm)\s+(\d+)\s*$")
PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
# Verse marker on joined chapter text:
#   'C:V' form must not be preceded by a digit/'('/'[' and not followed by
#   digit/colon/letter (excludes the '(5:16A)' gloss); bare 'N' form must
#   follow start-of-text or sentence punctuation (+ optional space), and be
#   followed by whitespace or (missing-space typo) an uppercase letter.
MARKER_RE = re.compile(
    r"(?:(?<![\d(\[])(?P<c>\d{1,3}):(?P<v1>\d{1,3})(?![\d:A-Za-z]))"
    r"|(?:(?<=^)|(?<=[.,;:?!\-—–\)\]\w\"'\"'’‘])|(?<=\s--)|(?<=\d ))\s*(?P<v2>\d{1,3})(?=\s+|\s*$|(?=[A-Z]))"
)


def parse_source(path):
    """Parse the Brenton text. Returns (verses, anomalies).

    verses: list of (book_id, chapter, verse, text).
    anomalies: list of strings describing gaps/dupes/skips.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    # NOTE: splitlines() also splits on \x0c (page-break running heads like
    # '\x0cGenesis'); those remnants have no leading space, which is exactly
    # what distinguishes them from indented real book headers.
    lines = raw.splitlines()

    header_to_book = {h: (bid, title) for h, bid, title in BOOKS}
    # Map exact header line (with its indent) -> book; verify uniqueness below.
    verses = []
    anomalies = []

    cur_bid = None
    cur_ch = None
    chap_buf = []  # accumulated text lines for the current chapter
    skipped_buf = []  # unversified pre-chapter text (prologue, epigraphs)
    skipped_line = None
    song_mode = False  # inside the Song of the Three Children (Dan 3)
    song_return_bid = None  # work book to restore when song mode ends

    def flush_chapter():
        nonlocal skipped_line
        if skipped_buf:
            total = len(" ".join(skipped_buf))
            if total > 200:
                anomalies.append(
                    f"skipped {total} chars unversified text "
                    f"(line ~{skipped_line}): {skipped_buf[0][:90]!r}..."
                )
            skipped_buf.clear()
            skipped_line = None
        if cur_bid is None or cur_ch is None:
            if chap_buf:
                anomalies.append(
                    f"orphan text with no chapter "
                    f"({len(' '.join(chap_buf))} chars): "
                    f"{' '.join(chap_buf)[:100]!r}"
                )
            chap_buf.clear()
            return
        text = " ".join(t for t in chap_buf)
        chap_buf.clear()
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            anomalies.append(f"{cur_bid} ch{cur_ch}: empty chapter")
            return
        # Parenthesized cross-refs (e.g. '(5:16A)' gloss in Kings II 5:16)
        # are never verse markers.
        text = re.sub(r"\(\d{1,3}:\d{1,3}[A-Za-z]?\)", "(REF)", text)
        # Combined verses ('2, 3 And should...' in 4 Macc 5:1-3): split the
        # numbers so each is an (empty-combinable) marker like Exod 40's.
        text = re.sub(r"(?<!\d)(\d{1,3}), (\d{1,3})(?= [A-Za-z])", r"\1 \2", text)
        split_chapter(cur_bid, cur_ch, text, verses, anomalies)

    # Locate first book header; everything before is front matter.
    first = None
    for i, l in enumerate(lines):
        if re.match(r"^ {1,3}[A-Za-z]", l) and l.strip() in header_to_book:
            first = i
            break
    if first is None:
        raise SystemExit("no book header found — source format changed?")
    for i, l in enumerate(lines[first:], start=first):
        s = l.strip()
        if not s or PAGE_NUM_RE.match(l):
            continue
        if s == "Song of the Three Children":
            # Titled insertion inside Daniel 3 with its own 1-67 numbering:
            # file under lxx_s3y (mirrors apoc 's3y'). Must precede the
            # header_to_book check: the line is bare (no indent), which
            # otherwise reads as a page running head. The narrative resumes
            # afterwards with a backward number (24), handled in
            # split_chapter; a real Chapter header ends song mode via the
            # normal path below.
            flush_chapter()
            if (cur_bid, cur_ch) != ("lxx_dan", 3):
                anomalies.append(
                    f"song header outside Dan 3 (at {cur_bid} ch{cur_ch})"
                )
            cur_bid, cur_ch = "lxx_s3y", 1
            song_return_bid = "lxx_dan"
            song_mode = True
            continue
        if s in header_to_book:
            if re.match(r"^ {1,3}[A-Za-z]", l):
                flush_chapter()
                song_mode = False
                cur_bid, _ = header_to_book[s]
                cur_ch = None
            # else: page running head (no indent) glued into the flow — skip.
            continue
        m = CHAP_RE.match(l)
        if m:
            flush_chapter()
            if song_mode:
                # Song filed under lxx_s3y; the new chapter belongs to the
                # enclosing book (Daniel).
                cur_bid = song_return_bid
            song_mode = False
            kind, n = m.group(1), int(m.group(2))
            if kind == "Psalm" and n == 152:
                # Brenton mislabels the Prayer of Manasses as 'Psalm 152'.
                cur_bid = "lxx_man"
                cur_ch = 1
            elif kind == "Psalm":
                cur_ch = n
            else:
                cur_ch = n
            continue
        if cur_bid is not None and cur_ch is not None:
            chap_buf.append(s)
        else:
            # Pre-chapter material (psalm epigraphs like 'Alleluia.', psalm
            # titles, Sirach prologue): skip, report if substantial.
            if skipped_line is None:
                skipped_line = i + 1
            skipped_buf.append(s)
    flush_chapter()
    # Merge reused numbers (LXX scrambles: 1 Kgs 6 vessels run, Prov/Sir/Jer
    # doublets, Deut 24 order). First occurrence keeps the key; later text is
    # appended so nothing is lost. Merges are logged, not silent.
    merged_rows = []
    seen = {}
    for (b, c, v, t) in verses:
        if (b, c, v) in seen:
            i = seen[(b, c, v)]
            ob, oc, ov, ot = merged_rows[i]
            merged_rows[i] = (ob, oc, ov, ot + " " + t)
            anomalies.append(
                f"{b} ch{c}: reused v{v} text merged "
                f"(+{len(t)} chars onto {len(ot)})"
            )
        else:
            seen[(b, c, v)] = len(merged_rows)
            merged_rows.append((b, c, v, t))
    return merged_rows, anomalies


def split_chapter(bid, ch, text, verses, anomalies):
    """Split joined chapter text into verses using sequential validation."""
    matches = list(MARKER_RE.finditer(text))
    # First marker must be verse 1 ('C:1' or bare '1').
    if not matches:
        anomalies.append(f"{bid} ch{ch}: no verse markers found")
        return
    expected = 1
    cur_v = None
    cur_start = None
    out_bid, out_ch = bid, ch  # song tail-switch may retarget these

    def close_verse(end):
        t = text[cur_start:end].strip()
        t = re.sub(r"\s+", " ", t)
        if t:
            verses.append((out_bid, out_ch, cur_v, t))
        else:
            # Adjacent numbers ('7 8 9 And...', '13:1 2 And...'): Brenton
            # leaves the verse text empty (combined verses).
            anomalies.append(f"{out_bid} ch{out_ch}: empty v{cur_v} skipped")

    for m in matches:
        c = m.group("c")
        v = int(m.group("v1") if m.group("v1") is not None else m.group("v2"))
        if c is not None and int(c) != ch and cur_v is not None:
            continue  # cross-reference-looking; keep as text
        if c is not None and int(c) != ch and cur_v is None:
            # First marker carries the wrong chapter prefix (Brenton typo,
            # e.g. 4 Macc 5 opens '1:1'): trust the verse part, log it.
            anomalies.append(
                f"{out_bid} ch{out_ch}: first marker C:V prefix {c} != ch; "
                f"accepted as v{v}"
            )
        if bid == "lxx_s3y" and (out_bid, out_ch) == ("lxx_s3y", 1):
            # End of the Song: the Dan 3 narrative resumes with a number far
            # below the song's run (67 -> 24). A big backward jump retargets
            # this and all following markers to Dan 3.
            if cur_v is not None and v < expected - 5:
                close_verse(m.start())
                anomalies.append(
                    f"song ends at v{cur_v}; Dan 3 narrative resumes v{v}"
                )
                out_bid, out_ch = "lxx_dan", 3
                cur_v = None
                expected = 1
        if cur_v is None:
            if v != 1:
                anomalies.append(
                    f"{out_bid} ch{out_ch}: first marker is v{v}, expected v1"
                )
                # Still accept it as the starting verse (source-faithful).
            cur_v = v
            cur_start = m.end()
            expected = v + 1
            continue
        if v == cur_v:
            # Duplicate number (e.g. Ps 151's two v5s): keep the digits in
            # the running verse text (source-faithful), log it.
            anomalies.append(f"{out_bid} ch{out_ch}: duplicate v{v} merged")
            continue
        if v != expected:
            anomalies.append(
                f"{out_bid} ch{out_ch}: gap/skip (had v{cur_v}, found v{v})"
            )
        close_verse(m.start())
        cur_v = v
        cur_start = m.end()
        expected = v + 1
    if cur_v is not None:
        close_verse(len(text))
    return expected - 1


def write_db(verses, db_path=None):
    """INSERT OR IGNORE everything. Returns exact insert counts."""
    conn = get_db(db_path) if db_path else get_db()
    # A dev API server (uvicorn) can hold the DB; wait patiently, never kill.
    conn.execute("PRAGMA busy_timeout = 120000")
    n_work = conn.execute(
        "INSERT OR IGNORE INTO works (id, title, position) "
        "VALUES ('lxx', 'Septuagint (Brenton 1851)', 9)"
    ).rowcount
    n_book = 0
    for pos, (_h, bid, title) in enumerate(BOOKS, start=1):
        n_book += conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) "
            "VALUES (?, 'lxx', ?, ?)",
            (bid, title, pos),
        ).rowcount
    n_verse = n_tr = n_fts = n_tri = 0
    # Idempotency: our verse_ids are brand-new (lxx_*), so per-row DELETEs
    # would each full-scan the FTS tables (verse_id is UNINDEXED). NOTE: LIKE
    # does not work on FTS5 tables (silently matches nothing); use =
    # on book_id. Fresh runs skip deletes entirely (checked on verses, a
    # real table); reruns clear per-book (102 indexed-equality scans).
    fresh = conn.execute(
        "SELECT COUNT(*) AS c FROM verses WHERE book_id LIKE 'lxx%'"
    ).fetchone()["c"] == 0
    if not fresh:
        book_ids = sorted({b for b, _c, _v, _t in verses})
        for tbl in ("verses_fts", "verses_fts_trigram"):
            for b in book_ids:
                conn.execute(f"DELETE FROM {tbl} WHERE book_id = ?", (b,))
    for i, (bid, ch, v, t) in enumerate(verses):
        vid = f"{bid}.{ch}.{v}"
        n_verse += conn.execute(
            "INSERT OR IGNORE INTO verses "
            "(id, book_id, chapter, verse, text_english) "
            "VALUES (?, ?, ?, ?, ?)",
            (vid, bid, ch, v, t),
        ).rowcount
        n_tr += conn.execute(
            "INSERT OR IGNORE INTO text_resources "
            "(verse_id, version, text, language) VALUES (?, 'LXX', ?, 'eng')",
            (vid, t),
        ).rowcount
        # No triggers on verses: mirror into FTS like import_jsh.py.
        n_fts += conn.execute(
            "INSERT INTO verses_fts "
            "(verse_id, book_id, text_english, text_hebrew, text_greek) "
            "VALUES (?, ?, ?, '', '')",
            (vid, bid, t),
        ).rowcount
        n_tri += conn.execute(
            "INSERT INTO verses_fts_trigram (verse_id, book_id, search_text) "
            "VALUES (?, ?, ?)",
            (vid, bid, f"english: {t}"),
        ).rowcount
        if (i + 1) % 5000 == 0:
            print(f"  ...{i + 1}/{len(verses)}", flush=True)
    conn.commit()
    conn.close()
    return n_work, n_book, n_verse, n_tr, n_fts, n_tri


def report(verses, anomalies):
    from collections import Counter, OrderedDict
    per_book = Counter(b for b, _c, _v, _t in verses)
    print(f"TOTAL verses parsed: {len(verses)}")
    print(f"{'book':10s} {'verses':>7s}")
    for _h, bid, _t in BOOKS:
        if per_book.get(bid):
            print(f"{bid:10s} {per_book[bid]:7d}")
    n_chapters = len({(b, c) for b, c, _v, _t in verses})
    print(f"chapters (book,ch) with verses: {n_chapters}")
    print(f"anomalies: {len(anomalies)}")
    for a in anomalies:
        print(f"  ! {a}")


def main():
    dry = "--dry-run" in sys.argv
    db_path = None
    for a in sys.argv[1:]:
        if a.startswith("--db="):
            db_path = a.split("=", 1)[1]
    verses, anomalies = parse_source(SOURCE)
    if dry:
        report(verses, anomalies)
        return
    report(verses, anomalies)
    n_work, n_book, n_verse, n_tr, n_fts, n_tri = write_db(verses, db_path)
    print("INSERT counts (rowcount; 0 = already present):")
    print(f"  works: {n_work}, books: {n_book}, verses: {n_verse}, "
          f"text_resources: {n_tr}, verses_fts: {n_fts}, trigram: {n_tri}")


if __name__ == "__main__":
    main()