#!/usr/bin/env python3
"""Order-insensitive second pass over the LXX Greek ingest.

Fills lxx_* rows left empty by scripts/import_lxx_greek.py where the
verse-NUMBER alignment refused (LXX ordering divergences: Proverbs
25-31, Jeremias, Kings III temple chapters, plus scattered splits).

Method: for books that already have partial Greek, match each unfilled
DB row to an UNUSED Wikisource Greek cell by normalized-English
similarity (same Brenton edition, so true mates score ~1.0), same book,
preferentially same chapter (+-3). One source cell fills at most one
verse (greedy best-first); never overwrites existing text_greek; only
touches rows with book_id LIKE 'lxx\\_%'.

Fill gates (ALL required):
  * best in-window (|dch|<=3) ratio >= 0.85, else book-wide >= 0.95
  * ratio >= 0.90
  * length ratio len(src_norm)/len(db_norm) in [0.90, 1.15]
    (rejects partial verse-merge/split pairings)
  * sentence-count equality (same number of [.!?…] segments;
    rejects title-prefix and merged-verse pairings)
  * cross-chapter matches additionally require ratio == 1.0,
    length ratio == 1.0 and margin (best-second) >= 0.10
  * source row not blacklisted (rows proven by direct Greek reading
    to carry a different verse per column -- see BLACKLIST below)
  * neighbour-shift screen: used neighbours of the candidate row must
    not unanimously hold shifted Greek with no same-label support
  * bilingual correspondence: >= 2 shared content-word anchors
    (scripts/lxx_anchors.py) between DB English and candidate Greek,
    or the twin rule (candidate Greek byte-identical to an intact
    filled verse with matching English); any stable-name absence
    (anchor-contradiction) vetoes the fill
  * source Greek contains Greek-range characters

Reads only /tmp/opencode/lxx_greek_cache (no network, no re-crawl).
Every decision (fill or skip with reason) is logged as JSONL.

Usage:
  python3 scripts/fill_lxx_greek_fuzzy.py --dry-run   # no writes
  python3 scripts/fill_lxx_greek_fuzzy.py             # idempotent UPDATEs
"""

import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from import_lxx_greek import (  # noqa: E402
    PAGEMAP, CACHE, parse_page, norm_en, align_book,
)
from lxx_anchors import (  # noqa: E402
    anchor_hits, anchor_contradictions, ANCHOR_NEED,
)

LOG = os.path.join(CACHE, "fuzzy_fill_log.jsonl")
OVERRIDES = os.path.join(os.path.dirname(__file__),
                         "fuzzy_overrides.json")

R_WIN = 0.85
R_BOOK = 0.95
R_FILL = 0.90
LEN_LO, LEN_HI = 0.90, 1.15
X_MARGIN = 0.10
R_TWIN = 0.90  # gap.EN vs filled-twin.EN for the twin rule
R_INTACT = 0.85  # same-label SRC.EN vs DB.EN proving a row intact

# (book_id, chapter, verse_str) source rows proven (by reading the
# Greek) to carry a DIFFERENT verse in each column. Josue 8: the
# English column skips verses while the Greek column is intact, so
# English-similarity picks the wrong Greek (e.g. DB 9:34 == SRC 8:32
# English at r=1.0, but SRC 8:32 Greek is 8:32's, not 9:34's). Josue
# 10: single-verse EN skip at row 15 shifts rows 15..end. Jeremias
# 41:16: EN = servant-release text, GR = Joanan/remnant text.
# DB Josue 8 has no gaps, so the ch-8 blacklist costs zero fills.
BLACKLIST = set(
    [("lxx_josh", 8, str(v)) for v in range(1, 60)]
    + [("lxx_josh", 10, str(v)) for v in range(15, 60)]
    + [("lxx_jer", 41, "16")]
    + [("lxx_ezek", 32, "23")]
    + [("lxx_ezek", 7, "9")]
)


# Books with proven Wikisource EN/GR column shifts (Kings III ch 4/7,
# Jeremias reorder zones): candidate rows there must additionally be
# same-label intact, i.e. the row's English must match OUR English at
# the SAME chapter+verse. (Row-level proof the columns agree there.)
# Proverbs is deliberately excluded: its table is intact, only the
# chapter ORDER differs (verified block swap), so same-label matching
# would wrongly block its correct cross-chapter fills.
WHITELIST_BOOKS = {"lxx_1kgs", "lxx_jer"}


def has_greek_chars(s):
    return any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff"
               for c in s)


