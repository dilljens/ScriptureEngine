#!/usr/bin/env python3
"""BoM 1830-vs-modern sync + Son-of insertions examiner.

Sync = align any modern verse to its 1830 first-edition wording via fuzzy
word-window search over the Wikisource 1830 text (which uses 1830 chaptering,
so direct chapter lookup does not work).

Usage:
  python3 tools/bom1830.py '{"action": "status"}'
  python3 tools/bom1830.py '{"action": "lookup", "verse": "1ne.11.18"}'
  python3 tools/bom1830.py '{"action": "sonof"}'
  python3 tools/bom1830.py '{"action": "sync"}'   # rebuild _sync.json + verify anchors

Actions:
  status  — 1830 corpus inventory (sections, books mapped, chars)
  lookup  — align one modern verse to 1830, show both wordings + diff flag
  sonof   — all modern BoM "Son of God" verses, each aligned + classified:
             SAME | INSERTION_CANDIDATE | UNCERTAIN
  sync    — write data/bom_1830/_sync.json (inventory + anchor verification)
"""

import json
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = os.path.join(os.path.dirname(__file__), "..")
TEXT1830 = os.path.join(BASE, "data", "bom_1830", "1830_wikisource_text.txt")
SYNCFILE = os.path.join(BASE, "data", "bom_1830", "_sync.json")

BOM_BOOKS = ["1ne", "2ne", "jacob", "enos", "jarom", "omni", "wom",
             "mosiah", "alma", "hel", "3ne", "4ne", "morm", "ether", "moro"]

# Fragment of the 1830 Wikisource title identifying each modern book.
FRAG = {
    "1ne": "1 Nephi", "2ne": "2 Nephi", "jacob": "Jacob", "enos": "Enos",
    "jarom": "Jarom", "omni": "Omni", "wom": "Words of Mormon",
    "mosiah": "Mosiah", "alma": "Alma", "hel": "Helaman",
    "3ne": "3 Nephi", "4ne": "4 Nephi", "morm": "Mormon",
    "ether": "Ether", "moro": "Moroni",
}

# Anchor verses known to carry (or not carry) the post-1830 "Son of" wording.
# Used by sync to verify the aligner actually finds the right 1830 passage.
ANCHORS = ["1ne.11.18", "1ne.11.21", "1ne.11.32", "1ne.13.40", "1ne.11.27"]


def _clean(raw):
    """Drop Wikisource nav/TOC/page-number junk, keep readable prose."""
    lines = []
    for ln in raw.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if "←" in s or "→" in s:
            continue
        if re.search(r"\.{4,}", s):  # TOC dot leaders
            continue
        if re.match(r"^(Chapter|CHAPTER)\s+[IVXLC]+\s*$", s):
            continue
        if re.match(r"^\d+\s*$", s):  # bare page numbers
            continue
        lines.append(s)
    t = " ".join(lines)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _norm(s):
    return re.sub(r"[^a-z ]", "", s.lower())


def load_1830():
    """Parse 1830 file -> {title: cleaned_text}. Raises with hint if missing."""
    if not os.path.exists(TEXT1830):
        return None, f"Missing {TEXT1830} — run scripts/download_bom1830.py first"
    txt = open(TEXT1830, encoding="utf-8", errors="replace").read()
    parts = re.split(r"\n===== (.*?) =====\n", txt)
    secs = {}
    for i in range(1, len(parts) - 1, 2):
        secs[parts[i]] = _clean(parts[i + 1])
    return secs, None


def book_texts(secs):
    """Group 1830 sections by modern book_id -> concatenated cleaned text."""
    out = {}
    for bid in BOM_BOOKS:
        frag = FRAG[bid]
        # NOTE: every title starts with "Book of Mormon (1830)/" so match
        # only against the part after the prefix (else "Mormon" hits all).
        hits = [t for t in secs
                if frag in t.split("Book of Mormon (1830)/", 1)[-1]]
        # Words-of-Mormon has no 1830 book page; fall back to Omni/Mosiah seam
        if not hits and bid == "wom":
            tails = [t.split("Book of Mormon (1830)/", 1)[-1] for t in secs]
            hits = [t for t in secs
                    if "Omni" in t.split("Book of Mormon (1830)/", 1)[-1]
                    or "Mosiah" in t.split("Book of Mormon (1830)/", 1)[-1]]
        out[bid] = " ".join(secs[t] for t in sorted(hits))
    return out


from collections import Counter

STOP = set("""thou thee thy thine ye you your unto upon hath doth saith saith
behold yea wherefore therefore because which that with from they them their
there were when then than come came pass lord god christ jesus son father
spirit people nephi laman lamanites lord's shall will would should could
also even ever never always among every take took taken give given know
knew known speak spake spoken word words thing things great mighty power
hand hands day days land lands city cities king reign church brethren
brother father mother child children man men woman women""".split())


