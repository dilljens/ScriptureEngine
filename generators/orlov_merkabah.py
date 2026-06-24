"""Orlov/Schäfer Merkabah — Hebrew/Greek priority, English fallback.

Priority: Hebrew lemma (OT) → Greek lemma (NT) → English keyword (BoM/D&C).
"""

import json
from ._heb_grk import (
    get_ot_by_lemmas, get_ot_by_lemma, get_nt_by_greek,
    get_cross_canon, add_connections_for_group,
)

META = json.dumps({
    "scholar": "Andrei Orlov",
    "source": "The Enoch-Metatron Tradition",
    "tag": "orlov_merkabah",
}, ensure_ascii=False)

META_SCHAFER = json.dumps({
    "scholar": "Peter Schäfer",
    "source": "The Origins of Jewish Mysticism",
    "tag": "schafer_hekhalot",
}, ensure_ascii=False)


def run(conn, book_ids=None):
    count = 0
    
    # 1. Throne visions: Hebrew 3678 (kisse/throne), Greek θρόνος
    kisse = get_ot_by_lemma(conn, '3678')
    thronos = get_nt_by_greek(conn, 'θρόνο')
    cc_throne = get_cross_canon(conn, 'throne')
    all_throne = list(set(kisse + thronos + cc_throne))
    
    c = add_connections_for_group(conn, all_throne, "sod", "merkabah",
                                   "throne_vision", 0.45, 0.35, "algorithm", META)
    count += c
    
    # 2. Heavenly ascent / visions of God: Hebrew 4758 (mar'eh/vision), 2377 (chazon)
    vision = get_ot_by_lemma(conn, '2377')
    gk_vision = get_nt_by_greek(conn, 'ἀποκάλυψι')
    cc_ascent = get_cross_canon(conn, 'caught up')
    all_ascent = list(set(vision + gk_vision + cc_ascent))
    
    c = add_connections_for_group(conn, all_ascent, "sod", "heavenly_ascent",
                                   "visionary_ascent", 0.45, 0.35, "algorithm", META_SCHAFER)
    count += c
    
    # 3. Two powers in heaven: right hand of God
    # Hebrew 3225 (yamin/right hand) — too broad alone
    # Better: Greek δεξιός (dexios/right hand)
    right_hand = get_nt_by_greek(conn, 'δεξι')
    cc_right = get_cross_canon(conn, 'right hand of God')
    all_right = list(set(right_hand + cc_right))
    
    c = add_connections_for_group(conn, all_right, "sod", "two_powers",
                                   "heavenly_mediator", 0.5, 0.4, "algorithm", META)
    count += c
    
    # 4. Heavenly temple: Hebrew 6918 (qadosh/holy) of heavens context
    # Better: Revelation temple language
    rev_temple = [r["id"] for r in conn.execute(
        "SELECT id FROM verses WHERE book_id='rev' AND text_english LIKE '%temple%' LIMIT 20"
    ).fetchall()]
    
    for v in rev_temple:
        for t in all_throne:
            try:
                from lib.db import add_connection
                existing = conn.execute(
                    "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type='hekhalot'",
                    (v, t)
                ).fetchone()[0]
                if existing == 0:
                    add_connection(conn, v, t, layer="sod",
                                  type_name="hekhalot", subtype="heavenly_temple",
                                  strength=0.5, confidence=0.4,
                                  discovered_by="algorithm", metadata=META_SCHAFER)
                    count += 1
            except:
                pass
    
    conn.commit()
    return count
