#!/usr/bin/env python3
"""Detect Wikisource LXX rows whose English and Greek columns mismatch.

Method (no Greek knowledge needed, uses the DB as a bilingual bridge):
  For each source row S = (book, chapter, verse) with non-empty EN + GR:
    A = DB verse in the same book whose text_english best matches S.EN
    B = filled DB verse(s) whose stored text_greek == S.GR exactly
         (only when S.GR is unique among all GR cells in the book)
    If A matches strongly (ratio >= 0.90, and clearly better than any
    match to B's own English, margin >= 0.15) and B exists and A not in B:
      S.EN means A-content but S.GR means B-content  ->  row MISMATCHED.

A mismatched row is unsafe for English-similarity gap filling, and any
original-import fill that took Greek from it (i.e. verse B) carries the
wrong verse's Greek.

LIMITATION (documented): corruption created by the original aligner
itself is self-consistent (B got S.GR from S, so A == B) and invisible
to this test. It catches gross transpositions, not off-by-one shifts.
Joshua 8/10 off-by-one shifts were found by direct inspection instead
(see fill script blacklist).

Reads only /tmp/opencode/lxx_greek_cache (no network). Read-only on DB.
Usage: python3 scripts/detect_lxx_mismatch.py [--db=PATH]
"""

import difflib
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from import_lxx_greek import PAGEMAP, CACHE, parse_page, norm_en  # noqa: E402


def ratio(a, b):
    return difflib.SequenceMatcher(None, norm_en(a), norm_en(b),
                                   autojunk=False).ratio()


def detect(db_path=None):
    con = get_db(db_path)
    con.execute("PRAGMA busy_timeout = 120000")
    flags = []
    stats = {}
    for bid, slug in PAGEMAP.items():
        with open(os.path.join(CACHE, slug + ".wikitext"),
                  encoding="utf-8") as f:
            src = parse_page(f.read())
        db = [(r["id"], r["chapter"], r["text_english"],
               r["text_greek"] or "", r["has_greek"])
              for r in con.execute(
                  "SELECT id, chapter, text_english, text_greek, has_greek "
                  "FROM verses WHERE book_id = ? ORDER BY chapter, verse",
                  (bid,))]
        norms = [norm_en(en) for _, _, en, _, _ in db]
        toks = [set(n.split()) for n in norms]
        vid2en = dict((vid, en) for vid, _, en, _, _ in db)
        # Greek -> verse ids holding it (filled rows only)
        gr2vid = defaultdict(list)
        for i, (vid, ch, en, gr, hg) in enumerate(db):
            if hg == 1 and gr:
                gr2vid[gr].append(vid)
        n_rows = n_testable = 0
        for (ch, v), (en, gr) in sorted(src.items()):
            if not en.strip() or not gr.strip():
                continue
            n_rows += 1
            holders = gr2vid.get(gr, [])
            if len(holders) != 1:
                continue  # unused, empty, or duplicated Greek: no verdict
            n_testable += 1
            sn = norm_en(en)
            st = set(sn.split())
            best = (0.0, None)
            for i, (vid, dch, den, dgr, hg) in enumerate(db):
                if abs(dch - ch) > 4:
                    continue
                n = norms[i]
                if not n or len(n) < len(sn) * 0.4 \
                        or len(n) > len(sn) * 2.5:
                    continue
                dt = toks[i]
                union = len(st | dt)
                if union == 0 or len(st & dt) / union < 0.35:
                    continue
                r = difflib.SequenceMatcher(
                    None, sn, n, autojunk=False).ratio()
                if r > best[0]:
                    best = (r, vid)
            r, avid = best
            if avid is None:
                continue
            rB = ratio(en, vid2en.get(holders[0], ""))
            if r >= 0.90 and avid != holders[0] and r - rB >= 0.15:
                flags.append({
                    "src": "%s %s:%s" % (bid, ch, v),
                    "en_matches": avid,
                    "en_ratio": round(r, 4),
                    "greek_holder": holders[0],
                    "src_en": en[:120],
                })
        stats[bid] = (n_rows, n_testable)
    con.close()
    return flags, stats


def main():
    db = None
    for a in sys.argv[1:]:
        if a.startswith("--db="):
            db = a.split("=", 1)[1]
    flags, stats = detect(db)
    print("book-rows testable: "
          + str(sum(s[1] for s in stats.values())) + "/"
          + str(sum(s[0] for s in stats.values())))
    print("MISMATCHED rows: %d" % len(flags))
    for f in flags:
        print("  %(src)s  EN~%(en_matches)s r=%(en_ratio)s  "
              "GR-held-by=%(greek_holder)s" % f)
        print("    SRC-EN: %s" % f["src_en"])


if __name__ == "__main__":
    main()
