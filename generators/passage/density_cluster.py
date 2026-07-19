"""
Density Cluster Detector — find passage pairs with high connection density.

Scans existing verse-level connections and identifies verse ranges where
a significant fraction of verses connect to another range. When density
exceeds threshold, creates a passage_connection record.

Algorithm:
  1. Slide a window across each book (default 10 verses, step 5)
  2. For each window, count connections to every other book's windows
  3. If density > threshold (default 0.5), create a passage_connection
  4. Merge adjacent windows targeting the same destination into larger passages

Uses existing connections table — no new data needed.
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Default parameters
DEFAULT_WINDOW = 10      # verses per sliding window
DEFAULT_STEP = 5         # verse overlap between windows
DEFAULT_DENSITY = 0.4    # min fraction of verses with connections to target
MIN_PASSAGE_SIZE = 5     # minimum verses for a passage connection


def run(conn, book_ids=None) -> int:
    """Find passage-level clusters from verse-level connections.

    Args:
        conn: SQLite connection
        book_ids: Optional list of book IDs to process (None = all)

    Returns count of passage_connections created.
    """
    all_connections = _load_connections(conn, book_ids)
    if not all_connections:
        logger.info("density_cluster: no connections loaded")
        return 0

    # Build verse-level connection map: (book, chapter) -> {target_book -> set of verses}
    connection_map = _build_connection_map(all_connections)
    if not connection_map:
        return 0

    # Get all verses per book for sliding window
    verse_list_by_book = _get_verse_list(conn, book_ids)

    # Find clusters
    clusters = _find_clusters(connection_map, verse_list_by_book)
    if not clusters:
        logger.info("density_cluster: no clusters found")
        return 0

    # Merge adjacent clusters and write to DB
    merged = _merge_clusters(clusters)
    count = _write_passage_connections(conn, merged)

    logger.info("density_cluster: %d passage connections created (from %d clusters)", count, len(merged))
    return count


def _load_connections(conn, book_ids=None):
    """Load all verse-level connections into memory."""
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT c.source_verse, c.target_verse, c.layer, c.type, c.strength, c.confidence
            FROM connections c
            WHERE SUBSTR(c.source_verse, 1, INSTR(c.source_verse, '.') - 1) IN ({placeholders})
               OR SUBSTR(c.target_verse, 1, INSTR(target_verse, '.') - 1) IN ({placeholders})
        """, book_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT c.source_verse, c.target_verse, c.layer, c.type, c.strength, c.confidence
            FROM connections c
        """).fetchall()

    return [dict(r) for r in rows]


def _build_connection_map(connections):
    """Build a map: (source_book, source_chapter) -> {target_book: set(source_verses)}.

    Tracks which verses in a (book, chapter) connect to which target book.
    """
    conn_map = defaultdict(lambda: defaultdict(set))

    for c in connections:
        try:
            src_parts = c["source_verse"].split(".")
            tgt_parts = c["target_verse"].split(".")
            if len(src_parts) < 3 or len(tgt_parts) < 3:
                continue
            src_book = src_parts[0]
            src_ch = int(src_parts[1])
            src_v = int(src_parts[2])
            tgt_book = tgt_parts[0]

            key = (src_book, src_ch)
            conn_map[key][tgt_book].add(src_v)
        except (ValueError, IndexError):
            continue

    return conn_map


def _get_verse_list(conn, book_ids=None):
    """Get all verses organized by book: {book: [(chapter, verse), ...]}."""
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT id FROM verses
            WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) IN ({placeholders})
            ORDER BY id
        """, book_ids).fetchall()
    else:
        rows = conn.execute("SELECT id FROM verses ORDER BY id").fetchall()

    by_book = defaultdict(list)
    for r in rows:
        parts = r["id"].split(".")
        if len(parts) >= 3:
            by_book[parts[0]].append((int(parts[1]), int(parts[2])))

    return dict(by_book)


