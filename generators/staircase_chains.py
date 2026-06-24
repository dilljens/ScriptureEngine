"""Staircase chain generator — detects and groups staircase (climactic) parallelism.

Staircase (climactic) parallelism is a multi-verse structure where:
1. Each verse builds on the previous, repeating a word/phrase while adding info
2. Verses progressively escalate in length or intensity
3. The sequence builds toward a climax

Two detection methods:
  Method A — Chain existing `parallel_step` connections (from parallelism generator)
  Method B — Direct text scan: consecutive verses with word repetition + length escalation

Chains are stored in the `patterns` table with pattern_type = 'staircase_chain'.
"""

import json
import re
from collections import defaultdict

# Words too common to count as staircase repetition
STOP_WORDS = {
    "and", "the", "for", "but", "yet", "not", "all", "are",
    "was", "were", "have", "has", "had", "did", "his", "her",
    "their", "our", "your", "its", "that", "this", "with",
    "from", "they", "them", "unto", "upon", "thou", "thy",
    "thee", "than", "then", "which", "what", "when", "where",
    "shall", "will", "would", "could", "should", "may", "might",
    "there", "here", "come", "came", "made", "make", "said",
    "also", "very", "every", "into",
}


def _tokenize(text):
    """Tokenize text into lowercase word set."""
    return set(re.findall(r"[a-zA-Z\u0590-\u05FF']+", text.lower()))


def _tokens_list(text):
    """Tokenize text into lowercase word list (preserving order)."""
    return re.findall(r"[a-zA-Z\u0590-\u05FF']+", text.lower())


def _get_verse_ref(conn, verse_id):
    """Get book.chapter.verse reference for a verse ID."""
    row = conn.execute("""
        SELECT book_id, chapter, verse FROM verses WHERE id = ?
    """, (verse_id,)).fetchone()
    if row:
        return f"{row['book_id']}.{row['chapter']}.{row['verse']}"
    return verse_id


def _detect_staircase_chains(verses, min_chain=3, max_chain=8):
    """Detect staircase chains from verse text.

    Looks for sequences of consecutive verses where:
    - Adjacent verses share significant words (word repetition)
    - Verses progressively increase in length (escalation)
    - The sequence has a building/climactic feel

    Args:
        verses: list of dicts with 'id', 'text_english', 'verse' keys
        min_chain: minimum verses in a chain (3 = one pair)
        max_chain: maximum verses to check in one chain

    Returns: list of chain dicts with verses, repeated_words, avg_overlap, length_escalation
    """
    if len(verses) < min_chain:
        return []

    chains = []

    for start in range(len(verses) - min_chain + 1):
        for end in range(start + min_chain, min(start + max_chain, len(verses)) + 1):
            segment = verses[start:end]
            texts = [v.get("text_english", "") for v in segment]

            # Check each adjacent pair
            overlaps = []
            length_ratios = []
            all_shared = set()

            for i in range(len(texts) - 1):
                t_a = _tokenize(texts[i])
                t_b = _tokenize(texts[i + 1])
                if not t_a or not t_b:
                    overlaps.append(0)
                    length_ratios.append(0)
                    continue

                # Word overlap (Jaccard)
                overlap = len(t_a & t_b) / max(len(t_a | t_b), 1)
                overlaps.append(overlap)

                # Track shared words across adjacent pairs
                shared = t_a & t_b
                meaningful = {w for w in shared if len(w) > 3 and w not in STOP_WORDS}
                all_shared.update(meaningful)

                # Length ratio (longer / shorter)
                len_a = len(_tokens_list(texts[i]))
                len_b = len(_tokens_list(texts[i + 1]))
                ratio = max(len_a, len_b) / max(min(len_a, len_b), 1)
                length_ratios.append(ratio)

            # Score the chain:
            # - Average word overlap > 0.1 (meaningful repetition)
            # - At least one pair shows escalation (ratio > 1.3)
            # - At least one meaningful shared word across adjacent pairs

            avg_overlap = sum(overlaps) / max(len(overlaps), 1)
            any_escalation = any(r > 1.3 for r in length_ratios)
            has_shared = len(all_shared) > 0

            if avg_overlap > 0.08 and any_escalation and len(all_shared) >= 2:
                # Calculate confidence based on strength of signals
                overlap_score = min(avg_overlap / 0.3, 1.0) * 0.4
                escalation_score = min(max(length_ratios) / 2.0, 1.0) * 0.3
                length_score = min(len(segment) / 5.0, 1.0) * 0.3
                confidence = round(overlap_score + escalation_score + length_score, 2)

                chains.append({
                    "verses": [v["id"] for v in segment],
                    "verse_numbers": [v["verse"] for v in segment],
                    "repeated_words": sorted(all_shared),
                    "avg_overlap": round(avg_overlap, 3),
                    "max_length_ratio": round(max(length_ratios), 2),
                    "confidence": confidence,
                })

                # Don't extend this start further (move to next start)
                break

    return chains