class BookIndex:
    """Word list + inverted index for one 1830 book text (fast anchoring)."""

    def __init__(self, raw):
        self.raw = raw
        # Word list + char offset per word so snippets map back exactly.
        self.words, self.offsets = [], []
        for m in re.finditer(r"[a-z]+", raw.lower()):
            self.words.append(m.group(0))
            self.offsets.append(m.start())
        self.freq = Counter(self.words)
        self.pos = {}
        for i, w in enumerate(self.words):
            self.pos.setdefault(w, []).append(i)

    def rare_words(self, modern_words, k=4):
        cands = [w for w in set(modern_words)
                 if len(w) > 4 and w not in STOP and w in self.pos]
        cands.sort(key=lambda w: (len(self.pos[w]), -len(w)))
        return cands[:k]

    def candidates(self, modern_words, n, pad=8):
        rares = self.rare_words(modern_words)
        starts = set()
        for w in rares:
            for p in self.pos[w][:40]:
                # Sweep starts around each anchor: the verse may begin
                # anywhere in the words before the anchor word.
                lo = max(0, p - n - pad)
                for s in range(lo, min(p + 1, len(self.words)), 2):
                    starts.add(s)
                    if len(starts) > 3000:
                        break
                if len(starts) > 3000:
                    break
            if len(starts) > 3000:
                break
        if not starts:  # every word is common — coarse fallback stride
            starts = set(range(0, len(self.words) - n, max(1, len(self.words) // 400)))
        return rares, sorted(starts)


def align(modern, book_text, pad=8):
    """Best fuzzy word-window match of modern verse inside 1830 book text.

    Keyword-anchored: windows are scored only around positions of the verse's
    rarest content words (inverted index), not across the whole book.
    Returns (score, snippet_raw, window_norm). Score is SequenceMatcher ratio
    on normalized word strings.
    """
    mw = _norm(modern).split()
    if isinstance(book_text, BookIndex):
        bi = book_text
    else:
        bi = BookIndex(book_text)
    bw = bi.words
    if not mw or not bw:
        return 0.0, "", ""
    n = len(mw)
    win = n + pad
    mstr = " ".join(mw)
    rares, starts = bi.candidates(mw, n)
    best, best_i = -1.0, 0
    for i in starts:
        c = " ".join(bw[i:i + win])
        s = SequenceMatcher(None, mstr, c).ratio()
        if s > best:
            best, best_i = s, i
    wnorm = " ".join(bw[best_i:best_i + win])
    # Surrounding span for the presence test: the scored window can clip a
    # long verse's tail (cf. hel.8.20), so absence must hold wider too.
    ext_lo, ext_hi = max(0, best_i - pad * 2), best_i + win + pad * 3
    surrounding = " ".join(bw[ext_lo:ext_hi])
    # Readable snippet cut at the matched window's own char offset
    # (never .find() from book start — that lands on unrelated occurrences).
    if bi.offsets and best_i < len(bi.offsets):
        j = bi.offsets[best_i]
    else:
        frac = best_i / max(1, len(bw))
        j = int(frac * len(bi.raw))
    snippet = bi.raw[max(0, j - 200):j + 600].strip()
    # Section attribution: caller fills this in; keep snippet-level here
    return round(best, 3), snippet, wnorm, surrounding


def find_section(secs, bid, snippet_probe):
    """Which 1830 section holds this match? Probe with first 40 chars."""
    probe = snippet_probe[:40].lower()
    frag = FRAG[bid]

    def tail(t):
        return t.split("Book of Mormon (1830)/", 1)[-1]

    for t in sorted(secs):
        if frag in tail(t) and probe and probe in secs[t].lower():
            return t
    # fallback: any section in this book containing a long probe word
    words = [w for w in probe.split() if len(w) > 6][:2]
    for t in sorted(secs):
        if frag in tail(t) and any(w in secs[t].lower() for w in words):
            return t
    return ""


def get_modern(verse_id):
    from lib.db import get_db, get_verse
    b, c, v = verse_id.split(".")
    conn = get_db()
    try:
        r = get_verse(conn, b, int(c), int(v))
    finally:
        conn.close()
    if not r:
        return None
    return r.get("text_english", "")


def do_lookup(secs, btexts, verse_id):
    bid, ch, vs = verse_id.split(".")
    modern = get_modern(verse_id)
    if modern is None:
        return {"verse": verse_id, "error": "modern verse not found"}
    bt = btexts.get(bid, "")
    if not bt:
        return {"verse": verse_id, "modern": modern,
                "error": f"no 1830 text mapped for book {bid}"}
    score, snippet, wnorm, surrounding = align(modern, bt)
    stripped = re.sub(r"\bson of\b", "", _norm(modern))
    sscore, _, _, _ = align(" ".join(stripped.split()), bt)
    in_window = "son of" in wnorm
    in_surrounding = "son of" in surrounding
    has_sonof_modern = "son of" in _norm(modern)
    # Second key phrase: verses pulled in via "Only Begotten" (e.g. Alma
    # 5:48, 13:9) carry no "son of" at all — judge them on their own phrase
    # instead of mislabeling them REWORDED.
    KEY = ("son of", "only begotten")
    mod_hits = {p for p in KEY if p in _norm(modern)}
    found_1830 = {p for p in mod_hits if p in wnorm or p in surrounding}
    missing = sorted(mod_hits - found_1830)
    # Presence/absence on a well-aligned window is the signal; the stripped
    # score delta is only a tiebreak (long verses dilute the delta).
    if missing and score >= 0.5:
        flag = "INSERTION_CANDIDATE"
    elif mod_hits and not missing:
        flag = "SAME"
    elif score < 0.35:
        flag = "UNCERTAIN"
    else:
        flag = "REWORDED"
    return {
        "verse": verse_id,
        "modern": modern,
        "sonof_in_modern": has_sonof_modern,
        "1830_section": find_section(secs, bid, snippet),
        "1830_snippet": snippet,
        "align_score": score,
        "align_score_stripped": sscore,
        "sonof_in_1830_window": in_window,
        "sonof_in_1830_surrounding": in_surrounding,
        "key_phrases_modern": sorted(mod_hits),
        "key_phrases_missing_in_1830": missing,
        "flag": flag,
    }


def do_status(secs):
    btexts = book_texts(secs)
    books = {b: len(t) for b, t in btexts.items()}
    return {
        "sections": len(secs),
        "source": os.path.basename(TEXT1830),
        "books_mapped": sum(1 for v in books.values() if v > 0),
        "book_chars": books,
        "unmapped": [b for b, v in books.items() if not v],
    }


def do_sonof(secs, btexts, limit=0):
    from lib.db import get_db
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, text_english FROM verses WHERE (text_english LIKE '%Son of God%'"
            " OR text_english LIKE '%Son of the Eternal%'"
            " OR text_english LIKE '%Son of the Everlasting%'"
            " OR text_english LIKE '%Only Begotten%')"
            " AND book_id IN ('1ne','2ne','jacob','enos','jarom','omni','wom','mosiah',"
            "'alma','hel','3ne','4ne','morm','ether','moro') ORDER BY id").fetchall()
        rows = [dict(r) for r in rows]
    finally:
        conn.close()
    if limit:
        rows = rows[:limit]
    out = []
    for r in rows:
        out.append(do_lookup(secs, btexts, r["id"]))
    tally = {}
    for o in out:
        tally[o["flag"]] = tally.get(o["flag"], 0) + 1
    return {"count": len(out), "tally": tally, "verses": out}


def _textlen(v):
    return len(v.words if isinstance(v, BookIndex) else v)


def do_sync(secs, btexts=None):
    btexts = btexts or book_texts(secs)
    anchors = [do_lookup(secs, btexts, a) for a in ANCHORS]
    ok = sum(1 for a in anchors if a.get("align_score", 0) >= 0.35)
    payload = {
        "source": os.path.basename(TEXT1830),
        "sections": len(secs),
        "books_mapped": sum(1 for v in btexts.values() if _textlen(v) > 0),
        "anchors": [
            {"verse": a["verse"], "score": a.get("align_score"),
             "flag": a.get("flag"), "section": a.get("1830_section")}
            for a in anchors
        ],
        "anchor_pass_rate": f"{ok}/{len(anchors)}",
        "synced": ok == len(anchors),
    }
    with open(SYNCFILE, "w") as f:
        json.dump(payload, f, indent=2)
    payload["sync_file"] = SYNCFILE
    return payload


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])
    action = args.get("action", "status")
    secs, err = load_1830()
    if err:
        print(json.dumps({"error": err}, indent=2))
        return
    btexts = book_texts(secs)
    bidx = {b: BookIndex(t) for b, t in btexts.items() if t}
    if action == "status":
        res = do_status(secs)
    elif action == "lookup":
        v = args.get("verse", "")
        if not v or v.count(".") != 2:
            res = {"error": "pass verse like 1ne.11.18"}
        else:
            res = do_lookup(secs, bidx, v)
    elif action == "sonof":
        res = do_sonof(secs, bidx, limit=int(args.get("limit", 0)))
    elif action == "sync":
        res = do_sync(secs, bidx)
    else:
        res = {"error": f"unknown action {action}",
               "actions": ["status", "lookup", "sonof", "sync"]}
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
