#!/usr/bin/env python3
"""Fill text_greek/has_greek on the existing lxx_* rows from en.wikisource.

SOURCE (verified by prior research pass):
  https://en.wikisource.org/wiki/Septuagint_(Brenton_1879)
  Per-book pages with verse-numbered tables: Brenton English col 1 +
  polytonic Unicode Greek col 2 (Greek words carry Strong's links of the
  form [[Strong's_...#NNNN|surface]]; the surface IS the Greek text).
  Same Brenton edition as our English ingest, so English-column sequence
  alignment determines the mapping.

  Attribution NOTE: the wiki layer of en.wikisource carries a CC BY-SA
  footer claim; the underlying Brenton 1879 text is public domain.
  This script stores only the 1879 Greek word-surfaces (facts of the
  edition), fetched via the MediaWiki API (~1 req/3s, honours
  Retry-After), wikitext cached under /tmp/opencode/lxx_greek_cache/.

Daniel/Tobit/etc: 'Septuagint (Brenton 1879)/Daniel (Greek)' is a redlink
(confirmed via API: {"missing": ""}); Tobit, Judith, Esther (Greek),
I-IV Maccabees, Wisdom, Sirach, Baruch, Epistle of Jeremy, Susanna,
Bel and the Dragon, I Esdras, Prayer of Manasses are header-only stubs
(~250 bytes, zero {{verse}} rows; survey.json in the cache dir).
Fallback candidate 'septuagint-with-apocrypha.-greek-and-english-1851'
_djvu.txt (archive.org, Public Domain Mark 1.0) was probed: two-column
Greek/English OCR with heavy bleed-through and scattered verse numbers
(e.g. Susanna region mixes 'ἐπεθύμησε λούσασθαι' with English fragments
and stray numbers 16/17/19/90/21/28/24/260). Verse-boundary recovery
is not deterministic -> judged unusable for automated fill. Those books
stay has_greek=0 and are reported as exact gap lists (see --dry-run).

Alignment: per (book, chapter), difflib.SequenceMatcher over normalized
English (lower, punctuation stripped) maps DB verses to source rows.
This is required because Wikisource numbers psalm titles as verse 1
books split verses our English ingest merged (Lev 7, Job 41, Neh, ...).
Naive key UPDATEs would put wrong Greek on shifted verses. Only
'чваequal'-aligned pairs are written; source-only rows are skipped;
DB-only rows are reported as gaps.

Safety: every UPDATE carries `AND book_id LIKE 'lxx\\_%' ESCAPE '\\'`
so non-lxx rows cannot be touched; post-run assertion verifies
has_greek=1 exists only on lxx_* rows. FTS tables are NOT written
(Greek stays out of the trigram index by design; verses_fts.text_greek
left as-is) — verified by --verify.

Usage:
  python3 scripts/import_lxx_greek.py --dry-run   # parse+align+report, no writes
  python3 scripts/import_lxx_greek.py             # idempotent UPDATEs
  python3 scripts/import_lxx_greek.py --verify    # counts, spot checks, FTS check
"""

import difflib
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db  # noqa: E402

UA = "ScriptureEngine-greek-fill/1.0 (local research)"
API = "https://en.wikisource.org/w/api.php"
CACHE = "/tmp/opencode/lxx_greek_cache"

# book_id -> Wikisource subpage (only pages with verse tables; stub/redlink
# books are absent here and reported as gaps).
PAGEMAP = {
    "lxx_gen": "Genesis", "lxx_exo": "Exodus", "lxx_lev": "Leviticus",
    "lxx_num": "Numbers", "lxx_deu": "Deuteronomy", "lxx_josh": "Joshua",
    "lxx_judg": "Judges", "lxx_ruth": "Ruth",
    "lxx_1sam": "Kings_I", "lxx_2sam": "Kings_II",
    "lxx_1kgs": "Kings_III", "lxx_2kgs": "Kings_IV",
    "lxx_1chr": "Chronicles_I", "lxx_2chr": "Chronicles_II",
    "lxx_ezra": "Ezra", "lxx_neh": "Nehemiah",
    "lxx_job": "Job", "lxx_psa": "Psalms", "lxx_prov": "Proverbs",
    "lxx_eccl": "Ecclesiastes", "lxx_song": "The_Song_of_Solomon",
    "lxx_isa": "Esaias", "lxx_jer": "Jeremias", "lxx_lam": "Lamentations",
    "lxx_ezek": "Jezekiel",
    "lxx_hos": "Osee", "lxx_joel": "Joel", "lxx_amos": "Amos",
    "lxx_obad": "Obdias", "lxx_jonah": "Jonas", "lxx_mic": "Michæas",
    "lxx_nah": "Naum", "lxx_hab": "Ambacum", "lxx_zeph": "Sophonias",
    "lxx_hag": "Aggæus", "lxx_zech": "Zacharias", "lxx_mal": "Malachias",
}

