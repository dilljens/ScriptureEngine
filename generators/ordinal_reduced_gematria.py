"""Ordinal and Reduced gematria generator.

Same algorithm as same_gematria_standard, but using ordinal and reduced
value systems. Connects verses sharing matching gematria values in
these alternative systems.
"""

from collections import defaultdict
from lib.db import add_connection


def run(conn, book_ids=None):
    """Connect verses sharing same ordinal or reduced gematria values.
    
    For each value that appears in 2-15 verses, connect all verses
    that share that value.
    
    Returns count of connections created.
    """
    count = 0
    
    # ── Ordinal Gematria ──
    count += _process_value_system(conn, "same_gematria_ordinal", "value_ordinal", max_verses=15)
    
    # ── Reduced Gematria ──
    # Reduced values are 1-9 (high collision, each in 15k+ verses).
    # Instead of full-group matching (pointless for 9 buckets),
    # connect verses where a word's reduced value matches the
    # reduced value of a divine name — meaningful word-level link.
    count += _process_reduced_via_divine_names(conn, "same_gematria_reduced", "value_reduced")
    
    return count


def _process_value_system(conn, conn_type, value_column, max_verses=15, hub_threshold=None):
    """Process one value system: find shared values and create connections.
    
    Args:
        conn: Database connection
        conn_type: Connection type string (e.g. 'same_gematria_ordinal')
        value_column: Column name in gematria table
        max_verses: Maximum verses for a value to be considered rare
        hub_threshold: If set, use hub-and-spoke for groups > this size (None = always full mesh)
    """
    count = 0
    batch = []
    
    rows = conn.execute(f"""
        SELECT g.{value_column} as val, g.verse_id
        FROM gematria g
        WHERE g.{value_column} > 0
    """).fetchall()
    
    # Group verses by value
    value_groups = defaultdict(set)
    for r in rows:
        val = r["val"]
        if 1 <= val <= 999:  # Skip values that are too large/common
            value_groups[val].add(r["verse_id"])
    
    processed = 0
    for val, verses in value_groups.items():
        size = len(verses)
        if size < 2 or size > max_verses:
            continue
        
        processed += 1
        verse_list = sorted(verses)
        strength = min(0.8, 0.3 + 0.05 * (max_verses - size))
        
        if hub_threshold is not None and len(verse_list) > hub_threshold:
            # Hub-and-spoke for larger groups
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "numerical",
                    conn_type, str(val), strength, 0.5, "algorithm",
                    f'{{"value": {val}, "system": "{conn_type}", "verse_count": {size}}}'
                ))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
        else:
            # Full mesh for smaller groups
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "numerical",
                        conn_type, str(val), strength, 0.6, "algorithm",
                        f'{{"value": {val}, "system": "{conn_type}", "verse_count": {size}}}'
                    ))
                    count += 1
                    
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        
        if processed % 500 == 0:
            print(f"    {conn_type}: {processed} values processed...", flush=True)
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  {conn_type}: {count} connections from {processed} value groups")
    return count


def _reduce_to_digit(n):
    """Reduce a number to a single digit (gematria reduction)."""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def _process_reduced_via_divine_names(conn, conn_type, value_column):
    """For reduced gematria: connect verses where a word's reduced value
    matches a divine name's reduced value. This is more meaningful than
    connecting all 16k verses sharing reduced=5."""
    count = 0
    batch = []

    # Get divine names and compute their true reduced values from standard
    divine = conn.execute("""
        SELECT name, hebrew, value_standard
        FROM divine_names
        WHERE value_standard > 0
    """).fetchall()

    if not divine:
        return 0

    # Map reduced value -> list of divine name info
    dn_reduced = {}
    for r in divine:
        # The divine_names table stores standard gematria in value_reduced column.
        # Compute true reduced: sum digits until single digit.
        val = _reduce_to_digit(r["value_standard"])
        if val not in dn_reduced:
            dn_reduced[val] = []
        dn_reduced[val].append({"name": r["name"], "hebrew": r["hebrew"]})

    # For each divine name reduced value, find verses containing a word
    # with that reduced value AND where the word itself is noteworthy
    # (not a function word). Create connections between verses that
    # share the same divine-name-reduced-value match.
    for target_val, names in dn_reduced.items():
        verses = conn.execute(f"""
            SELECT DISTINCT g.verse_id
            FROM gematria g
            WHERE g.{value_column} = ?
              AND g.morph NOT LIKE 'HR%'   -- Skip prepositions
              AND g.morph NOT LIKE 'HC%'   -- Skip conjunctions
              AND g.morph NOT LIKE 'HT%'   -- Skip particles
              AND g.morph != ''
            ORDER BY g.verse_id
        """, (target_val,)).fetchall()

        verse_ids = [v[0] for v in verses]
        if len(verse_ids) < 2:
            continue

        names_str = "/".join(n["name"] for n in names)

        # Hub-and-spoke
        hub = verse_ids[0]
        for v in verse_ids[1:]:
            batch.append((
                hub, v, "numerical",
                conn_type, f"divine_{target_val}",
                0.55, 0.5, "algorithm",
                f'{{"reduced_value": {target_val}, '
                f'"divine_names": "{names_str}", '
                f'"system": "same_gematria_reduced"}}'
            ))
            count += 1

            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  {conn_type}: {count} connections from {len(dn_reduced)} divine name reduced values")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
