"""Narrative Typology (dim 5) — lift verse-level types into passage arcs.

The codebase already has a verse-level typology generator
(generators/typology.py) and a populated `typology` table (curated
type → antitype pairs). This passage-level generator:

1. Reads the curated pairs from the `typology` table, clusters the type verses
   and antitype verses into passage ranges, and connects each type passage to
   its antitype passage (type='typology').
2. Adds a few curated narrative-level arcs (whole-story types) that span
   larger passages.

This is a discovery generator (passage-level).
"""

import logging
from collections import defaultdict

from ._common import to_passages, upsert

logger = logging.getLogger(__name__)

# ── Narrative-level arcs (whole-story types) ─────────────────────────
# Beyond the verse-level pairs in the typology table, these arcs connect
# larger narrative units.
NARRATIVE_ARCS = [
    {
        "name": "Exodus → Salvation narrative",
        "type_start": "exo.1.1", "type_end": "exo.15.21",
        "antitype_start": "matt.1.18", "antitype_end": "matt.2.23",
        "description": "Deliverance from Egypt as type of deliverance in Christ",
    },
    {
        "name": "Wilderness → Testing of the Church",
        "type_start": "num.14.1", "type_end": "num.14.45",
        "antitype_start": "1cor.10.1", "antitype_end": "1cor.10.13",
        "description": "Forty years of testing as type of the church's testing",
    },
    {
        "name": "Temple → Body of Christ",
        "type_start": "1kgs.6.1", "type_end": "1kgs.8.66",
        "antitype_start": "john.2.18", "antitype_end": "john.2.22",
        "description": "Solomon's temple as type of Christ's body",
    },
    {
        "name": "Israel in Egypt → Son out of Egypt",
        "type_start": "gen.46.1", "type_end": "gen.47.12",
        "antitype_start": "matt.2.13", "antitype_end": "matt.2.15",
        "description": "Hosea 11:1 'out of Egypt I called my son' — Israel as type of Christ",
    },
]


def _table_pairs(conn):
    """Curated pairs from the typology table: name -> {type_verses, antitype_verses}."""
    groups = defaultdict(lambda: {"type": [], "antitype": []})
    try:
        rows = conn.execute(
            "SELECT type_name, antitype_name, type_verse, antitype_verse FROM typology"
        ).fetchall()
    except Exception as e:  # pragma: no cover - table missing
        logger.warning("typology table unavailable: %s", e)
        return groups
    for r in rows:
        key = f"{r['type_name']} → {r['antitype_name']}"
        if r["type_verse"]:
            groups[key]["type"].append(r["type_verse"])
        if r["antitype_verse"]:
            groups[key]["antitype"].append(r["antitype_verse"])
    return groups


def run(conn, book_ids=None) -> int:
    """Connect curated type passages to their antitype passages.

    Returns the number of passage_connections created.
    """
    total = 0

    def scoped(start, end):
        return not book_ids or start.split(".")[0] in book_ids

    # 1. Passage arcs from the curated typology table. The table stores
    # single-verse pairs (gen.2.7 -> 1cor.15.45); single-verse passages are
    # legitimate type nodes, so allow singles.
    for name, sides in _table_pairs(conn).items():
        type_passages = to_passages(sides["type"])
        anti_passages = to_passages(sides["antitype"])
        for tp in type_passages:
            for ap in anti_passages:
                if tp["book"] == ap["book"]:
                    continue
                if upsert(
                    conn, tp, ap, "interpretive", "typology",
                    strength=0.6, confidence=0.6,
                    metadata={"arc": name, "source": "typology_table"},
                ):
                    total += 1
        conn.commit()

    # 2. Narrative-level arcs.
    for arc in NARRATIVE_ARCS:
        if not scoped(arc["type_start"], arc["type_end"]):
            continue
        a = {"start": arc["type_start"], "end": arc["type_end"],
             "count": 1, "book": arc["type_start"].split(".")[0]}
        b = {"start": arc["antitype_start"], "end": arc["antitype_end"],
             "count": 1, "book": arc["antitype_start"].split(".")[0]}
        if upsert(
            conn, a, b, "interpretive", "typology",
            strength=0.65, confidence=0.55,
            metadata={"arc": arc["name"], "description": arc["description"],
                      "source": "narrative_arcs"},
        ):
            total += 1
    conn.commit()

    logger.info("typology: %d passage connections created", total)
    return total
