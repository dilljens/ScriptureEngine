"""Hendiadys generator — hendiadys connections.

Hendiadys: two words joined by "and" expressing a single complex idea
(e.g., "good and pleasant", "knowledge and wisdom", "tokens and wonders").

Uses a seed list of known biblical hendiadys pairs and scans English text
for coordinated X-and-Y patterns where both words exist in the same verse.
"""

import re
from collections import defaultdict

# Known biblical hendiadys pairs (from biblical scholarship)
# Format: (word_a, word_b) — normalized lowercase
KNOWN_HENDIADYS = [
    # Psalm/poetic hendiadys
    ("good", "pleasant"),        # Psalm 133:1
    ("knowledge", "wisdom"),     # Common wisdom pair
    ("counsel", "understanding"), # Common wisdom pair
    ("glory", "honour"),         # Psalm 8:5
    ("power", "might"),          # Common pair
    ("grace", "truth"),          # John 1:17
    (" mercy", "truth"),         # Common OT pair (chesed ve'emet)
    ("steadfast love", "faithfulness"),  # Same concept
    ("joy", "gladness"),         # Common pair
    ("weeping", "mourning"),     # Common pair
    ("tokens", "wonders"),       # OT signs formula
    ("signs", "wonders"),        # NT signs formula
    ("signs", "portents"),       # Apocalyptic pair
    ("wonders", "signs"),        # Reversed order
    ("wonders", "portents"),     # Apocalyptic pair
    ("righteousness", "justice"),  # Common prophetic pair
    ("judgment", "justice"),     # Common pair
    ("peace", "safety"),         # Common pair
    ("blessing", "prosperity"),  # Common pair
    ("glory", "beauty"),         # Common pair
    ("holiness", "righteousness"), # Common pair
    ("gentiles", "peoples"),     # Common NT pair
    ("nations", "peoples"),      # Common pair
    ("adversity", "distress"),   # Common lament pair
    ("trouble", "sorrow"),       # Common lament pair
    ("affliction", "anguish"),   # Common lament pair
    ("joy", "rejoicing"),        # Common pair
    ("song", "melody"),          # Psalm pair
    ("fear", "dread"),           # Common pair
    ("desire", "delight"),       # Common pair
    ("shame", "disgrace"),       # Common prophetic pair
    ("reproach", "disgrace"),    # Common prophetic pair
    ("gladness", "joy"),         # Common pair
    ("rejoicing", "joy"),        # Common pair
    ("love", "kindness"),        # Common OT pair (hesed)
]

# Also detect potential hendiadys patterns from co-occurrence data
# We look for "A and B" where A and B share the same part of speech
PATTERN = re.compile(r'\b(' + '|'.join(
    re.escape(a.strip()) + r'\s+and\s+' + re.escape(b.strip())
    for a, b in KNOWN_HENDIADYS
) + r')\b', re.IGNORECASE)

# Also detect reversed order
PATTERN_REVERSED = re.compile(r'\b(' + '|'.join(
    re.escape(b.strip()) + r'\s+and\s+' + re.escape(a.strip())
    for a, b in KNOWN_HENDIADYS
) + r')\b', re.IGNORECASE)


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate hendiadys connections.

    For each known hendiadys pair, find all verses containing it,
    then connect verses sharing the same pair.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Get all English verse text
    query = """
        SELECT id, text_english FROM verses
        WHERE text_english != ''
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND book_id IN ({placeholders})"
    rows = conn.execute(query).fetchall()

    print(f"  Scanning {len(rows)} verses for hendiadys patterns...", flush=True)

    # Build hendiadys->verses index
    hendiadys_verses = defaultdict(set)
    for r in rows:
        verse_id = r[0]
        text = r["text_english"] or ""
        text_lower = text.lower()

        # Check forward patterns
        abd = PATTERN.findall(text_lower)
        for _match in abd:
            # Need to figure out which hendiadys pair this matches
            for a, b in KNOWN_HENDIADYS:
                pattern = a.strip() + " and " + b.strip()
                if pattern in text_lower:
                    hendiadys_verses[f"{a.strip()}_{b.strip()}"].add(verse_id)
                    break

        # Check reversed patterns
        revd = PATTERN_REVERSED.findall(text_lower)
        for _match in revd:
            for b, a in KNOWN_HENDIADYS:
                pattern = b.strip() + " and " + a.strip()
                if pattern in text_lower:
                    hendiadys_verses[f"{a.strip()}_{b.strip()}"].add(verse_id)
                    break

    # Connect verses sharing the same hendiadys pair
    for pair_key, verses in hendiadys_verses.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)
        pair_display = pair_key.replace("_", " and ")

        if len(verse_list) <= 10:
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "linguistic",
                        "hendiadys", pair_key,
                        0.55, 0.5, "algorithm",
                        '{"pair": "' + pair_display + '", "hendiadys_type": "known"}'
                    ))
                    count += 1

                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        else:
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "linguistic",
                    "hendiadys", pair_key,
                    0.55, 0.5, "algorithm",
                    '{"pair": "' + pair_display + '", "hendiadys_type": "known"}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Hendiadys: {count} connections across {len(hendiadys_verses)} pairs")
    return count
