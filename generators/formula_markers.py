"""Formula marker generator — connects verses at the same structural position.

Uses the structural_formulas table to find formula markers (toledot,
"and it came to pass", "thus says the Lord", etc.) and connects verses
that use the same formula type at the same position across different books.
"""

from collections import defaultdict
from lib.db import add_connection


def run(conn, book_ids=None):
    """Connect verses that share the same formula marker position.
    
    For each formula type, group verses by their position within that type.
    Connect verses with the same position across different books.
    Also connect sequential positions within the same book (seams).
    
    Returns count of connections created.
    """
    count = 0
    batch = []
    
    # Get all formula markers with their positions
    rows = conn.execute("""
        SELECT book_id, verse_id, formula_type, formula_text, position
        FROM structural_formulas
        ORDER BY formula_type, position
    """).fetchall()
    
    # Group by (formula_type, position)
    position_groups = defaultdict(list)
    for r in rows:
        key = (r["formula_type"], r["position"])
        position_groups[key].append(r["verse_id"])
    
    # Connect verses with the same formula at the same position
    # (e.g., toledot position 1 in Genesis, Numbers, Ruth)
    parallel_count = 0
    for (formula_type, position), verses in position_groups.items():
        if len(verses) < 2:
            continue
        
        verse_list = sorted(verses)
        for i in range(len(verse_list)):
            for j in range(i + 1, len(verse_list)):
                batch.append((
                    verse_list[i], verse_list[j], "structural",
                    "formula_marker", formula_type, 0.6, 0.8, "algorithm",
                    f'{{"formula": "{formula_type}", "position": {position}}}'
                ))
                parallel_count += 1
                
                if len(batch) >= 200:
                    conn.executemany("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    batch = []

    count += parallel_count
    
    # Also create "seam" connections — connect consecutive markers within each book
    seam_count = 0
    by_book_type = defaultdict(list)
    for r in rows:
        by_book_type[(r["book_id"], r["formula_type"])].append(r)
    
    for (book, formula_type), markers in by_book_type.items():
        sorted_markers = sorted(markers, key=lambda x: x["position"])
        for i in range(len(sorted_markers) - 1):
            batch.append((
                sorted_markers[i]["verse_id"],
                sorted_markers[i + 1]["verse_id"],
                "structural", "seam", formula_type,
                0.4, 0.7, "algorithm",
                f'{{"formula": "{formula_type}", "book": "{book}"}}'
            ))
            seam_count += 1
            
            if len(batch) >= 200:
                conn.executemany("""
                    INSERT OR IGNORE INTO connections
                        (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []
    
    count += seam_count
    
    if batch:
        conn.executemany("""
            INSERT OR IGNORE INTO connections
                (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"  Formula markers: {parallel_count} parallel + {seam_count} seam = {count} total")
    return count
