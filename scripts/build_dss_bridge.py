#!/usr/bin/env python3
"""
DSS → Engine Bridge: populate gematria + English gloss for DSS texts.

Reads ETCBC/dss TF v2.0 files directly (fast, no text-fabric).
Populates text_english + gematria for all imported DSS scrolls.

Usage: python3 scripts/build_dss_bridge.py
"""

import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

TF_DIR = "/home/dillon/text-fabric-data/github/ETCBC/dss/tf/2.0"

# ─── Gematria ────────────────────────────────────────────────────────
GEM_STD = {'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,'י':10,
           'כ':20,'ל':30,'מ':40,'נ':50,'ס':60,'ע':70,'פ':80,'צ':90,'ק':100,
           'ר':200,'ש':300,'ת':400,'ך':20,'ם':40,'ן':50,'ף':80,'ץ':90}
GEM_ORD = {'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,'י':10,
           'כ':11,'ל':12,'מ':13,'נ':14,'ס':15,'ע':16,'פ':17,'צ':18,'ק':19,
           'ר':20,'ש':21,'ת':22,'ך':11,'ם':13,'ן':14,'ף':17,'ץ':18}

def gem(word):
    w = word.strip(' ־')
    std = sum(GEM_STD.get(c,0) for c in w)
    ord_v = sum(GEM_ORD.get(c,0) for c in w)
    red = ord_v
    while red > 9: red = sum(int(d) for d in str(red))
    return std or None, ord_v or None, red or None


def tf_read_sparse(filepath):
    """Read a TF sparse column/edge file.

    TF format: @header lines, then data in the form:
      node_id \t value  (explicit start of a run)
      value             (continuation for next sequential node)

    Returns dict node_id -> value.
    """
    with open(filepath) as f:
        lines = f.readlines()

    h = 0
    for line in lines:
        if line.startswith('@'): h += 1
        else: break

    result = {}
    current_node = 0
    for i in range(h, len(lines)):
        line = lines[i].rstrip('\n')
        if not line:
            current_node += 1
            continue

        if '\t' in line:
            parts = line.split('\t', 1)
            try:
                current_node = int(parts[0])
            except ValueError:
                current_node += 1
            val = parts[1].strip()
        else:
            current_node += 1
            val = line.strip()

        if val:
            result[current_node] = val

    return result


def tf_read_oslots(filepath, non_sign_start=1430242):
    """Parse oslots.tf edge file.

    TF oslots stores slot mappings sequentially. Format:
      source_node \t target_slot(s)   (explicit source, first line only)
      target_slot(s)                   (subsequent lines = next node IDs)

    Returns dict node_id -> set(slot_ids).
    """
    with open(filepath) as f:
        lines = f.readlines()

    h = 0
    for line in lines:
        if line.startswith('@'): h += 1
        else: break

    result = {}
    current_nid = non_sign_start  # First non-sign node

    for i in range(h, len(lines)):
        line = lines[i].rstrip('\n')
        if not line:
            current_nid += 1
            continue

        if '\t' in line:
            parts = line.split('\t', 1)
            try:
                current_nid = int(parts[0])
                rest = parts[1]
            except (ValueError, IndexError):
                rest = line
        else:
            rest = line

        # Parse slot tokens (single numbers and ranges)
        for tok in rest.split():
            if '-' in tok:
                try:
                    a, b = tok.split('-', 1)
                    for sid in range(int(a), int(b)+1):
                        if current_nid not in result:
                            result[current_nid] = set()
                        result[current_nid].add(sid)
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    sid = int(tok)
                    if current_nid not in result:
                        result[current_nid] = set()
                    result[current_nid].add(sid)
                except ValueError:
                    pass

        current_nid += 1

    return result


