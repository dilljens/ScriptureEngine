"""
Chiastic Structure Promoter — elevates verse-level chiastic pairs to passage-level.

The known_chiasms table contains chiastic structures with start_verse, end_verse,
and layers_json listing the paired sections (A↔A', B↔B', etc.). This generator:

1. Reads known chiasms from the known_chiasms table
2. For each chiasm with labeled parallel sections, creates passage-level connections
3. Records the chiastic center (pivot) as connection metadata
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def run(conn, book_ids=None) -> int:
    """Promote chiastic structures to passage-level connections."""
    chiasms = _load_chiasms(conn, book_ids)
    if not chiasms:
        return 0

    count = _process_chiasms(conn, chiasms)
    logger.info("chiastic_promoter: %d passage connections created from %d chiasms", count, len(chiasms))
    return count


def _load_chiasms(conn, book_ids=None):
    """Load known chiasms from the database."""
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT * FROM known_chiasms
            WHERE book_id IN ({placeholders})
            ORDER BY book_id, start_verse
        """, book_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM known_chiasms
            ORDER BY book_id, start_verse
        """).fetchall()
    return [dict(r) for r in rows]


def _parse_layers(layers_json):
    """Parse the layers_json field into chiastic section labels."""
    if not layers_json:
        return []
    try:
        layers = json.loads(layers_json) if isinstance(layers_json, str) else layers_json
        if isinstance(layers, list):
            return layers
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _process_chiasms(conn, chiasms):
    """Create passage-level connections from chiastic sections."""
    count = 0

    for chiasm in chiasms:
        book_id = chiasm["book_id"]
        start = chiasm["start_verse"]
        end_verse = chiasm.get("end_verse", "")
        pivot = chiasm.get("pivot_verse", "")
        scholar = chiasm.get("scholar", "unknown")
        chiasm_type = chiasm.get("chiasm_type", "")
        confidence = chiasm.get("confidence", 0.7)

        if not end_verse:
            continue

        layers = _parse_layers(chiasm.get("layers_json", "[]"))

        if layers:
            # Has labeled sections — create A↔A', B↔B' connections
            seen = set()
            for section in layers:
                label = section.get("label", "").strip()
                s_start = section.get("start", "")
                s_end = section.get("end", "")

                if not label or not s_start or not s_end:
                    continue

                # Find matching pair (A matches A', B matches B', etc.)
                base_label = label.rstrip("'")
                pair_label = base_label + "'" if not label.endswith("'") else base_label

                if label in seen or pair_label in seen:
                    continue

                # Find the paired section
                pair = None
                for other in layers:
                    if other.get("label", "").strip() == pair_label:
                        pair = other
                        break

                if pair:
                    seen.add(label)
                    seen.add(pair_label)

                    metadata = json.dumps({
                        "chiastic_label": label,
                        "chiastic_pair": pair_label,
                        "scholar": scholar,
                        "chiasm_type": chiasm_type,
                        "pivot_verse": pivot,
                        "source": "chiastic_promoter",
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
                            s_start, s_end,
                            pair.get("start", ""), pair.get("end", ""),
                            "structural", "macro_chiastic",
                            0.8, confidence,
                            scholar, metadata,
                        ))
                        count += 1
                    except Exception as e:
                        logger.warning("chiastic_promoter: insert error: %s", e)
        else:
            # No labeled sections — create a single passage-level record for the whole chiasm
            metadata = json.dumps({
                "chiasm_type": chiasm_type,
                "scholar": scholar,
                "pivot_verse": pivot,
                "source": "chiastic_promoter",
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
                    start, end_verse, start, end_verse,
                    "structural", "macro_chiastic",
                    0.7, confidence, scholar, metadata,
                ))
                count += 1
            except Exception as e:
                logger.warning("chiastic_promoter: insert error: %s", e)

    conn.commit()
    return count
