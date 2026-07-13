"""Genealogical generator — genealogical connections.

Connects verses through family lineage relationships:
  1. Same person mentions across the canon
  2. Genealogical formula patterns ("X begat Y", "son of")
  3. Shared genealogical context (same family tree)

Uses the entity_links/verse_entities tables for person entities
and text pattern matching for genealogical formulas.
"""

import re
from collections import defaultdict

# Person entity IDs from entity_links
# (these are the ones that actually link to verses)
PERSON_ENTITIES = {
    "adam", "eve", "noah", "abraham", "isaac", "jacob", "sarah",
    "moses", "joshua", "samuel", "david", "isaiah", "jeremiah",
    "ezekiel", "daniel", "elijah", "elisha", "john_baptist",
    "peter", "paul", "john_apostle", "jesus", "mary", "joseph",
}

# Genealogical formula patterns (English)
GENEALOGICAL_PATTERNS = [
    (r"\b(?:begat|begot|became the father of|was the father of)\b", "begat"),
    (r"\b(?:son of|daughter of|sons of|daughters of)\b", "child_of"),
    (r"\b(?:the son of|the daughter of)\b", "the_child_of"),
    (r"\b(?:genealogy|generations of|the book of the generation)\b", "genealogy_header"),
    (r"\b(?:was born|bare|gave birth|conceived)\b", "birth"),
    (r"\b(?:lineage|descendant|descendants|seed|offspring)\b", "descent"),
    (r"\b(?:elder|older|younger|firstborn|first.born)\b", "birth_order"),
]


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate genealogical connections.

    Strategy 1: Connect verses mentioning the same person entity.
    Strategy 2: Connect verses using the same genealogical formula.
    Strategy 3: Connect OT and NT genealogies for shared ancestors.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # === Strategy 1: Same person entity ===
    print("  Processing person entities...", flush=True)

    entity_filter = ",".join("?" for _ in PERSON_ENTITIES)
    person_verses = conn.execute(f"""
        SELECT ve.entity_id, ve.verse_id
        FROM verse_entities ve
        WHERE ve.entity_id IN ({entity_filter})
          AND ve.relationship_type = 'mentions'
    """, list(PERSON_ENTITIES)).fetchall()

    person_groups = defaultdict(set)
    for r in person_verses:
        person_groups[r[0]].add(r[1])

    for person, verses in person_groups.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)
        # Hub-and-spoke for very common persons (moses, david, etc.)
        if len(verse_list) > 30:
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "chronological",
                    "genealogical", f"same_person_{person}",
                    0.7, 0.75, "algorithm",
                    '{"person": "' + person + '", "relationship": "same_person"}'
                ))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
        else:
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "chronological",
                        "genealogical", f"same_person_{person}",
                        0.7, 0.75, "algorithm",
                        '{"person": "' + person + '", "relationship": "same_person"}'
                    ))
                    count += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []

    # === Strategy 2: Genealogical formula patterns ===
    print("  Scanning for genealogical formulas...", flush=True)

    formula_query = """
        SELECT id, text_english FROM verses
        WHERE text_english != ''
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        formula_query += f" AND book_id IN ({placeholders})"
    verse_texts = conn.execute(formula_query).fetchall()

    formula_groups = defaultdict(set)
    for r in verse_texts:
        text = r["text_english"] or ""
        text_lower = text.lower()
        for pattern, formula_name in GENEALOGICAL_PATTERNS:
            if re.search(pattern, text_lower):
                formula_groups[formula_name].add(r["id"])

    for formula, verses in formula_groups.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)
        # Hub-and-spoke for very common formulas ("son of")
        if len(verse_list) > 50:
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "chronological",
                    "genealogical", f"formula_{formula}",
                    0.4, 0.5, "algorithm",
                    '{"formula": "' + formula + '", "relationship": "shared_formula"}'
                ))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
        else:
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "chronological",
                        "genealogical", f"formula_{formula}",
                        0.4, 0.5, "algorithm",
                        '{"formula": "' + formula + '", "relationship": "shared_formula"}'
                    ))
                    count += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []

    # === Strategy 3: NT ↔ OT genealogy links ===
    # Connect Matt 1 / Luke 3 genealogies to their OT ancestor verses
    print("  Connecting NT↔OT genealogical links...", flush=True)
    genealogical_blocks = [
        ("matt.1.1", "matt.1.17", "Matthew's Genealogy"),
        ("luke.3.23", "luke.3.38", "Luke's Genealogy"),
        ("gen.5.1", "gen.5.32", "Adam's Genealogy"),
        ("gen.10.1", "gen.10.32", "Table of Nations"),
        ("gen.11.10", "gen.11.32", "Shem to Abram"),
        ("1chr.1.1", "1chr.9.44", "Chronicles Genealogies"),
    ]

    # Get all verses in each block
    block_verses = {}
    for start, end, name in genealogical_blocks:
        book = start.split(".")[0]
        start_ch = int(start.split(".")[1])
        start_v = int(start.split(".")[2])
        end_ch = int(end.split(".")[1])
        end_v = int(end.split(".")[2])

        rows = conn.execute("""
            SELECT id FROM verses
            WHERE book_id = ?
              AND ((chapter = ? AND verse >= ?) OR (chapter = ? AND verse <= ?))
              AND (chapter BETWEEN ? AND ?)
            ORDER BY chapter, verse
        """, (book, start_ch, start_v, end_ch, end_v, start_ch, end_ch)).fetchall()

        block_verses[name] = [r[0] for r in rows if r[0]] if rows else []

    # Connect Matthew's genealogy to OT genealogies
    nt_blocks = ["Matthew's Genealogy", "Luke's Genealogy"]
    ot_blocks = [b[2] for b in genealogical_blocks if b[2] not in nt_blocks]

    for nt_name in nt_blocks:
        nt_verses = block_verses.get(nt_name, [])
        if not nt_verses:
            continue
        nt_hub = nt_verses[0]

        for ot_name in ot_blocks:
            ot_verses = block_verses.get(ot_name, [])
            if not ot_verses:
                continue
            ot_hub = ot_verses[0]

            batch.append((
                nt_hub, ot_hub, "chronological",
                "genealogical", "nt_ot_genealogy",
                0.65, 0.7, "algorithm",
                '{"nt_genealogy": "' + nt_name + '", "ot_genealogy": "' + ot_name + '", '
                '"relationship": "genealogical_link"}'
            ))
            count += 1

            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Genealogical: {count} connections")
    return count
