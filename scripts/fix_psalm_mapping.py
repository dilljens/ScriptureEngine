#!/usr/bin/env python3
"""Fix Psalm Vulgate chapter mapping.

The Vulgate Psalms use different numbering than KJV/MT.
Vulgate 1-8 = KJV 1-8
Vulgate 9 = KJV 9+10 (combined)
Vulgate 10-112 = KJV 11-113
Vulgate 113 = KJV 114+115 (combined)
Vulgate 114 = KJV 116:1-9
Vulgate 115 = KJV 116:10-19
Vulgate 116-145 = KJV 117-146
Vulgate 146 = KJV 147:1-11
Vulgate 147 = KJV 147:12-20
Vulgate 148-150 = KJV 148-150

Uses verse-level split mapping for combined psalms.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

VULGATE_JSON = 'https://raw.githubusercontent.com/yoarikso/latinvulgatebible/master/vulgate-json/EntireBible-VULGATE.json'

def map_psalm_verse(vg_ch, vg_v):
    """Map (Vulgate chapter, Vulgate verse) -> (KJV chapter, KJV verse).

    Returns (kjv_chapter, kjv_verse) or None if no mapping.
    """
    ch = int(vg_ch)
    v = int(vg_v)

    # 1-8 → 1-8 (direct)
    if 1 <= ch <= 8:
        return (ch, v)

    # 9: Vulgate 9 = KJV 9 (v1-18) + KJV 10 (v19-21 remapped to KJV v1-3)
    if ch == 9:
        if v <= 18:
            return (9, v)
        elif v <= 21:
            return (10, v - 18)  # v19→v1, v20→v2, v21→v3
        else:
            return None

    # 10-112 → 11-113 (+1 chapter, same verse)
    if 10 <= ch <= 112:
        return (ch + 1, v)

    # 113: Vulgate 113 = KJV 114 (v1-8) + KJV 115 (v9-15 remapped to v1-7)
    if ch == 113:
        if v <= 8:
            return (114, v)
        elif v <= 15:
            return (115, v - 8)  # v9→v1, v10→v2, ...
        else:
            return None

    # 114-115 → 116 (all verses, kept in order)
    # Vulgate 114:1-9 → KJV 116:1-9
    # Vulgate 115:10-19 → KJV 116:10-19
    if 114 <= ch <= 115:
        return (116, v)

    # 116-145 → 117-146 (+1 chapter)
    if 116 <= ch <= 145:
        return (ch + 1, v)

    # 146-147 → 147 (sequential: 146:1-11→147:1-11, 147:12-20→147:12-20)
    if 146 <= ch <= 147:
        return (147, v)

    # 148-150 → 148-150
    if 148 <= ch <= 150:
        return (ch, v)

    # 151 → no mapping
    return None


def fix_psalms():
    """Re-insert Vulgate Psalms with correct chapter mapping."""
    conn = get_db()

    # Delete existing Vulgate Psalm entries
    conn.execute("DELETE FROM textual_variants WHERE tradition = 'vulgate' AND verse_id LIKE 'psa.%'")
    conn.commit()
    print("  Deleted existing Vulgate Psalm entries")

    # Download fresh or use cached
    print("  Downloading Vulgate JSON...", flush=True)
    req = urllib.request.Request(VULGATE_JSON, headers={'User-Agent': 'Mozilla/5.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())

    psalms_data = data.get('Psalms', {})
    if not psalms_data:
        print("  ERROR: No Psalms data found!")
        return

    # Remove charset keys
    psalm_chapters = {k: v for k, v in psalms_data.items() if k != 'charset'}
    print(f"  Processing {len(psalm_chapters)} Vulgate psalms...", flush=True)

    total = 0
    skipped = 0

    for vg_ch, verses in sorted(psalm_chapters.items(), key=lambda x: int(x[0])):
        # Remove charset verse keys
        clean_verses = {k: v for k, v in verses.items() if k != 'charset'}
        len(clean_verses)

        for vg_v, text in sorted(clean_verses.items(), key=lambda x: int(x[0])):
            mapping = map_psalm_verse(int(vg_ch), int(vg_v))

            if mapping is None:
                skipped += 1
                continue  # Psalm 151, no mapping

            kjv_ch, kjv_v = mapping
            verse_id = f"psa.{kjv_ch}.{kjv_v}"

            # Verify verse exists
            exists = conn.execute(
                "SELECT 1 FROM verses WHERE id = ?", (verse_id,)
            ).fetchone()

            if exists:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO textual_variants
                            (verse_id, tradition, text, source, notes)
                        VALUES (?, 'vulgate', ?, 'Clementine Vulgate', ?)
                    """, (verse_id, text, f"Vulgate chapter {vg_ch}"))
                    total += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  Inserted {total} Vulgate Psalm verses")
    if skipped:
        print(f"  Skipped {skipped} (Psalm 151 / no mapping)")

    # Verify
    final = conn.execute("SELECT COUNT(*) FROM textual_variants WHERE tradition='vulgate' AND verse_id LIKE 'psa.%'").fetchone()[0]
    print(f"  Final Psalm entries: {final}")

    # Also fix the connections: delete and regenerate for Psalms
    conn.execute("""
        DELETE FROM connections
        WHERE type = 'vulgate_variant' AND discovered_by = 'algorithm'
        AND (source_verse LIKE 'psa.%' OR target_verse LIKE 'psa.%')
    """)
    conn.commit()

    # Recreate Psalm connections (hub-and-spoke)
    var_rows = conn.execute("""
        SELECT tv.verse_id, tv.text
        FROM textual_variants tv
        WHERE tv.tradition = 'vulgate'
          AND tv.verse_id LIKE 'psa.%'
        ORDER BY tv.verse_id
    """).fetchall()

    if len(var_rows) >= 2:
        hub = var_rows[0]['verse_id']
        for r in var_rows[1:]:
            text_snippet = (r['text'] or '')[:80]
            conn.execute("""
                INSERT OR IGNORE INTO connections
                    (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                VALUES (?, ?, 'textual', 'vulgate_variant', 'book_psa', 0.5, 0.6, 'algorithm', ?)
            """, (hub, r['verse_id'],
                  '{"vulgate": "' + text_snippet.replace('"', "'") + '", "book": "psa", "variant_type": "systematic"}'))
        conn.commit()
        print(f"  Created {len(var_rows)-1} Psalm vulgate_variant connections")

    conn.close()
    print("  Done.")


if __name__ == "__main__":
    print("=" * 60)
    print("  FIX PSALM VULGATE MAPPING")
    print("=" * 60)
    fix_psalms()
