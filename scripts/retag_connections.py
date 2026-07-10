#!/usr/bin/env python3
"""Retag existing connections with scholar tags for source attribution.

Adds a 'tag' field to metadata JSON for all connections that have
scholar information but are missing the tag field.
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import get_db


SCHOLAR_TAGS = {
    "Margaret Barker": "barker_temple",
    "L. Michael Morales": "morales_ascent",
    "Barker/ETCBC": "dss_etcbc",
}

SOURCE_TAGS = {
    "Temple Theology": "barker_temple",
    "Who Shall Ascend the Mountain of the Lord": "morales_ascent",
    "BiblicalDSS": "dss_biblical",
}


def retag():
    conn = get_db()
    changed = 0

    rows = conn.execute("""
        SELECT id, metadata FROM connections
        WHERE metadata IS NOT NULL AND metadata != '{}'
    """).fetchall()

    for r in rows:
        try:
            meta = json.loads(r["metadata"])
        except (json.JSONDecodeError, TypeError):
            continue

        if meta.get("tag"):
            continue

        tag = None
        scholar = meta.get("scholar", "")
        source = meta.get("source", "")

        if scholar in SCHOLAR_TAGS:
            tag = SCHOLAR_TAGS[scholar]
        elif source in SOURCE_TAGS:
            tag = SOURCE_TAGS[source]

        if tag:
            meta["tag"] = tag
            conn.execute(
                "UPDATE connections SET metadata = ? WHERE id = ?",
                (json.dumps(meta, ensure_ascii=False), r["id"])
            )
            changed += 1

    conn.commit()
    print(f"Retagged {changed} connections with scholar tags")

    tags = {}
    all_rows = conn.execute("""
        SELECT id, metadata FROM connections
        WHERE metadata IS NOT NULL AND metadata != '{}'
    """).fetchall()
    for r in all_rows:
        try:
            meta = json.loads(r["metadata"])
        except (json.JSONDecodeError, TypeError):
            continue
        t = meta.get("tag")
        if t:
            tags[t] = tags.get(t, 0) + 1

    print("\nTags breakdown:")
    for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    conn.close()
    return changed


if __name__ == "__main__":
    print("=== Retagging Connections ===")
    retag()
