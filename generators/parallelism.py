"""Parallelism generator — connects verses through detected parallelism.

Runs the expanded parallelism detector on all books and creates
connections for each detected parallel pattern.
"""

from lib.patterns.parallelism import detect_inclusio_in_passage, detect_parallelisms


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate parallelism connections for all books."""
    count = 0
    batch = []

    # Get books to process
    query = """
        SELECT DISTINCT v.book_id, b.title
        FROM verses v JOIN books b ON b.id = v.book_id
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" WHERE v.book_id IN ({placeholders})"
    books = conn.execute(query, book_ids or []).fetchall()

    for book_row in books:
        book_id = book_row["book_id"]

        # Get all verses for this book
        verse_rows = conn.execute("""
            SELECT id, chapter, verse, text_english
            FROM verses WHERE book_id = ? AND text_english != ''
            ORDER BY chapter, verse
        """, (book_id,)).fetchall()

        if len(verse_rows) < 3:
            continue

        verses = [dict(r) for r in verse_rows]

        # Run parallelism detection
        parallelisms = detect_parallelisms(verses, context_size=1)

        for p in parallelisms:
            idx_a = p["verse_a_index"]
            idx_b = p["verse_b_index"]
            if idx_a >= len(verses) or idx_b >= len(verses):
                continue

            vid_a = verses[idx_a]["id"]
            vid_b = verses[idx_b]["id"]

            batch.append((
                vid_a, vid_b, "structural",
                p["type"], book_id, p["confidence"], p["confidence"], "algorithm",
                f'{{"evidence": "{p.get("evidence", "")[:80]}", "book": "{book_id}"}}'
            ))
            count += 1

            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []

        # Run inclusio detection (per chapter)
        chapters = {}
        for v in verses:
            ch = v["chapter"]
            if ch not in chapters:
                chapters[ch] = []
            chapters[ch].append(v)

        for _ch, ch_verses in chapters.items():
            inc = detect_inclusio_in_passage(ch_verses)
            if inc:
                idx_a = inc["verse_a_index"]
                idx_b = inc["verse_b_index"]
                if idx_a < len(ch_verses) and idx_b < len(ch_verses):
                    vid_a = ch_verses[idx_a]["id"]
                    vid_b = ch_verses[idx_b]["id"]
                    batch.append((
                        vid_a, vid_b, "structural",
                        "inclusio", book_id, 0.6, 0.6, "algorithm",
                        f'{{"overlap": {inc.get("overlap", 0.5)}, "shared": "{inc.get("shared_terms", [])[:3]}"}}'
                    ))
                    count += 1

                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Parallelism: {count} connections")
    return count