def main():
    t0 = time.time()
    print("DSS Bridge — building gematria + English gloss")

    # ── Parse otype ──
    ranges = {}
    with open(f"{TF_DIR}/otype.tf") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('@'): continue
            if '\t' in line:
                r, t = line.split('\t', 1)
                a, b = r.split('-') if '-' in r else (r, r)
                ranges[t] = (int(a), int(b))

    max(r[1] for r in ranges.values())
    w_start, w_end = ranges['word']        # 1606869-2107863
    l_start, l_end = ranges['line']        # 1552973-1605867
    f_start, f_end = ranges['fragment']    # 1531341-1542522
    print(f"Word range:     {w_start}-{w_end} ({w_end-w_start+1})")
    print(f"Line range:     {l_start}-{l_end} ({l_end-l_start+1})")
    print(f"Fragment range: {f_start}-{f_end} ({f_end-f_start+1})")

    # ── Read sparse columns ──
    print("Reading scroll, fragment, line...", end=' ', flush=True)
    scroll_map = tf_read_sparse(f"{TF_DIR}/scroll.tf")
    tf_read_sparse(f"{TF_DIR}/fragment.tf")
    tf_read_sparse(f"{TF_DIR}/line.tf")

    # Build scroll_name -> set of nodes that have that scroll
    # Filter to target scrolls
    TARGETS = [
        '1QS','1QSa','1QSb','1QM','1QHa','1QpHab',
        '11Q13','11Q19','11Q20','CD',
        '4Q400','4Q401','4Q402','4Q403','4Q404','4Q405','4Q406','4Q407',
        '4Q174','4Q246','4Q521',
        '4Q266','4Q267','4Q268','4Q269','4Q270','4Q271','4Q272','4Q273',
        '4Q394','4Q395','4Q396','4Q397','4Q398','4Q399','1Qisaa',
    ]

    # Get set of node IDs belonging to each target scroll
    scroll_nodes = defaultdict(set)
    for nid, sname in scroll_map.items():
        if sname in TARGETS:
            scroll_nodes[sname].add(nid)

    print(f"{len(scroll_map)} mapped nodes")
    for t in TARGETS:
        if t in scroll_nodes:
            print(f"  {t}: {len(scroll_nodes[t])} nodes")
    print(f"({time.time()-t0:.1f}s)")
    sys.stdout.flush()

    # ── Read glyph, glex, lex (also sparse) ──
    print("Reading glyph/glex/lex...", end=' ', flush=True)
    glyph = tf_read_sparse(f"{TF_DIR}/glyph.tf")
    glex = tf_read_sparse(f"{TF_DIR}/glex.tf")
    lex_col = tf_read_sparse(f"{TF_DIR}/lex.tf")
    print(f"{len(glyph)} glyph, {len(glex)} glex, {len(lex_col)} lex ({time.time()-t0:.1f}s)")
    sys.stdout.flush()

    # ── Read oslots ──
    print("Reading oslots...", end=' ', flush=True)
    oslots = tf_read_oslots(f"{TF_DIR}/oslots.tf")
    print(f"{len(oslots)} nodes with slots ({time.time()-t0:.1f}s)")
    sys.stdout.flush()

    # ── Build word → scroll mapping ──
    print("Mapping words to scrolls...", end=' ', flush=True)

    # For each word node, check which scroll it belongs to
    # via the scroll_map (which maps arbitrary nodes to scrolls)
    #
    # TF convention: scroll_map maps nodes of any type to their scroll
    # For a word in range word_start..word_end, we find its parent fragment/line
    #
    # Simpler: use oslots to find which sign slots a word covers,
    # then check which scroll's sign slots contain it.
    #
    # Even simpler: scroll_map[nid] directly maps a word's node_id
    # to its scroll name, if the TF data follows that convention.

    # Check if word nodes are directly in scroll_map
    word_scroll = {}
    for w_nid in range(w_start, w_end + 1):
        if w_nid in scroll_map:
            word_scroll[w_nid] = scroll_map[w_nid]

    # If few words have direct scroll entries, use fragment membership
    if len(word_scroll) < 100:
        print(f"\n  Direct word→scroll: {len(word_scroll)} — too few, using fragment/line hierarchy...")

        # Build sign → fragment mapping
        # fragment_map maps fragment nodes to scroll names
        # A word belongs to a scroll if its signs overlap with that scroll's fragments

        # Build fragment → scroll lookup
        frag_scroll = {}
        for nid, sname in scroll_map.items():
            if f_start <= nid <= f_end and sname in TARGETS:
                frag_scroll[nid] = sname

        # Build sign → fragment mapping from oslots of fragment nodes
        sign_frag = {}
        for fnid in range(f_start, f_end + 1):
            if fnid in oslots and fnid in frag_scroll:
                scroll_name = frag_scroll[fnid]
                for s in oslots[fnid]:
                    if s not in sign_frag:
                        sign_frag[s] = scroll_name

        # Map each word to its scroll via sign membership
        for w_nid in range(w_start, w_end + 1):
            if w_nid in oslots:
                slots = oslots[w_nid]
                if slots:
                    fs = min(slots)  # Sign IDs are monotonic — first sign tells scroll
                    if fs in sign_frag:
                        word_scroll[w_nid] = sign_frag[fs]

    print(f"{len(word_scroll)} words mapped ({time.time()-t0:.1f}s)")
    sys.stdout.flush()

    # ── Build scroll → words → line structure ──
    print("Building scroll→line→word...")

    conn = get_db()
    total_gem = 0
    total_eng = 0

    for scroll_name in TARGETS:
        # Get all word nodes for this scroll
        w_nodes = sorted([nid for nid, s in word_scroll.items() if s == scroll_name])
        if not w_nodes:
            print(f"  {scroll_name}: no word nodes found")
            continue

        # Get existing verses
        existing = conn.execute(
            "SELECT id, verse FROM verses WHERE book_id=? ORDER BY verse",
            (scroll_name,)
        ).fetchall()
        if not existing:
            print(f"  {scroll_name}: no verses in DB")
            continue

        # Line→words: For each line, oslots tells which sign slots it covers.
        # A word's oslots are its sign slots.
        # If word_W's signs ⊆ line_L's signs, word_W belongs to line_L.
        # For efficiency with contiguous sign IDs:
        #   word belongs to line if line.min_sign <= word.min_sign and word.max_sign <= line.max_sign
        #
        # Build line → sign_range for lines in this scroll
        line_range = {}
        for lnid in range(l_start, l_end + 1):
            sname = scroll_map.get(lnid, '')
            if sname == scroll_name and lnid in oslots:
                slots = oslots[lnid]
                if slots:
                    line_range[lnid] = (min(slots), max(slots))

        if not line_range:
            print(f"  {scroll_name}: no lines found")
            continue

        sorted_lines = sorted(line_range.items(), key=lambda x: x[1][0])

        # Assign words to lines by sign range
        n = min(len(existing), len(sorted_lines))
        gem_batch = []
        eng_updates = []
        word_idx = 0

        for li in range(n):
            verse_id = existing[li]['id']
            line_nid, (l_min, l_max) = sorted_lines[li]

            # Collect all words whose signs fall within this line's sign range
            line_words = []
            for wi in range(word_idx, len(w_nodes)):
                w_nid = w_nodes[wi]
                w_slots = oslots.get(w_nid, set())
                if not w_slots:
                    continue
                w_min, w_max = min(w_slots), max(w_slots)
                if w_min > l_max:
                    # Past this line — next line's words start here
                    word_idx = wi
                    break
                if w_min >= l_min and w_max <= l_max:
                    line_words.append(w_nid)
                    word_idx = wi + 1

            # Build glosses and gematria entries
            glosses = []
            for wi_off, w_nid in enumerate(line_words):
                g = glyph.get(w_nid, '')
                gl = glex.get(w_nid, '')
                lx = lex_col.get(w_nid, '')
                if g:
                    if gl: glosses.append(gl)
                    std, ord_v, red_val = gem(g)
                    if std:
                        gem_batch.append((
                            verse_id, wi_off, g.strip(),
                            lx if lx else g.strip()[:20],
                            std, ord_v or 0, red_val or 0,
                            lx if lx else '',
                        ))

            if glosses:
                eng_updates.append((' '.join(glosses), verse_id))

        # Batch apply
        for eng_txt, vid in eng_updates:
            conn.execute(
                "UPDATE verses SET text_english=? WHERE id=? AND (text_english IS NULL OR text_english='')",
                (eng_txt, vid)
            )
            total_eng += 1

        if gem_batch:
            conn.executemany("""
                INSERT OR IGNORE INTO gematria
                    (verse_id, word_index, word_hebrew, lemma,
                     value_standard, value_ordinal, value_reduced, hebrew_plain)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, gem_batch)
            total_gem += len(gem_batch)

        conn.commit()
        print(f"  {scroll_name:8s}: {n:5d} lines, {len(gem_batch):6d} gematria, {len(eng_updates):5d} gloss | {len(w_nodes)} words")
        sys.stdout.flush()

    # ── Report ──
    print(f"\n{'='*60}")
    print(f"Done in {time.time()-t0:.1f}s")
    print(f"  English glosses added: {total_eng}")
    print(f"  Gematria entries added: {total_gem}")

    dss_gem = conn.execute("""SELECT COUNT(*) FROM gematria g
        JOIN verses v ON v.id=g.verse_id
        WHERE v.book_id IN (SELECT id FROM books WHERE work_id='dss')""").fetchone()[0]
    dss_eng = conn.execute("""SELECT COUNT(*) FROM verses v
        WHERE v.book_id IN (SELECT id FROM books WHERE work_id='dss')
        AND v.text_english != ''""").fetchone()[0]
    print(f"\n  DSS verses with English: {dss_eng} / 7655")
    print(f"  DSS gematria entries: {dss_gem}")
    conn.close()


if __name__ == '__main__':
    main()
