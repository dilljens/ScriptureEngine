#!/usr/bin/env python3
"""Mukdam u'Meuchar (מוקדם ומאוחר) — Non-Chronological Order Detection.

The principle that the Torah does not always follow chronological order.
Earlier events can be mentioned after later ones.

Detects passages that reference events out of narrative sequence by:
1. Finding temporal markers that conflict with the surrounding timeline
2. Identifying genealogies and king lists that break narrative flow
3. Matching against known rabbinic cases of non-chronological order

Existing algorithmic seeds (from docs/wiki/plans/rabbinic-kabbalistic-tools.md):
1. Genesis 38 — Judah and Tamar interrupts the Joseph narrative
2. Genesis 36:31 — Kings of Edom mentioned before kings ruled Israel
3. Genesis 35:8 — Deborah's death mentioned out of sequence
4. Exodus 6:14-27 — Genealogy interrupts Moses' call narrative
5. Numbers 7 — Tabernacle offerings chronologically displaced
6. Numbers 9:1-14 — Second Passover before the cloud narrative

Usage:
    python3 scripts/detect_mukdam_umeuchar.py
"""

import sys, os, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db

# Known cases from rabbinic tradition
KNOWN_CASES = [
    {
        "verse_id": "gen.38.1",
        "description": "Judah and Tamar interrupts the Joseph narrative (Gen 37-50)",
        "tradition": "rabbinic",
        "reference": "Genesis 38 — Judah and Tamar interrupts the Joseph narrative timeline",
        "confidence": 0.9,
    },
    {
        "verse_id": "gen.36.31",
        "description": "Kings of Edom mentioned before kings ruled Israel",
        "tradition": "rabbinic",
        "reference": "Genesis 36:31 — 'before there reigned any king over Israel' — anachronistic",
        "confidence": 0.9,
    },
    {
        "verse_id": "gen.35.8",
        "description": "Deborah's death mentioned out of sequence (before events that already occurred)",
        "tradition": "rabbinic",
        "reference": "Genesis 35:8 — Deborah dies but was introduced earlier in Gen 24:59",
        "confidence": 0.8,
    },
    {
        "verse_id": "exo.6.14",
        "description": "Genealogy interrupts Moses' call narrative between chapters 6 and 7",
        "tradition": "rabbinic",
        "reference": "Exodus 6:14-27 — genealogical insertion breaks the chronological flow",
        "confidence": 0.85,
    },
    {
        "verse_id": "num.7.1",
        "description": "Tabernacle offerings chronologically displaced (events from Exodus 40)",
        "tradition": "rabbinic",
        "reference": "Numbers 7 — describes offerings from the first month but placed in the second year",
        "confidence": 0.8,
    },
    {
        "verse_id": "num.9.1",
        "description": "Second Passover discussed before the cloud narrative that chronologically precedes it",
        "tradition": "rabbinic",
        "reference": "Numbers 9:1-14 — Second Passover before Numbers 9:15-23 (the cloud)",
        "confidence": 0.8,
    },
]


def detect_temporal_disruptions(conn, book_id):
    """Find potential non-chronological passages by detecting temporal markers
    that conflict with surrounding context.
    
    Looks for:
    - 'before there reigned' style anachronisms
    - Genealogies that interrupt narrative
    - Time references that don't fit the surrounding chapter timeline
    """
    verses = conn.execute(
        "SELECT id, text_english, chapter, verse FROM verses WHERE book_id=? AND text_english IS NOT NULL ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)",
        (book_id,)
    ).fetchall()
    
    disruptions = []
    
    for v in verses:
        text = v["text_english"] or ""
        lower = text.lower()
        
        # Pattern 1: "before there reigned" or "before there was" (anachronism)
        if re.search(r'before there (reigned|was|came)', lower):
            disruptions.append({
                "verse_id": v["id"],
                "type": "anachronism",
                "text": text[:120],
                "confidence": 0.6,
            })
        
        # Pattern 2: Genealogical markers ("these are the generations/sons of")
        if re.search(r'(these are|this is|are the) (generations|sons|descendants) of', lower):
            # Check if this interrupts a narrative
            disruptions.append({
                "verse_id": v["id"],
                "type": "genealogical_insertion",
                "text": text[:120],
                "confidence": 0.4,
            })
        
        # Pattern 3: "in that day" or "at that time" referring to future events
        if re.search(r'at that time|in that day|after these things', lower):
            disruptions.append({
                "verse_id": v["id"],
                "type": "temporal_marker",
                "text": text[:120],
                "confidence": 0.3,
            })
    
    return disruptions


def main():
    conn = get_db()
    
    print("=" * 60)
    print("Mukdam u'Meuchar — Non-Chronological Order Detection")
    print("=" * 60)
    
    # 1. Known cases (already cataloged)
    print(f"\nKnown rabinnic cases: {len(KNOWN_CASES)}")
    for kc in KNOWN_CASES:
        print(f"  ✅ {kc['verse_id']}: {kc['description'][:70]}...")
    
    # 2. Algorithmic detection in narrative books
    narrative_books = ["gen", "exo", "lev", "num", "deu", "josh", "judg", "sam", "kgs"]
    
    all_disruptions = []
    for bid in narrative_books:
        dis = detect_temporal_disruptions(conn, bid)
        for d in dis:
            d["book"] = bid
        all_disruptions.extend(dis)
    
    print(f"\nAlgorithmic detections: {len(all_disruptions)}")
    
    # Store in patterns table
    stored = 0
    for d in all_disruptions:
        if d["confidence"] < 0.5:
            continue
        try:
            conn.execute(
                """INSERT OR IGNORE INTO patterns 
                   (book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata)
                   VALUES (?, ?, ?, 'mukdam_umeuchar', ?, ?, 'algorithm', ?)""",
                (d["book"], d["verse_id"], d["verse_id"],
                 f"{d['type']}: {d['text'][:80]}",
                 d["confidence"],
                 json.dumps({"type": d["type"]}))
            )
            stored += 1
        except Exception:
            pass
    
    conn.commit()
    print(f"  Stored: {stored}")
    
    # Show top findings
    high_confidence = [d for d in all_disruptions if d["confidence"] >= 0.5]
    print(f"\nTop findings:")
    for d in high_confidence[:10]:
        print(f"  [{d['book']}] {d['verse_id']}: {d['type']} (conf={d['confidence']})")
        print(f"    {d['text'][:80]}")
    
    conn.close()


if __name__ == "__main__":
    main()