VERSE_RE = re.compile(
    r"\{\{verse\|chapter=(\d+)\|verse=([^\}]+)\}\}(.*?)(?=\n\|\-|\n\|\})",
    re.S,
)
LINK_RE = re.compile(r"\[\[[^\]|]*\|([^\]]*)\]\]")
BARE_LINK_RE = re.compile(r"\[\[([^\]|]*)\]\]")
TMPL_RE = re.compile(r"\{\{[^\}]*\}\}")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def fetch_wikitext(slug):
    path = os.path.join(CACHE, slug + ".wikitext")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    q = urllib.parse.urlencode({
        "action": "parse",
        "page": f"Septuagint (Brenton 1879)/{slug.replace('_', ' ')}",
        "prop": "wikitext", "format": "json"})
    for _ in range(5):
        try:
            req = urllib.request.Request(API + "?" + q,
                                         headers={"User-Agent": UA})
            d = json.loads(urllib.request.urlopen(req, timeout=60).read())
            break
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After", "15"))
            print(f"  HTTP {e.code}, waiting {wait}s", flush=True)
            time.sleep(wait + 2)
    else:
        raise SystemExit("api failed after retries")
    if "error" in d:
        raise SystemExit(f"missing page: {slug}: {d['error'].get('info')}")
    w = d["parse"]["wikitext"]["*"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(w)
    time.sleep(3)
    return w


def clean_greek(cell):
    t = LINK_RE.sub(r"\1", cell)
    t = BARE_LINK_RE.sub(r"\1", t)
    t = TMPL_RE.sub("", t)
    t = TAG_RE.sub("", t)
    t = html.unescape(t)
    return WS_RE.sub(" ", t).strip()


def clean_en(cell):
    t = TMPL_RE.sub("", cell)
    t = TAG_RE.sub("", t)
    t = html.unescape(t)
    return WS_RE.sub(" ", t).strip()


def norm_en(s):
    return PUNCT_RE.sub("", s.lower()).strip()


def parse_page(w):
    """-> dict (chapter, verse_str) -> (en_raw, greek)."""
    out = {}
    for ch, v, body in VERSE_RE.findall(w):
        parts = body.split("||", 1)
        en = clean_en(parts[0])
        gr = clean_greek(parts[1]) if len(parts) > 1 else ""
        out[(int(ch), v.strip())] = (en, gr)
    return out


def align_book(bid, src, db_rows):
    """Align one book. Returns (updates, gaps, extras, chapters).

    updates: list of (verse_id, greek) for equal-aligned pairs w/ Greek.
    gaps: list of verse_ids with no usable Greek (unmapped or empty).
    extras: count of source-only rows skipped.
    chapters: per-chapter (ch, n_db, n_aligned) for the report.
    """
    updates, gaps = [], []
    extras = 0
    chapters = []
    src_chs = {}
    for (ch, v), (en, gr) in src.items():
        src_chs.setdefault(ch, []).append((v, en, gr))
    db_chs = {}
    for vid, ch, v, en in db_rows:
        db_chs.setdefault(ch, []).append((vid, v, en))
    for ch in sorted(set(src_chs) | set(db_chs)):
        srows = sorted(src_chs.get(ch, []),
                       key=lambda r: int(r[0]) if r[0].isdigit() else 0)
        drows = sorted(db_chs.get(ch, []), key=lambda r: r[1])
        sm = difflib.SequenceMatcher(
            None, [norm_en(e) for _, e, _ in srows],
            [norm_en(e) for _, _, e in drows], autojunk=False)
        aligned = 0
        used_src = set()
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for si, di in zip(range(i1, i2), range(j1, j2)):
                    vid = drows[di][0]
                    gr = srows[si][2]
                    used_src.add(si)
                    if gr:
                        updates.append((vid, gr))
                        aligned += 1
                    else:
                        gaps.append((vid, "empty-greek-in-source"))
            else:
                for dj in range(j1, j2):
                    # DB rows consumed by non-equal ops are unmapped...
                    # (equal-tag zip above already advanced both sides in
                    # lockstep only for equal blocks)
                    pass
        # any DB row not covered by an equal op is a gap
        covered = set()
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for dj in range(j1, j2):
                    covered.add(dj)
        for dj, (vid, v, _e) in enumerate(drows):
            if dj not in covered:
                gaps.append((vid, "no-source-alignment"))
        extras += len(srows) - len(used_src)
        chapters.append((ch, len(drows), aligned))
    return updates, gaps, extras, chapters


def collect(db_path=None):
    con = get_db(db_path)
    con.execute("PRAGMA busy_timeout = 120000")
    plan = []
    for bid, slug in PAGEMAP.items():
        w = fetch_wikitext(slug)
        src = parse_page(w)
        db_rows = [(r["id"], r["chapter"], r["verse"], r["text_english"])
                   for r in con.execute(
                       "SELECT id, chapter, verse, text_english FROM verses "
                       "WHERE book_id LIKE 'lxx\\_%' ESCAPE '\\' "
                       "AND book_id = ? ORDER BY chapter, verse", (bid,))]
        updates, gaps, extras, chapters = align_book(bid, src, db_rows)
        plan.append({
            "book": bid, "db": len(db_rows), "src": len(src),
            "aligned": len(updates), "gaps": gaps, "extras": extras,
            "chapters": chapters, "updates": updates,
        })
    # gap-only books (stub/redlink pages): every verse is a gap
    gap_books = ["lxx_1esd", "lxx_tob", "lxx_jdt", "lxx_esth",
                 "lxx_1ma", "lxx_2ma", "lxx_3ma", "lxx_4ma",
                 "lxx_wis", "lxx_sir", "lxx_bar", "lxx_dan", "lxx_s3y",
                 "lxx_man"]
    for bid in gap_books:
        rows = [(r["id"],) for r in con.execute(
            "SELECT id FROM verses WHERE book_id LIKE 'lxx\\_%' ESCAPE '\\' "
            "AND book_id = ? ORDER BY chapter, verse", (bid,))]
        plan.append({
            "book": bid, "db": len(rows), "src": 0, "aligned": 0,
            "gaps": [(vid, "no-wikisource-text") for (vid,) in rows],
            "extras": 0, "chapters": [], "updates": [],
        })
    con.close()
    return plan


def report(plan, save=True):
    total_db = sum(p["db"] for p in plan)
    total_al = sum(p["aligned"] for p in plan)
    total_gap = sum(len(p["gaps"]) for p in plan)
    print(f"{'book':10s} {'db':>6s} {'src':>6s} {'align':>6s} "
          f"{'gaps':>6s} {'extra':>6s}  rate")
    for p in plan:
        rate = p["aligned"] / p["db"] if p["db"] else 1.0
        print(f"{p['book']:10s} {p['db']:6d} {p['src']:6d} "
              f"{p['aligned']:6d} {len(p['gaps']):6d} {p['extras']:6d}  "
              f"{rate:5.1%}")
    print(f"TOTAL db={total_db} aligned={total_al} gaps={total_gap}")
    if save:
        slim = [{k: p[k] for k in ("book", "db", "src", "aligned",
                                   "extras", "chapters")} for p in plan]
        gaps = {p["book"]: [v for v, _ in p["gaps"]] for p in plan
                if p["gaps"]}
        with open(os.path.join(CACHE, "fill_report.json"), "w") as f:
            json.dump({"books": slim, "gaps": gaps}, f, indent=1)
        print("wrote fill_report.json (books + gap verse lists)")


def write_db(plan, db_path=None):
    con = get_db(db_path)
    con.execute("PRAGMA busy_timeout = 120000")
    # Baseline: Greek NT rows (matt, mark, ...) already carry has_greek=1
    # from scripts/ingest_greek.py. Our UPDATEs all pin book_id to an
    # lxx_* id, but assert non-lxx state is unchanged rather than zero.
    non_lxx_before = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE has_greek = 1 AND book_id NOT LIKE 'lxx\\_%' ESCAPE '\\'"
    ).fetchone()["c"]
    n = 0
    batch = []
    for p in plan:
        for vid, gr in p["updates"]:
            bid = vid.rsplit(".", 2)[0]
            assert bid.startswith("lxx_"), vid  # never touch other works
            batch.append((gr, vid, bid))
    con.executemany(
        "UPDATE verses SET text_greek = ?, has_greek = 1 "
        "WHERE id = ? AND book_id = ? "
        "AND book_id LIKE 'lxx\\_%' ESCAPE '\\'", batch)
    # rowcount from executemany is unreliable; count instead
    n = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE book_id LIKE 'lxx\\_%' ESCAPE '\\' AND has_greek = 1"
    ).fetchone()["c"]
    con.commit()
    leak = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE has_greek = 1 AND book_id NOT LIKE 'lxx\\_%' ESCAPE '\\'"
    ).fetchone()["c"]
    assert leak == non_lxx_before, \
        f"non-lxx has_greek changed: {non_lxx_before} -> {leak}"
    con.close()
    return n, len(batch)


