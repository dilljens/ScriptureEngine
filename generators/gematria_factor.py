"""Gematria factor generator — gematria_factor connections.

Finds words whose gematria values are exact multiples of sacred numbers
(7, 12, 40, 50, 70, 100) or divine name values (26=YHWH, 86=Elohim, etc.).

Connects all verses that contain a word with the same factor relationship.
A word whose value = 7 × 26 (e.g., 182) connects to other verses with
7-multiple words — it's factorable by BOTH a sacred number AND a divine name.
"""

from collections import defaultdict
from lib.db import add_connection


# Sacred numbers and their metadata
SACRED_FACTORS = {
    7: {"name": "seven", "description": "Sacred number 7 — completeness/divine perfection"},
    10: {"name": "ten", "description": "Sacred number 10 — trial/testimony"},
    12: {"name": "twelve", "description": "Sacred number 12 — divine government"},
    40: {"name": "forty", "description": "Sacred number 40 — testing/preparation"},
    50: {"name": "fifty", "description": "Sacred number 50 — jubilee/redemption"},
    70: {"name": "seventy", "description": "Sacred number 70 — nations/elders"},
    100: {"name": "hundred", "description": "Sacred number 100 — fullness of time"},
}

# Divine name values (from divine_names table)
# Format: value -> (name, hebrew)
DIVINE_NAME_VALUES = {
    26: ("YHWH", "יהוה"),
    86: ("Elohim", "אֱלֹהִים"),
    65: ("Adonai", "אֲדֹנָי"),
    345: ("El Shaddai", "אֵל שַׁדַּי"),
    31: ("El", "אֵל"),
}

# Combined: sacred numbers and divine name values are both valid factors
ALL_FACTORS = {}
ALL_FACTORS.update(SACRED_FACTORS)
for val, (name, hebrew) in DIVINE_NAME_VALUES.items():
    ALL_FACTORS[val] = {"name": name.lower(), "description": f"Divine name {name} ({hebrew})"}


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Connect verses through gematria factor relationships.

    For each word, checks if its value_standard is a multiple of any
    sacred number or divine name value. Groups verses by the factor
    relationship and connects them.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Get all words with their gematria values
    query = """
        SELECT g.verse_id, g.lemma, g.word_hebrew, g.value_standard
        FROM gematria g
        WHERE g.value_standard > 0
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND g.verse_id LIKE ?"

    rows = conn.execute(query).fetchall()

    # Build index: factor_key -> set of verse_ids
    # factor_key = "factor_name:multiplier" (e.g., "seven:26", "yhwh:7")
    factor_verses = defaultdict(set)
    factor_details = {}

    for r in rows:
        verse_id = r[0]
        val = r[3]

        for factor, info in ALL_FACTORS.items():
            if val >= factor and val % factor == 0:
                multiplier = val // factor
                # Only interesting: multiplier should be reasonable (1-100)
                if multiplier < 1 or multiplier > 100:
                    continue
                # Skip multiplier of 1 (the factor value itself — uninteresting)
                if multiplier == 1:
                    continue

                key = f"{info['name']}_x{multiplier}"
                factor_verses[key].add(verse_id)
                factor_details[key] = {
                    "factor": factor,
                    "factor_name": info["name"],
                    "multiplier": multiplier,
                    "description": f"Value is {multiplier} × {info['name']} ({factor})",
                }

    # Connect verses sharing the same factor relationship
    HUB_THRESHOLD = 10
    for key, verses in factor_verses.items():
        if len(verses) < 2:
            continue

        detail = factor_details[key]
        verse_list = sorted(verses)

        # Rarer factor relationships are stronger
        rarity_bonus = max(0, min(0.3, 0.3 * (1 - len(verses) / 100)))
        strength = round(0.5 + rarity_bonus, 2)

        if len(verse_list) <= HUB_THRESHOLD:
            # Full mesh for small groups
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    if verse_list[i] == verse_list[j]:
                        continue
                    batch.append((
                        verse_list[i], verse_list[j], "numerical",
                        "gematria_factor", key, strength, 0.6, "algorithm",
                        '{"factor": ' + str(detail["factor"]) + ', '
                        '"factor_name": "' + detail["factor_name"] + '", '
                        '"multiplier": ' + str(detail["multiplier"]) + '}'
                    ))
                    count += 1

                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        else:
            # Hub-and-spoke for larger groups
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "numerical",
                    "gematria_factor", key, strength, 0.6, "algorithm",
                    '{"factor": ' + str(detail["factor"]) + ', '
                    '"factor_name": "' + detail["factor_name"] + '", '
                    '"multiplier": ' + str(detail["multiplier"]) + '}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Gematria Factor: {count} connections across {len(factor_verses)} factor relationships")
    return count
