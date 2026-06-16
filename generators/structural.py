"""Structural generator — chiastic pair connections.

Connects outer pairs, pivot-center, and inner layers from known chiasms.
Creates connections at the structural layer showing the mirror
relationship between paired sections of a chiasm.
"""

import json
from lib.db import add_connection


def run(conn, book_ids=None):
    """Generate structural connections from known chiasms.

    1. For each known chiasm, connect start↔end (outer pair)
    2. Connect pivot to both start and end
    3. Parse layers_json for inner pairs (A↔A', B↔B')
    4. Hook detected chiasms from patterns table

    Returns count of connections created.
    """
    count = 0

    # Step 1: Process known chiasms
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT * FROM known_chiasms WHERE book_id IN ({placeholders})
        """, book_ids).fetchall()
    else:
        rows = conn.execute("SELECT * FROM known_chiasms").fetchall()

    for row in rows:
        r = dict(row)
        start = r.get("start_verse", "")
        end = r.get("end_verse", "")
        pivot = r.get("pivot_verse", "")
        conf = r.get("confidence", 0.7)

        # Outer pair
        if start and end and start != end:
            try:
                add_connection(conn, start, end,
                              layer="structural", type_name="chiastic",
                              subtype="outer_pair",
                              strength=conf, confidence=conf,
                              discovered_by="algorithm",
                              metadata={
                                  "scholar": r.get("scholar", ""),
                                  "chiasm_id": r["id"],
                                  "pair": f"{start}↔{end}",
                              })
                count += 1
            except Exception:
                pass

        # Pivot connections
        if pivot and pivot != start:
            for v in [start] if end == pivot else [start, end]:
                if v and v != pivot:
                    try:
                        add_connection(conn, pivot, v,
                                      layer="structural", type_name="chiastic",
                                      subtype="chiasm_pivot",
                                      strength=min(0.95, conf + 0.1),
                                      confidence=conf,
                                      discovered_by="algorithm",
                                      metadata={"chiasm_id": r["id"], "pair": "pivot"})
                        count += 1
                    except Exception:
                        pass

        # Inner pairs from layers_json
        try:
            layers = json.loads(r["layers_json"]) if r.get("layers_json") else []
        except (json.JSONDecodeError, TypeError):
            layers = []

        if layers:
            for i in range(len(layers) // 2):
                a = layers[i]
                b = layers[-(i + 1)]
                av = a.get("start", "") or a.get("verse", "")
                bv = b.get("end", "") or b.get("verse", "")
                if av and bv:
                    try:
                        add_connection(conn, av, bv,
                                      layer="structural", type_name="chiastic",
                                      subtype=r.get("chiasm_type", "known_chiasm"),
                                      strength=conf, confidence=conf,
                                      discovered_by="algorithm",
                                      metadata={
                                          "pair": f"{a.get('letter', '?')}↔{b.get('letter', '?')}",
                                          "chiasm_id": r["id"],
                                      })
                        count += 1
                    except Exception:
                        pass

    # Step 2: Link chiasms to their book (as metadata grouping)
    chiasm_count = len(rows)
    conn.commit()
    print(f"  Structural (chiastic): {count} connections from {chiasm_count} chiasms")
    return count
