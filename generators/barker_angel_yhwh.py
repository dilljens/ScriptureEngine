"""Barker Angel of YHWH — Hebrew/Greek priority, English fallback.

Priority: Hebrew lemma (OT) → Greek lemma (NT) → English keyword (BoM/D&C).
"""

import json

from ._heb_grk import (
    add_connections_for_group,
    get_cross_canon,
    get_nt_by_greek,
    get_ot_by_lemma,
    get_ot_by_lemmas,
)

META = json.dumps({
    "scholar": "Margaret Barker",
    "source": "Temple Theology",
    "tag": "barker_temple",
}, ensure_ascii=False)


def run(conn, book_ids=None):
    count = 0

    # 1. Angel of YHWH (same pattern as Heiser, Barker's primary focus)
    angel_yhwh = get_ot_by_lemmas(conn, ['4397', '3068'])
    angel_yhwh += get_ot_by_lemmas(conn, ['4397', '3069'])
    angel_nt = get_nt_by_greek(conn, 'ἄγγελος')
    angel_cc = get_cross_canon(conn, 'angel of the Lord')
    all_angel = list(set(angel_yhwh + angel_nt + angel_cc))

    c = add_connections_for_group(conn, all_angel, "sod", "angel_of_yhwh",
                                   "barker_angel", 0.55, 0.45, "algorithm", META)
    count += c

    # 2. Day of Atonement / mercy seat: Hebrew 3722 (kaphar/atonement)
    kaphar = get_ot_by_lemma(conn, '3722')
    # Also 3725 (kippurim/atonement)
    atonement = get_ot_by_lemma(conn, '3725')
    all_atone = list(set(kaphar + atonement))

    c = add_connections_for_group(conn, all_atone, "sod", "holy_of_holies",
                                   "atonement_typology", 0.5, 0.4, "algorithm", META)
    count += c

    # 3. Temple microcosm: broader — connect verses with temple/tabernacle
    # to creation passages via lemmas
    # Hebrew 4725 (maqom/place) + 4908 (mishkan/dwelling)
    mishkan = get_ot_by_lemma(conn, '4908')
    mikdash = get_ot_by_lemma(conn, '4720')  # sanctuary
    all_temple = list(set(mishkan + mikdash))

    # Creation passages (key Genesis texts)
    creation = ['gen.1.1','gen.2.1','gen.2.2','gen.2.3']

    for t in all_temple:
        for c_verse in creation:
            try:
                from lib.db import add_connection
                existing = conn.execute(
                    "SELECT COUNT(*) FROM connections WHERE source_verse = ? AND target_verse = ? AND type='temple_microcosm'",
                    (t, c_verse)
                ).fetchone()[0]
                if existing == 0:
                    add_connection(conn, t, c_verse, layer="sod",
                                  type_name="temple_microcosm", subtype="creation_temple",
                                  strength=0.45, confidence=0.35,
                                  discovered_by="algorithm", metadata=META)
                    count += 1
            except Exception:
                pass

    # 4. Divine council + Wisdom theology (Barker's "Lady Wisdom" / Logos)
    # Hebrew 2451 (chokmah/wisdom)
    # Greek σοφία (sophia/wisdom)
    wisdom_ot = get_ot_by_lemma(conn, '2451')
    wisdom_nt = get_nt_by_greek(conn, 'σοφία')
    all_wisdom = list(set(wisdom_ot + wisdom_nt))

    c = add_connections_for_group(conn, all_wisdom, "sod", "divine_ascent",
                                   "wisdom_logos", 0.5, 0.4, "algorithm", META)
    count += c

    conn.commit()
    return count