def sent_count(s):
    return len([p for p in re.split(r"[.!?…]+", s.strip()) if p.strip()])


def vint(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def collect(db_path=None):
    """Return (decisions, by_book). decisions: list of dicts."""
    con = get_db(db_path)
    con.execute("PRAGMA busy_timeout = 120000")
    decisions = []
    for bid, slug in PAGEMAP.items():
        with open(os.path.join(CACHE, slug + ".wikitext"),
                  encoding="utf-8") as f:
            src = parse_page(f.read())
        db_rows = [(r["id"], r["chapter"], r["verse"], r["text_english"],
                    r["text_greek"] or "", r["has_greek"])
                   for r in con.execute(
                       "SELECT id, chapter, verse, text_english, text_greek,"
                       " has_greek FROM verses "
                       "WHERE book_id LIKE 'lxx\\_%' ESCAPE '\\' "
                       "AND book_id = ? ORDER BY chapter, verse", (bid,))]
        # Unused source cells: recompute the ch-number alignment to find
        # which source rows the first pass consumed.
        plain = [(vid, ch, v, en) for vid, ch, v, en, _, _ in db_rows]
        updates, gaps, extras, _ = align_book(bid, src, plain)
        src_chs = {}
        for (ch, v), (en, gr) in src.items():
            src_chs.setdefault(ch, []).append((v, en, gr))
        db_chs = {}
        for vid, ch, v, en in plain:
            db_chs.setdefault(ch, []).append((vid, v, en))
        used = set()
        for ch in set(src_chs) | set(db_chs):
            srows = sorted(src_chs.get(ch, []),
                           key=lambda r: int(r[0]) if r[0].isdigit()
                           else 0)
            drows = sorted(db_chs.get(ch, []), key=lambda r: r[1])
            sm = difflib.SequenceMatcher(
                None, [norm_en(e) for _, e, _ in srows],
                [norm_en(e) for _, _, e in drows], autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    for si in range(i1, i2):
                        used.add((ch, si))
        pool = []  # (ch, v, src_norm, src_en, greek)
        for ch in src_chs:
            srows = sorted(src_chs[ch],
                           key=lambda r: int(r[0]) if r[0].isdigit()
                           else 0)
            for si, (v, en, gr) in enumerate(srows):
                if (ch, si) in used or not gr.strip():
                    continue
                if not has_greek_chars(gr):
                    continue
                pool.append((ch, v, norm_en(en), en, gr))
        # Twin rule support: filled verses keyed by exact Greek text,
        # plus same-label intactness (SRC.EN(ch,v) ~= DB verse (ch,v)).
        filled_by_gr = {}
        db_en_by_cv = {}
        db_id_by_cv = {}
        for vid2, ch2, v2, en2, gr2, hg2 in db_rows:
            db_en_by_cv[(ch2, str(v2))] = en2
            db_id_by_cv[(ch2, str(v2))] = vid2
            if hg2 == 1 and gr2.strip():
                filled_by_gr.setdefault(gr2, []).append(
                    (vid2, ch2, str(v2), en2))
        src_en_by_cv = {(ch, v): en for (ch, v), (en, gr) in src.items()}

        def row_intact(sch, sv):
            s_en = src_en_by_cv.get((sch, sv), "")
            d_en = db_en_by_cv.get((sch, sv), "")
            if not s_en.strip() or not d_en.strip():
                return False
            return difflib.SequenceMatcher(
                None, norm_en(s_en), norm_en(d_en),
                autojunk=False).ratio() >= R_INTACT

        def chapter_offset(sch):
            """Dominant dbV-srcV offset over this chapter's equal-aligned
            pairs; 0 when no offset dominates (mixed/shift zone)."""
            from collections import Counter as _C
            srows = sorted(src_chs.get(sch, []),
                           key=lambda r: int(r[0]) if r[0].isdigit()
                           else 0)
            drows = sorted(db_chs.get(sch, []), key=lambda r: r[1])
            sm = difflib.SequenceMatcher(
                None, [norm_en(e) for _, e, _ in srows],
                [norm_en(e) for _, _, e in drows], autojunk=False)
            cnt = _C()
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    for si, di in zip(range(i1, i2), range(j1, j2)):
                        a = vint(drows[di][1])
                        b = vint(srows[si][0])
                        if a is not None and b is not None:
                            cnt[a - b] += 1
            tot = sum(cnt.values())
            if tot and cnt.most_common(1)[0][1] >= max(3, 0.6 * tot):
                return cnt.most_common(1)[0][0]
            return 0

        def neighbor_consistent(sch, sv, K):
            """USED neighbours of SRC row (sch, sv) whose Greek is held
            by the DB verse at (sch, sv+dv+K) [consistent] vs elsewhere
            [inconsistent]. Returns (con, inc)."""
            con_n = inc_n = 0
            nv = vint(sv)
            if nv is None:
                return con_n, inc_n
            for dv in (-2, -1, 1, 2):
                key = (sch, str(nv + dv))
                if key not in src:
                    continue
                _, ngr = src[key]
                if not ngr.strip():
                    continue
                holders = filled_by_gr.get(ngr, [])
                if len(holders) != 1:
                    continue
                if holders[0][0] == db_id_by_cv.get((sch, str(nv + dv + K))):
                    con_n += 1
                else:
                    inc_n += 1
            return con_n, inc_n
        # Unfilled DB rows; skip anything already carrying Greek.
        targets = [(vid, ch, v, en) for vid, ch, v, en, gr, hg in db_rows
                   if not gr.strip()]
        by_id = {vid: (ch, en) for vid, ch, v, en in targets}
        # rank[vid] = full ranked list of (ratio, chdist, pool_idx)
        rank = {}
        for vid, ch, v, en in targets:
            n = norm_en(en)
            if not n:
                decisions.append({"verse": vid, "action": "skip",
                                  "reason": "empty-db-english"})
                continue
            lst = []
            for i, (sch, sv, sn, se, sg) in enumerate(pool):
                if not sn:
                    continue
                r = difflib.SequenceMatcher(None, n, sn,
                                            autojunk=False).ratio()
                lst.append((r, abs(sch - ch), i))
            lst.sort(key=lambda t: (-t[0], t[1], t[2]))
            win_best = max([t[0] for t in lst
                            if abs(pool[t[2]][0] - ch) <= 3] + [0.0])
            book_best = max([t[0] for t in lst
                             if abs(pool[t[2]][0] - ch) > 3] + [0.0])
            if win_best < R_WIN and book_best < R_BOOK:
                decisions.append({
                    "verse": vid, "action": "skip",
                    "reason": "no-candidate",
                    "best": round(max(win_best, book_best), 4)})
                continue
            rank[vid] = lst
        # One-to-one greedy: gaps ordered by best ratio first; ties
        # prefer chapter proximity, then verse-number proximity
        # (repetitions like Num 7 land on the nearest twin), then
        # source order. Fallback to the next-best cell when the best
        # is taken (within 0.02: identical formulas share
        # interchangeable cells) or blacklisted.
        def gapkey(vid):
            lst = rank[vid]
            r, cd, pi = lst[0]
            ch = by_id[vid][0]
            sv = pool[pi][1]
            dv = vint(vid.rsplit(".", 1)[1])
            svv = vint(sv)
            vd = abs(dv - svv) if dv is not None and svv is not None \
                else 999
            return (-r, cd, vd, pi)
        taken_src = set()
        for vid in sorted(rank, key=gapkey):
            ch = by_id[vid][0]
            n = norm_en(by_id[vid][1])
            lst = rank[vid]
            best_r = lst[0][0]
            second = lst[1][0] if len(lst) > 1 else 0.0
            margin = best_r - second
            placed, reason, placed_src = None, None, None
            for (r, cd, pi) in lst:
                sch, sv, sn, se, sg = pool[pi]
                in_win = abs(sch - ch) <= 3
                if in_win and r < R_WIN:
                    break  # list is ratio-ordered; nothing better below
                if not in_win and r < R_BOOK:
                    break
                if pi in taken_src:
                    if best_r - r <= 0.02:
                        continue  # try next-best twin cell
                    reason = "source-cell-taken"
                    break
                lr = len(sn) / max(1, len(n))
                if r < R_FILL:
                    reason = "below-ratio-gate"
                    break
                if not (LEN_LO <= lr <= LEN_HI):
                    reason = "length-ratio"
                    break
                if (bid, sch, sv) in BLACKLIST:
                    reason = "blacklisted-source-row"
                    continue  # poisoned cell: try the next pairing
                if bid in WHITELIST_BOOKS and not row_intact(sch, sv):
                    reason = "row-not-intact"
                    continue  # shift-zone book: need same-label proof
                chap_k = chapter_offset(sch)
                con_k, inc_k = neighbor_consistent(sch, sv, chap_k)
                con_0, _ = neighbor_consistent(sch, sv, 0)
                if inc_k > 0 and con_k == 0 and con_0 < 2:
                    # Used neighbours hold shifted Greek while (almost)
                    # none hold same-label Greek: this row sits in a
                    # column-shift zone (cf. Jos 8, 3 Kgs 7, Ezek 32).
                    reason = "neighbor-shift"
                    continue
                if not in_win and not (
                        r == 1.0 and lr == 1.0 and margin >= X_MARGIN):
                    reason = "cross-chapter-not-exact"
                    break
                if sent_count(by_id[vid][1]) != sent_count(se) \
                        and r < 1.0:
                    # Punctuation-only differences (r == 1.0 on the
                    # normalized text) are fine; real clause-count
                    # differences mean merged/split verses.
                    reason = "sentence-count"
                    break
                # Bilingual correspondence: anchor test (>= ANCHOR_NEED
                # shared content words) or twin rule (identical Greek
                # already held by an intact filled verse with matching
                # English). Anything else needs human Greek reading.
                hits = anchor_hits(by_id[vid][1], sg)
                contra = anchor_contradictions(by_id[vid][1], sg)
                if contra:
                    reason = "anchor-contradiction"
                    decisions.append({
                        "verse": vid, "action": "skip", "reason": reason,
                        "ratio": round(r, 4), "len_ratio": round(lr, 4),
                        "scope": "in-window" if in_win else "book-wide",
                        "src": "%s %d:%s" % (bid, sch, sv),
                        "anchors": sorted(hits),
                        "contradictions": sorted(contra),
                        "src_en": se[:200], "db_en": by_id[vid][1][:200],
                        "greek": sg})
                    placed = ("reviewed",)
                    break
                twin_ok = False
                if len(hits) < ANCHOR_NEED:
                    for fvid, fch, fv, fen in filled_by_gr.get(sg, []):
                        if row_intact(fch, fv) and \
                           difflib.SequenceMatcher(
                               None, n, norm_en(fen),
                               autojunk=False).ratio() >= R_TWIN:
                            twin_ok = True
                            break
                if len(hits) < ANCHOR_NEED and not twin_ok:
                    decisions.append({
                        "verse": vid, "action": "skip",
                        "reason": "anchor-review",
                        "ratio": round(r, 4), "len_ratio": round(lr, 4),
                        "scope": "in-window" if in_win else "book-wide",
                        "src": "%s %d:%s" % (bid, sch, sv),
                        "anchors": sorted(hits),
                        "src_en": se[:200], "db_en": by_id[vid][1][:200],
                        "greek": sg})
                    placed = ("reviewed",)
                    break
                placed = (r, lr, margin, sch, sv, se, sg,
                          "in-window" if in_win else "book-wide",
                          sorted(hits), twin_ok)
                placed_src = pi
                break
            if placed is None:
                decisions.append({
                    "verse": vid, "action": "skip",
                    "reason": reason or "source-cell-taken",
                    "ratio": round(best_r, 4)})
                continue
            if placed == ("reviewed",):
                continue
            taken_src.add(placed_src)
            r, lr, margin, sch, sv, se, sg, scope, hits, twin_ok = placed
            chap_k = chapter_offset(sch)
            con_k, inc_k = neighbor_consistent(sch, sv, chap_k)
            con_0, _ = neighbor_consistent(sch, sv, 0)
            decisions.append({
                "verse": vid, "action": "fill",
                "ratio": round(r, 4), "len_ratio": round(lr, 4),
                "margin": round(margin, 4), "scope": scope,
                "src": "%s %d:%s" % (bid, sch, sv),
                "src_en": se[:200], "db_en": by_id[vid][1][:200],
                "anchors": hits, "twin": twin_ok,
                "neigh": [con_k, inc_k, chap_k, con_0],
                "greek": sg})
    apply_overrides(decisions, db_path)
    con.close()
    return decisions


def apply_overrides(decisions, db_path=None):
    """Human-verified fills from fuzzy_overrides.json (each Greek cell
    read-verified verse-correct; see reasons in the file). Applied only
    when the verse is still unfilled, the cell is still free, and the
    cell is not blacklisted. Logged as fill/how=override."""
    if not os.path.exists(OVERRIDES):
        return
    with open(OVERRIDES, encoding="utf-8") as f:
        overrides = json.load(f)
    by_verse = {d["verse"]: d for d in decisions}
    taken = {d["src"] for d in decisions
             if d["action"] == "fill" and "src" in d}
    con = get_db(db_path)
    for o in overrides:
        vid, src = o["verse"], o["src"]
        bid = vid.rsplit(".", 2)[0]
        assert bid.startswith("lxx_"), vid
        sch = int(src.split()[1].split(":")[0])
        sv = src.split()[1].split(":")[1]
        if (bid, sch, sv) in BLACKLIST:
            by_verse[vid] = {"verse": vid, "action": "skip",
                             "reason": "override-blacklisted", "src": src}
            continue
        cur = by_verse.get(vid)
        if cur is None:
            continue  # not a gap verse at all; nothing to do
        if cur["action"] == "fill":
            continue  # automatic fill already took it
        if src in taken:
            by_verse[vid] = {"verse": vid, "action": "skip",
                             "reason": "override-cell-taken", "src": src}
            continue
        row = con.execute(
            "SELECT text_greek FROM verses WHERE id = ? "
            "AND book_id LIKE 'lxx\\_%' ESCAPE '\\'", (vid,)).fetchone()
        if row is None or (row["text_greek"] or "").strip():
            by_verse[vid] = {"verse": vid, "action": "skip",
                             "reason": "override-no-longer-empty",
                             "src": src}
            continue
        with open(os.path.join(
                CACHE, _slug_for(bid) + ".wikitext"),
                encoding="utf-8") as f:
            srcmap = parse_page(f.read())
        en, gr = srcmap.get((sch, sv), ("", ""))
        if not gr.strip() or not has_greek_chars(gr):
            by_verse[vid] = {"verse": vid, "action": "skip",
                             "reason": "override-cell-empty",
                             "src": src}
            continue
        taken.add(src)
        by_verse[vid] = {"verse": vid, "action": "fill", "how": "override",
                         "ratio": o.get("ratio"), "scope": "override",
                         "src": src, "override_reason": o.get("reason"),
                         "greek": gr}
    decisions[:] = [by_verse[v] for v in
                    [d["verse"] for d in decisions]]
    con.close()


def _slug_for(bid):
    return PAGEMAP[bid]


def write_db(decisions, db_path=None):
    con = get_db(db_path)
    con.execute("PRAGMA busy_timeout = 120000")
    non_lxx_before = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE has_greek = 1 AND book_id NOT LIKE 'lxx\\_%' ESCAPE '\\'"
    ).fetchone()["c"]
    batch = []
    for d in decisions:
        if d["action"] != "fill":
            continue
        vid = d["verse"]
        bid = vid.rsplit(".", 2)[0]
        assert bid.startswith("lxx_"), vid
        batch.append((d["greek"], vid, bid))
    # Never overwrite: only rows whose text_greek is empty/NULL.
    con.executemany(
        "UPDATE verses SET text_greek = ?, has_greek = 1 "
        "WHERE id = ? AND book_id = ? "
        "AND book_id LIKE 'lxx\\_%' ESCAPE '\\' "
        "AND (text_greek IS NULL OR text_greek = '')", batch)
    con.commit()
    n = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE book_id LIKE 'lxx\\_%' ESCAPE '\\' AND has_greek = 1"
    ).fetchone()["c"]
    leak = con.execute(
        "SELECT COUNT(*) AS c FROM verses "
        "WHERE has_greek = 1 AND book_id NOT LIKE 'lxx\\_%' ESCAPE '\\'"
    ).fetchone()["c"]
    assert leak == non_lxx_before, \
        "non-lxx has_greek changed: %s -> %s" % (non_lxx_before, leak)
    # Confirm no overwrite happened: every filled verse was empty before.
    con.close()
    return n, len(batch)


def main():
    dry = "--dry-run" in sys.argv
    db = None
    for a in sys.argv[1:]:
        if a.startswith("--db="):
            db = a.split("=", 1)[1]
    decisions = collect(db)
    fills = [d for d in decisions if d["action"] == "fill"]
    skips = [d for d in decisions if d["action"] != "fill"]
    from collections import Counter
    per_book = Counter(d["verse"].rsplit(".", 2)[0] for d in fills)
    skip_reasons = Counter(d.get("reason") for d in skips)
    print("FILL candidates: %d  skips: %d" % (len(fills), len(skips)))
    print("per-book fills:")
    for b in sorted(per_book):
        print("  %s %d" % (b, per_book[b]))
    print("skip reasons: %s" % dict(skip_reasons))
    with open(LOG, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print("wrote %s (%d decisions)" % (LOG, len(decisions)))
    if dry:
        print("dry-run: no writes.")
        return
    n, batch = write_db(decisions, db)
    print("UPDATE batch: %d, has_greek=1 lxx rows now: %d" % (batch, n))


if __name__ == "__main__":
    main()
