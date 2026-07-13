"""Heiser divine council — Hebrew/Greek priority, English fallback.

Priority: Hebrew lemma (OT) → Greek lemma (NT) → English keyword (BoM/D&C).
"""

import json

from ._heb_grk import (
    add_connections_for_group,
    get_cross_canon,
    get_nt_by_greek,
    get_ot_by_lemmas,
)

META = json.dumps({
    "scholar": "Michael S. Heiser",
    "source": "The Unseen Realm",
    "tag": "heiser_council",
}, ensure_ascii=False)


def run(conn, book_ids=None):
    count = 0

    # 1. Angel of YHWH: Hebrew lemma 4397 (malak) + 3068/3069 (YHWH)
    angel_yhwh = get_ot_by_lemmas(conn, ['4397', '3068'])
    angel_yhwh += get_ot_by_lemmas(conn, ['4397', '3069'])
    angel_nt = get_nt_by_greek(conn, 'ἄγγελος')
    angel_cc = get_cross_canon(conn, 'angel of the Lord')
    all_angel = list(set(angel_yhwh + angel_nt + angel_cc))

    c = add_connections_for_group(conn, all_angel, "sod", "angel_of_yhwh",
                                   "divine_angel", 0.5, 0.4, "algorithm", META)
    count += c

    # 2. Divine council: sons of God (Hebrew 1121 ben + 430 elohim)
    son_god = get_ot_by_lemmas(conn, ['1121'])
    son_nt = get_nt_by_greek(conn, 'υἱό')
    son_cc = get_cross_canon(conn, 'sons of God')
    all_son = list(set(son_god + son_nt + son_cc))

    c = add_connections_for_group(conn, all_son, "sod", "divine_council",
                                   "divine_sonship", 0.5, 0.4, "algorithm", META)
    count += c

    # 3. Council / assembly: Hebrew 5475 (sod/council), 6951 (qahal)
    council = get_ot_by_lemmas(conn, ['5475'])
    qahal = get_ot_by_lemmas(conn, ['6951'])
    all_council = list(set(council + qahal))

    c = add_connections_for_group(conn, all_council, "sod", "divine_council",
                                   "heavenly_court", 0.45, 0.35, "algorithm", META)
    count += c

    conn.commit()
    return count