def run(conn, book_ids=None):
    """Generate staircase chain patterns.

    Uses two methods:
      A — Chain existing parallel_step connections
      B — Direct text scan for staircase patterns

    Args:
        conn: Database connection
        book_ids: Optional list of book IDs to filter by

    Returns: Count of chains + connections created.
    """
    chain_count = 0

    # ── Method A: Chain existing parallel_step connections ──

    query = """
        SELECT c.source_verse, c.target_verse, c.confidence
        FROM connections c
        JOIN verses v1 ON c.source_verse = v1.id
        WHERE c.type = 'parallel_step'
    """
    params = []
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND v1.book_id IN ({placeholders})"
        params.extend(book_ids)
    query += " ORDER BY v1.book_id, v1.chapter, v1.verse"

    step_rows = conn.execute(query, params).fetchall()

    book_step = defaultdict(list)
    for r in step_rows:
        src_info = conn.execute(
            "SELECT book_id FROM verses WHERE id = ?", (r["source_verse"],)
        ).fetchone()
        if src_info:
            book_step[src_info["book_id"]].append({
                "source": r["source_verse"],
                "target": r["target_verse"],
                "confidence": r["confidence"],
            })

    for book_id, conns in book_step.items():
        forward = {c["source"]: c["target"] for c in conns}
        all_sources = set(c["source"] for c in conns)
        all_targets = set(c["target"] for c in conns)
        starters = all_sources - all_targets
        if not starters and all_sources:
            starters = {next(iter(all_sources))}

        used = set()
        for starter in starters:
            chain = []
            current = starter
            while current in forward and current not in used:
                used.add(current)
                chain.append(current)
                nxt = forward[current]
                if nxt in used:
                    chain.append(nxt)
                    break
                chain.append(nxt)
                used.add(nxt)
                current = nxt
                if current not in forward:
                    break

            if len(chain) >= 3:
                chain_conns = [c for c in conns if c["source"] in chain or c["target"] in chain]
                avg_conf = sum(c["confidence"] for c in chain_conns) / max(len(chain_conns), 1)
                start_ref = _get_verse_ref(conn, chain[0])
                end_ref = _get_verse_ref(conn, chain[-1])

                metadata = {
                    "method": "parallel_step_chaining",
                    "verse_refs": [_get_verse_ref(conn, v) for v in chain],
                    "chain_length": len(chain),
                    "avg_confidence": round(avg_conf, 2),
                }

                existing = conn.execute("""
                    SELECT id FROM patterns
                    WHERE pattern_type = 'staircase_chain'
                    AND book_id = ? AND start_verse = ? AND end_verse = ?
                """, (book_id, start_ref, end_ref)).fetchone()

                if not existing:
                    conn.execute("""
                        INSERT INTO patterns
                            (book_id, start_verse, end_verse, pattern_type,
                             description, confidence, discovered_by, metadata)
                        VALUES (?, ?, ?, 'staircase_chain',
                                ?, ?, 'algorithm', ?)
                    """, (
                        book_id, start_ref, end_ref,
                        f"Staircase chain of {len(chain)} verses from parallel_step links",
                        round(avg_conf, 2),
                        json.dumps(metadata),
                    ))
                    chain_count += 1

    # ── Method B: Direct text scan for staircase patterns ──

    books_query = """
        SELECT DISTINCT v.book_id, b.title
        FROM verses v JOIN books b ON b.id = v.book_id
    """
    book_params = []
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        books_query += f" WHERE v.book_id IN ({placeholders})"
        book_params.extend(book_ids)

    books = conn.execute(books_query, book_params).fetchall()

    for book_row in books:
        book_id = book_row["book_id"]

        # Get all verses ordered by chapter, verse
        verse_rows = conn.execute("""
            SELECT id, book_id, chapter, verse, text_english
            FROM verses
            WHERE book_id = ? AND text_english != ''
            ORDER BY chapter, verse
        """, (book_id,)).fetchall()

        if len(verse_rows) < 3:
            continue

        verses = [dict(r) for r in verse_rows]

        # Group by chapter (staircase chains are within chapters)
        chapters = defaultdict(list)
        for v in verses:
            chapters[v["chapter"]].append(v)

        for chapter_num, ch_verses in chapters.items():
            if len(ch_verses) < 3:
                continue

            raw_chains = _detect_staircase_chains(ch_verses)

            # Deduplicate: greedy non-overlapping selection by confidence
            raw_chains.sort(key=lambda c: c["confidence"], reverse=True)
            covered = set()
            chains = []
            for c in raw_chains:
                vset = set(c["verse_numbers"])
                if not vset & covered:  # No overlap with already-selected chains
                    chains.append(c)
                    covered.update(vset)

            for chain in chains:
                start_ref = _get_verse_ref(conn, chain["verses"][0])
                end_ref = _get_verse_ref(conn, chain["verses"][-1])

                metadata = {
                    "method": "text_scan",
                    "chapter": chapter_num,
                    "verse_numbers": chain["verse_numbers"],
                    "verse_refs": [_get_verse_ref(conn, v) for v in chain["verses"]],
                    "chain_verses": chain["verses"],
                    "repeated_words": chain["repeated_words"],
                    "chain_length": len(chain["verses"]),
                    "avg_overlap": chain["avg_overlap"],
                    "max_length_ratio": chain["max_length_ratio"],
                }

                # Check for existing
                existing = conn.execute("""
                    SELECT id FROM patterns
                    WHERE pattern_type = 'staircase_chain'
                    AND book_id = ? AND start_verse = ? AND end_verse = ?
                """, (book_id, start_ref, end_ref)).fetchone()

                if not existing:
                    conn.execute("""
                        INSERT INTO patterns
                            (book_id, start_verse, end_verse, pattern_type,
                             description, confidence, discovered_by, metadata)
                        VALUES (?, ?, ?, 'staircase_chain',
                                ?, ?, 'algorithm', ?)
                    """, (
                        book_id, start_ref, end_ref,
                        f"Staircase chain of {len(chain['verses'])} verses in {book_id}.{chapter_num}",
                        chain["confidence"],
                        json.dumps(metadata),
                    ))
                    chain_count += 1

    conn.commit()
    print(f"  Staircase Chains: {chain_count} chains created")
    return chain_count
