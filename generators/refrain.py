"""Refrain generator — refrain connections.

A refrain is a repeated phrase at structural intervals within a book.
Detects formula markers that repeat 3+ times in the same book and
connects their verse positions, creating a network of refrain links.

Examples: "And God said" (Genesis 1), "Thus saith the LORD" (Isaiah),
"And it came to pass" (narrative books), "Woe unto" (prophetic oracles).
"""

from collections import defaultdict

from lib.db import add_connection


def run(conn, book_ids=None):
    """Generate refrain connections.

    Finds formula markers that repeat within a book and connects
    their verse positions.

    Returns count of connections created.
    """
    count = 0

    # Find repeated formula markers within each book
    query = """
        SELECT sf.book_id, sf.formula_type, sf.formula_text, sf.verse_id
        FROM structural_formulas sf
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" WHERE sf.book_id IN ({placeholders})"
    query += " ORDER BY sf.book_id, sf.formula_text, sf.verse_id"

    rows = conn.execute(query).fetchall()

    # Group by (book_id, formula_text)
    formula_groups = defaultdict(list)
    for r in rows:
        key = (r[0], r[1], r[2])
        formula_groups[key].append(r[3])

    refrain_count = 0
    for (book_id, formula_type, formula_text), verses in formula_groups.items():
        if len(verses) < 3:
            continue

        refrain_count += 1
        verse_list = sorted(verses)

        # Connect each verse to its structural neighbors (chain)
        # This preserves the sequence: verse 1 ↔ verse 2, verse 2 ↔ verse 3, etc.
        for i in range(len(verse_list) - 1):
            try:
                add_connection(conn, verse_list[i], verse_list[i + 1],
                              layer="structural",
                              type_name="refrain",
                              subtype=formula_type,
                              strength=0.5,
                              confidence=0.6,
                              discovered_by="algorithm",
                              metadata={
                                  "book": book_id,
                                  "formula": formula_text,
                                  "formula_type": formula_type,
                                  "occurrences": len(verses),
                                  "position": i + 1,
                              })
                count += 1
            except Exception:
                pass

        # Also connect first to last (inclusio of the refrain chain)
        if len(verse_list) >= 4:
            try:
                add_connection(conn, verse_list[0], verse_list[-1],
                              layer="structural",
                              type_name="refrain",
                              subtype=f"{formula_type}_inclusio",
                              strength=0.45,
                              confidence=0.5,
                              discovered_by="algorithm",
                              metadata={
                                  "book": book_id,
                                  "formula": formula_text,
                                  "formula_type": formula_type,
                                  "occurrences": len(verses),
                                  "note": "First to last occurrence of the refrain",
                              })
                count += 1
            except Exception:
                pass

    conn.commit()
    print(f"  Refrain: {count} connections from {refrain_count} refrain formulas")
    return count
