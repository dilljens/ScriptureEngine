"""Beale temple-creation — Hebrew/Greek priority, English fallback.

Priority: Hebrew lemma (OT) → Greek lemma (NT) → English keyword (BoM/D&C).
"""

import json
from ._heb_grk import (
    get_ot_by_lemmas, get_ot_by_lemma, get_nt_by_greek,
    get_cross_canon, add_connections_for_group,
)

META = json.dumps({
    "scholar": "G.K. Beale",
    "source": "The Temple and the Church's Mission",
    "tag": "beale_temple",
}, ensure_ascii=False)


def run(conn, book_ids=None):
    count = 0
    
    # 1. Temple/tabernacle → creation: Hebrew 4908 (mishkan), 4720 (mikdash)
    mishkan = get_ot_by_lemma(conn, '4908')    # tabernacle
    mikdash = get_ot_by_lemma(conn, '4720')    # sanctuary
    # Greek: ναός (naos/temple), ἱερόν (hieron/temple)
    naos = get_nt_by_greek(conn, 'ναό')
    hieron = get_nt_by_greek(conn, 'ἱερό')
    cc_temple = get_cross_canon(conn, 'temple of God')
    
    all_temple = list(set(mishkan + mikdash + naos + hieron + cc_temple))
    
    # Connect temple verses to creation
    creation = ['gen.1.1','gen.2.1','gen.2.2','gen.2.3','psa.78.69','psa.104.1']
    for t in all_temple:
        for c_verse in creation:
            try:
                from lib.db import add_connection
                existing = conn.execute(
                    "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type='temple_creation'",
                    (t, c_verse)
                ).fetchone()[0]
                if existing == 0:
                    add_connection(conn, t, c_verse, layer="sod",
                                  type_name="temple_creation", subtype="cosmos_temple",
                                  strength=0.4, confidence=0.35,
                                  discovered_by="algorithm", metadata=META)
                    count += 1
            except:
                pass
    
    # 2. Garden/Eden → temple: Hebrew 1588 (gan/garden), 5731 (Eden)
    gan = get_ot_by_lemma(conn, '1588')
    eden = get_ot_by_lemma(conn, '5731')
    # Also cherubim: 3742 (keruv)
    cherub = get_ot_by_lemma(conn, '3742')
    all_eden = list(set(gan + eden + cherub))
    
    c = add_connections_for_group(conn, all_eden, "sod", "eden_temple",
                                   "garden_sanctuary", 0.45, 0.35, "algorithm", META)
    count += c
    
    # 3. Church as temple: NT temple passages + cross-canon
    nt_temple = get_nt_by_greek(conn, 'ναό')
    cc_church = get_cross_canon(conn, 'temple of God')
    all_nt_temple = list(set(nt_temple + cc_church))
    
    # Connect to OT temple presence (Shekinah)
    ot_presence = mishkan + mikdash
    
    for nt in all_nt_temple:
        for ot in ot_presence[:100]:
            try:
                from lib.db import add_connection
                existing = conn.execute(
                    "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type='temple_microcosm'",
                    (nt, ot)
                ).fetchone()[0]
                if existing == 0:
                    add_connection(conn, nt, ot, layer="sod",
                                  type_name="temple_microcosm", subtype="church_as_temple",
                                  strength=0.45, confidence=0.35,
                                  discovered_by="algorithm", metadata=META)
                    count += 1
            except:
                pass
    
    # 4. New Creation temple: Greek καινός (kainos/new) + Ἱερουσαλήμ (Jerusalem)
    new_jer = get_nt_by_greek(conn, 'καιν')
    all_new = list(set(new_jer))
    
    # Connect to Ezekiel's temple vision
    ezek_temple = [r["id"] for r in conn.execute(
        "SELECT id FROM verses WHERE book_id='ezek' AND (text_english LIKE '%measured%' OR text_english LIKE '%living waters%') LIMIT 20"
    ).fetchall()]
    
    for n in all_new:
        for e in ezek_temple:
            try:
                from lib.db import add_connection
                existing = conn.execute(
                    "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type='temple_eschaton'",
                    (n, e)
                ).fetchone()[0]
                if existing == 0:
                    add_connection(conn, n, e, layer="sod",
                                  type_name="temple_eschaton", subtype="new_creation_temple",
                                  strength=0.5, confidence=0.4,
                                  discovered_by="algorithm", metadata=META)
                    count += 1
            except:
                pass
    
    conn.commit()
    return count