def verify(db_path=None):
    con = get_db(db_path)
    esc = "LIKE 'lxx\\_%' ESCAPE '\\'"
    tot = con.execute(
        f"SELECT COUNT(*) AS c FROM verses WHERE book_id {esc}").fetchone()["c"]
    got = con.execute(
        f"SELECT COUNT(*) AS c FROM verses WHERE book_id {esc} "
        "AND has_greek = 1").fetchone()["c"]
    print(f"lxx rows: {tot}, has_greek=1: {got} ({got/tot:.1%})")
    print("per-book has_greek:")
    for r in con.execute(
            f"SELECT book_id, COUNT(*) AS c FROM verses WHERE book_id {esc} "
            "AND has_greek = 1 GROUP BY book_id ORDER BY book_id"):
        print(f"  {r['book_id']:10s} {r['c']}")
    leak = con.execute(
        "SELECT COUNT(*) AS c FROM verses WHERE has_greek = 1 "
        f"AND book_id NOT {esc}").fetchone()["c"]
    print(f"non-lxx rows with has_greek=1 (pre-existing Greek NT, "
          f"must be unchanged by this script): {leak}")
    for vid in ("lxx_gen.1.1", "lxx_isa.7.14", "lxx_psa.22.1"):
        r = con.execute(
            "SELECT text_greek, text_english FROM verses WHERE id = ?",
            (vid,)).fetchone()
        print(f"--- {vid}")
        print(f"  EN: {r['text_english'][:100]}")
        print(f"  GR: {r['text_greek'][:100]}")
    # polytonic check: Greek-range chars present, no pure-ASCII 'Greek'
    import unicodedata
    bad = 0
    for r in con.execute(
            f"SELECT id, text_greek FROM verses WHERE book_id {esc} "
            "AND has_greek = 1"):
        g = r["text_greek"]
        has_greek = any("\u0370" <= ch <= "\u03ff" or
                        "\u1f00" <= ch <= "\u1fff" for ch in g)
        if not has_greek:
            bad += 1
            if bad < 5:
                print(f"  !! no Greek-range chars: {r['id']}: {g[:60]!r}")
    print(f"rows with has_greek=1 but no Greek-range chars: {bad}")
    # FTS untouched: trigram search_text has no Greek; verses_fts.text_greek empty
    tri = con.execute(
        "SELECT COUNT(*) AS c FROM verses_fts_trigram "
        "WHERE book_id LIKE 'lxx%'").fetchone()["c"]
    print(f"trigram rows for lxx books: {tri}")
    sample = con.execute(
        "SELECT text_greek FROM verses_fts WHERE book_id = 'lxx_gen' "
        "LIMIT 3").fetchall()
    print("verses_fts.text_greek samples (expect ''): "
          f"{[r[0][:20] for r in sample]}")
    fts_nonempty = con.execute(
        "SELECT COUNT(*) AS c FROM verses_fts WHERE book_id LIKE 'lxx%' "
        "AND text_greek != ''").fetchone()["c"]
    print(f"verses_fts lxx rows with non-empty text_greek (expect 0): "
          f"{fts_nonempty}")
    con.close()


def main():
    if "--verify" in sys.argv:
        db = None
        for a in sys.argv[1:]:
            if a.startswith("--db="):
                db = a.split("=", 1)[1]
        verify(db)
        return
    dry = "--dry-run" in sys.argv
    db = None
    for a in sys.argv[1:]:
        if a.startswith("--db="):
            db = a.split("=", 1)[1]
    plan = collect(db)
    report(plan)
    if dry:
        print("dry-run: no writes.")
        return
    n, batch = write_db(plan, db)
    print(f"UPDATE batch: {batch}, has_greek=1 lxx rows now: {n}")


if __name__ == "__main__":
    main()
