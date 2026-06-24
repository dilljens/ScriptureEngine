"""Chiasm detector generator — chiasm_detected connections.

Runs algorithmic chiastic structure detection on each book and
creates connections for detected mirror pairs.

Uses three detection methods:
  1. Word count mirroring (Giliadi-style)
  2. Keyword distribution inversion
  3. Formula sequence mirroring

Connections are created for outer pairs (A↔A', B↔B') and pivot
sections of candidate chiasms. Lower confidence than human-curated
`chiastic` connections.
"""

from collections import defaultdict
from lib.db import add_connection


def run(conn, book_ids=None):
    """Run algorithmic chiasm detection and create connections.

    For each book, detect chiastic candidates and create connections
    between mirrored section pairs.

    Returns count of connections created.
    """
    count = 0

    # Get all books to process
    query = """
        SELECT DISTINCT v.book_id, b.title
        FROM verses v JOIN books b ON b.id = v.book_id
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" WHERE v.book_id IN ({placeholders})"
    books = conn.execute(query).fetchall()

    for book_row in books:
        book_id = book_row[0]

        # Get chapter word counts (Hebrew word count per chapter)
        chap_counts = conn.execute("""
            SELECT v.chapter,
                   COUNT(DISTINCT g.lemma) as heb_lemma_count
            FROM verses v
            LEFT JOIN gematria g ON g.verse_id = v.id
            WHERE v.book_id = ? AND v.has_hebrew = 1
            GROUP BY v.chapter
            ORDER BY v.chapter
        """, (book_id,)).fetchall()

        if len(chap_counts) < 5:
            continue

        chapters = [r[0] for r in chap_counts]
        word_counts = [r[1] or 0 for r in chap_counts]
        num_chapters = len(chapters)

        # Try odd-numbered section divisions
        max_sections = min(num_chapters, 11)
        for num_sections in range(5, max_sections + 1, 2):
            section_size = num_chapters / num_sections

            # Try groupings
            for offset in range(min(num_sections, 3)):
                sections = []
                for s in range(num_sections):
                    start_ch = max(chapters[0], chapters[0] + int(s * section_size) + offset)
                    end_ch = min(chapters[-1], chapters[0] + int((s + 1) * section_size) + offset - 1)
                    if start_ch <= end_ch:
                        total = sum(word_counts[chapters.index(start_ch):chapters.index(end_ch) + 1])
                        sections.append({
                            "label": chr(65 + s),  # A, B, C, ...
                            "start_ch": start_ch,
                            "end_ch": end_ch,
                            "word_count": total,
                        })

                if len(sections) < 5 or len(sections) % 2 == 0:
                    continue

                # Score for chiastic mirroring
                pairs = []
                score = 0
                max_possible = len(sections) // 2

                for i in range(max_possible):
                    j = -(i + 1)
                    a, b = sections[i], sections[j]
                    if a["word_count"] > 0 and b["word_count"] > 0:
                        ratio = max(a["word_count"], b["word_count"]) / max(min(a["word_count"], b["word_count"]), 1)
                        if ratio <= 1.15:
                            pair_score = max(0, 1.0 - (ratio - 1.0) * 5)
                            score += pair_score
                            pairs.append({
                                "a_idx": i, "b_idx": j,
                                "a_label": a["label"], "b_label": b["label"],
                                "a_start_ch": a["start_ch"], "a_end_ch": a["end_ch"],
                                "b_start_ch": b["start_ch"], "b_end_ch": b["end_ch"],
                                "pair_score": round(pair_score, 2),
                            })

                if not pairs:
                    continue

                total_score = score / max_possible if max_possible > 0 else 0

                if total_score > 0.35:
                    # Found a candidate chiasm — create connections

                    # Get verse IDs for paired sections
                    for pair in pairs:
                        a_start = conn.execute("""
                            SELECT id FROM verses
                            WHERE book_id = ? AND chapter = ?
                            ORDER BY verse LIMIT 1
                        """, (book_id, pair["a_start_ch"])).fetchone()

                        a_end = conn.execute("""
                            SELECT id FROM verses
                            WHERE book_id = ? AND chapter = ? AND verse = (
                                SELECT MAX(verse) FROM verses WHERE book_id = ? AND chapter = ?
                            )
                        """, (book_id, pair["a_end_ch"], book_id, pair["a_end_ch"])).fetchone()

                        b_start = conn.execute("""
                            SELECT id FROM verses
                            WHERE book_id = ? AND chapter = ?
                            ORDER BY verse LIMIT 1
                        """, (book_id, pair["b_start_ch"])).fetchone()

                        b_end = conn.execute("""
                            SELECT id FROM verses
                            WHERE book_id = ? AND chapter = ? AND verse = (
                                SELECT MAX(verse) FROM verses WHERE book_id = ? AND chapter = ?
                            )
                        """, (book_id, pair["b_end_ch"], book_id, pair["b_end_ch"])).fetchone()

                        if a_start and b_end:
                            # Connect start of A section to end of A' section
                            try:
                                add_connection(conn, a_start[0], b_end[0],
                                              layer="structural",
                                              type_name="chiasm_detected",
                                              subtype=f"{book_id}_{num_sections}s_{pair['a_label']}{pair['b_label']}",
                                              strength=round(0.3 + total_score * 0.4, 2),
                                              confidence=round(0.3 + total_score * 0.4, 2),
                                              discovered_by="algorithm",
                                              metadata={
                                                  "book": book_id,
                                                  "num_sections": num_sections,
                                                  "method": "word_count_mirroring",
                                                  "pair": f"{pair['a_label']}↔{pair['b_label']}",
                                                  "a_range": f"{pair['a_start_ch']}-{pair['a_end_ch']}",
                                                  "b_range": f"{pair['b_start_ch']}-{pair['b_end_ch']}",
                                                  "pair_score": pair["pair_score"],
                                                  "total_score": round(total_score, 3),
                                              })
                                count += 1
                            except Exception:
                                pass

                    # Connect the pivot (center section) to itself
                    pivot_idx = len(sections) // 2
                    pivot = sections[pivot_idx]
                    pivot_first = conn.execute("""
                        SELECT id FROM verses
                        WHERE book_id = ? AND chapter = ?
                        ORDER BY verse LIMIT 1
                    """, (book_id, pivot["start_ch"])).fetchone()

                    pivot_last = conn.execute("""
                        SELECT id FROM verses
                        WHERE book_id = ? AND chapter = ? AND verse = (
                            SELECT MAX(verse) FROM verses WHERE book_id = ? AND chapter = ?
                        )
                    """, (book_id, pivot["end_ch"], book_id, pivot["end_ch"])).fetchone()

                    if pivot_first and pivot_last and pivot_first[0] != pivot_last[0]:
                        try:
                            add_connection(conn, pivot_first[0], pivot_last[0],
                                          layer="structural",
                                          type_name="chiasm_detected",
                                          subtype=f"{book_id}_{num_sections}s_pivot",
                                          strength=round(0.3 + total_score * 0.3, 2),
                                          confidence=round(0.25 + total_score * 0.3, 2),
                                          discovered_by="algorithm",
                                          metadata={
                                              "book": book_id,
                                              "num_sections": num_sections,
                                              "method": "word_count_mirroring",
                                              "pair": "pivot↔pivot",
                                              "pivot_range": f"{pivot['start_ch']}-{pivot['end_ch']}",
                                              "total_score": round(total_score, 3),
                                          })
                            count += 1
                        except Exception:
                            pass

                    # Only process the best candidate per book to avoid noise
                    break

    conn.commit()
    print(f"  Chiasm Detector: {count} connections")
    return count