def _find_clusters(connection_map, verse_list_by_book):
    """Find passage clusters using sliding window."""
    clusters = []

    for src_book, verses in verse_list_by_book.items():
        verses.sort()
        book_chapters = defaultdict(list)
        for ch, v in verses:
            book_chapters[ch].append(v)

        # Determine the verse range per chapter
        chapter_verses = {}
        for ch in sorted(book_chapters.keys()):
            vs = book_chapters[ch]
            chapter_verses[ch] = {"min": min(vs), "max": max(vs), "count": len(vs)}

        # Build a flat list of (book, chapter, verse_num) for sliding window
        flat = []
        for ch in sorted(chapter_verses.keys()):
            for v in range(chapter_verses[ch]["min"], chapter_verses[ch]["max"] + 1):
                flat.append((src_book, ch, v))

        if len(flat) < DEFAULT_WINDOW:
            continue

        # Sliding window
        for i in range(0, len(flat) - DEFAULT_WINDOW + 1, DEFAULT_STEP):
            window = flat[i:i + DEFAULT_WINDOW]
            src_start = window[0]
            src_end = window[-1]

            # Count connections from this window to each target book
            target_verse_counts = defaultdict(set)
            for (bk, ch, v) in window:
                key = (bk, ch)
                if key in connection_map:
                    for tgt_book, verses in connection_map[key].items():
                        if v in verses:
                            target_verse_counts[tgt_book].add(v)

            # Calculate density per target book
            win_size = len(window)
            for tgt_book, verses in target_verse_counts.items():
                density = len(verses) / win_size
                if density >= DEFAULT_DENSITY and len(verses) >= MIN_PASSAGE_SIZE:
                    clusters.append({
                        "source_book": src_book,
                        "source_start_chapter": src_start[1],
                        "source_start_verse": src_start[2],
                        "source_end_chapter": src_end[1],
                        "source_end_verse": src_end[2],
                        "target_book": tgt_book,
                        "verse_count": len(verses),
                        "density": round(density, 3),
                    })

    return clusters


def _merge_clusters(clusters):
    """Merge adjacent windows targeting the same source into larger passages."""
    if not clusters:
        return []

    # Group by (source_book, target_book) and sort by position
    by_pair = defaultdict(list)
    for c in clusters:
        key = (c["source_book"], c["target_book"])
        by_pair[key].append(c)

    merged = []
    for key, clist in by_pair.items():
        clist.sort(key=lambda x: (x["source_start_chapter"], x["source_start_verse"]))

        current = dict(clist[0])
        for c in clist[1:]:
            # Check if adjacent (step <= DEFAULT_STEP)
            prev_end = (current["source_end_chapter"], current["source_end_verse"])
            this_start = (c["source_start_chapter"], c["source_start_verse"])
            adjacent = (
                (this_start[0] == prev_end[0] and abs(this_start[1] - prev_end[1]) <= DEFAULT_STEP * 2)
                or (this_start[0] == prev_end[0] + 1)
            )
            if adjacent and c["target_book"] == current["target_book"]:
                current["source_end_chapter"] = c["source_end_chapter"]
                current["source_end_verse"] = c["source_end_verse"]
                current["verse_count"] = max(current["verse_count"], c["verse_count"])
                current["density"] = round((current["density"] + c["density"]) / 2, 3)
            else:
                if current["source_start_chapter"] < current["source_end_chapter"] or \
                   current["source_start_verse"] < current["source_end_verse"]:
                    merged.append(current)
                current = dict(c)
        merged.append(current)

    return merged


def _write_passage_connections(conn, clusters):
    """Write passage connection records to the database."""
    count = 0
    for c in clusters:
        source_start = f"{c['source_book']}.{c['source_start_chapter']}.{c['source_start_verse']}"
        source_end = f"{c['source_book']}.{c['source_end_chapter']}.{c['source_end_verse']}"

        # Find target window — simplest approach: use first chapter of target book
        target_start = f"{c['target_book']}.1.1"
        target_end = _get_last_verse_of_book(conn, c['target_book'])

        metadata = json.dumps({
            "verse_count": c["verse_count"],
            "density": c["density"],
            "source": "density_cluster",
        })

        try:
            conn.execute("""
                INSERT INTO passage_connections
                    (source_start, source_end, target_start, target_end, layer, type,
                     strength, confidence, discovered_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_start, source_end, target_start, target_end, layer, type, subtype)
                DO NOTHING
            """, (
                source_start, source_end,
                target_start, target_end,
                "intertextual", "pericope_parallel",
                c["density"], min(c["density"] + 0.2, 1.0),
                "algorithm", metadata,
            ))
            count += 1
        except Exception as e:
            logger.warning("density_cluster: insert error: %s", e)

    conn.commit()
    return count


def _get_last_verse_of_book(conn, book_id):
    """Get the last verse ID for a book (e.g. 'mal.4.6')."""
    row = conn.execute("""
        SELECT id FROM verses
        WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ?
        ORDER BY id DESC LIMIT 1
    """, (book_id,)).fetchone()
    return row["id"] if row else f"{book_id}.1.1"
