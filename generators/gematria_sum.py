"""Gematria sum relationship generator — gematria_sum_relationship connections.

Finds within-verse gematria sum relationships: Word A + Word B = Word C.
Connects verses that share the same numerical sum pattern, especially
when divine name values or sacred numbers are involved.

Two strategies:
  1. Within-verse: find triples where A + B = C in the same verse
  2. Cross-verse: connect verses whose sum patterns involve the same
     divine name or sacred number base
"""

from collections import defaultdict

# Divine name values and sacred numbers
DIVINE_VALUES = {26: "yhwh", 86: "elohim", 65: "adonai", 345: "el_shaddai", 31: "el"}
SACRED_VALUES = {7, 10, 12, 40, 50, 70, 100, 120}


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate gematria sum relationship connections.

    For each verse, finds word triples where A + B = C.
    Groups verses by their sum relationship signature and
    connects those sharing the same pattern.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Get all word gematria values per verse
    query = """
        SELECT verse_id, word_index, value_standard, word_hebrew, lemma
        FROM gematria
        WHERE value_standard > 0
    """
    if book_ids:
        ",".join("?" for _ in book_ids)
        query += " AND verse_id LIKE ?"
    query += " ORDER BY verse_id, word_index"
    rows = conn.execute(query).fetchall()

    # Group words by verse
    verse_words = defaultdict(list)
    for r in rows:
        verse_words[r[0]].append({
            "idx": r[1],
            "val": r[2],
            "word": r[3],
            "lemma": r[4],
        })

    print(f"  Scanning {len(verse_words)} Hebrew verses for sum relationships...")

    # Strategy 1: Within-verse sum relationships
    # For each verse, find pairs (A, B) where A + B equals some C in the same verse
    verse_sums = defaultdict(set)  # verse_id -> set of canonical sum signatures

    processed = 0
    for verse_id, words in verse_words.items():
        if len(words) < 3:
            continue

        values = [w["val"] for w in words if w["val"] > 0]
        if len(values) < 3:
            continue

        # Check all pair sums
        value_set = set(values)
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                pair_sum = values[i] + values[j]
                if pair_sum in value_set and pair_sum != values[i] and pair_sum != values[j]:
                    # Found a sum relationship: values[i] + values[j] = pair_sum
                    # Create a canonical signature
                    signature = tuple(sorted([values[i], values[j], pair_sum]))
                    verse_sums[verse_id].add(signature)

        processed += 1
        if processed % 2000 == 0:
            print(f"    {processed} verses scanned...", flush=True)

    print(f"  Found sum relationships in {len(verse_sums)} verses")

    # Strategy 2: Connect verses sharing the same sum signature
    # Group by signature
    sig_groups = defaultdict(set)
    for verse_id, sigs in verse_sums.items():
        for sig in sigs:
            sig_groups[sig].add(verse_id)

    for sig, verses in sig_groups.items():
        if len(verses) < 2:
            continue

        a, b, c = sig
        # Calculate strength based on how interesting the sum is
        strength = 0.5
        evidence_parts = []

        # Check if any component is a divine name value
        divine_comps = [str(v) for v in (a, b, c) if v in DIVINE_VALUES]
        if divine_comps:
            strength = min(0.75, strength + 0.15)
            evidence_parts.append("divine_name_involved")

        # Check if any component is a sacred number
        sacred_comps = [str(v) for v in (a, b, c) if v in SACRED_VALUES]
        if sacred_comps:
            strength = min(0.7, strength + 0.1)

        # Check if the sum itself is interesting
        if c in DIVINE_VALUES:
            strength = min(0.8, strength + 0.15)
            evidence_parts.append(f"sum_is_{DIVINE_VALUES[c]}")
        if c in SACRED_VALUES:
            strength = min(0.75, strength + 0.1)

        verse_list = sorted(verses)
        is_notable = bool(divine_comps or c in DIVINE_VALUES or c in SACRED_VALUES)

        # Only connect if there's some notable numerical significance
        # (otherwise the relationship is likely coincidental)
        if not is_notable:
            continue

        subtype = f"{a}_{b}_{c}"
        if len(verse_list) <= 10:
            # Full mesh for small groups
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    if verse_list[i] == verse_list[j]:
                        continue
                    batch.append((
                        verse_list[i], verse_list[j], "numerical",
                        "gematria_sum_relationship", subtype,
                        round(strength, 2), 0.5, "algorithm",
                        '{"values": [' + str(a) + ', ' + str(b) + ', ' + str(c) + '], '
                        '"sum": ' + str(c) + ', '
                        '"evidence": "' + "|".join(evidence_parts) + '"}'
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
                    "gematria_sum_relationship", subtype,
                    round(strength, 2), 0.5, "algorithm",
                    '{"values": [' + str(a) + ', ' + str(b) + ', ' + str(c) + '], '
                    '"sum": ' + str(c) + ', '
                    '"evidence": "' + "|".join(evidence_parts) + '"}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    # Strategy 3: Divine name complement relationships
    # Find word pairs where word A + divine_name_value = word B
    for _verse_id, words in verse_words.items():
        if len(words) < 2:
            continue

        values_dict = {}  # val -> list of words
        for w in words:
            v = w["val"]
            if v > 0:
                if v not in values_dict:
                    values_dict[v] = []
                values_dict[v].append(w)

        vals = sorted(values_dict.keys())
        for dv, _dv_name in DIVINE_VALUES.items():
            for v in vals:
                complement = v - dv
                if complement > 0 and complement in values_dict and complement != v:
                    # Found: word of value v = complement + divine_name_value
                    # Connect this verse to other verses with same complement relationship
                    # Canonical signature for this: (complement, dv, v)
                    sig = tuple(sorted([complement, dv, v]))
                    # We'll store this for cross-verse matching
                    # For simplicity, just record it if already found
                    pass

    if batch:
        _batch_insert(conn, batch)

    print(f"  Gematria Sum: {count} connections from {len(sig_groups)} sum patterns")
    return count
