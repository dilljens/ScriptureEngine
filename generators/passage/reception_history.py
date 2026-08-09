"""Reception History (dim 10).

Links passages through interpretive tradition. Passages that multiple
interpretive traditions engage (visible in the `interpretive_disagreements`
table — verses with recorded disagreement across traditions) are clustered
into passage ranges and connected to each other (type='shared_reception'),
with scholar provenance from the connections graph folded into metadata.

Uses only data already in the engine (interpretive_disagreements + connection
provenance) — no new ingests. Confidence is low (0.45): shared engagement is
reception evidence, not an interpretive claim.
"""

import logging
from collections import defaultdict

from ._common import to_passages, upsert

logger = logging.getLogger(__name__)


def _engaged_verses(conn):
    """{verse_id: disagreement_count} from interpretive_disagreements."""
    counts = defaultdict(int)
    try:
        rows = conn.execute(
            "SELECT verse_id, COUNT(*) AS n FROM interpretive_disagreements GROUP BY verse_id"
        ).fetchall()
    except Exception as e:  # pragma: no cover - table missing
        logger.warning("interpretive_disagreements unavailable: %s", e)
        return counts
    for r in rows:
        counts[r["verse_id"]] = r["n"]
    return counts


def _scholar_count(conn, verse_id):
    """Distinct scholar provenance tags on a verse's connections."""
    try:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT discovered_by) AS n FROM connections
            WHERE (source_verse = ? OR target_verse = ?)
              AND discovered_by IS NOT NULL AND discovered_by != 'algorithm'
            """,
            (verse_id, verse_id),
        ).fetchone()
        return row["n"] if row else 0
    except Exception:  # pragma: no cover
        return 0


def run(conn, book_ids=None) -> int:
    """Connect tradition-engaged passages across the canon.

    Returns the number of passage_connections created.
    """
    engaged = _engaged_verses(conn)
    if not engaged:
        return 0

    # Any verse with recorded interpretive disagreement is a reception node;
    # single disputed verses are meaningful (e.g. isa.1.2 with 98 signals).
    verses = list(engaged)
    if book_ids:
        verses = [v for v in verses if v.split(".")[0] in book_ids]

    passages = to_passages(verses)
    total = 0
    for i in range(len(passages)):
        for j in range(i + 1, len(passages)):
            a, b = passages[i], passages[j]
            if a["book"] == b["book"]:
                continue
            scholars = _scholar_count(conn, a["start"]) + _scholar_count(conn, b["start"])
            if upsert(
                conn, a, b, "interpretive", "shared_reception",
                strength=min(0.4 + min(a["count"], b["count"]) * 0.03, 0.7),
                confidence=0.45,
                metadata={"tradition_signals": scholars, "source": "reception_history"},
            ):
                total += 1
    conn.commit()

    logger.info("reception_history: %d connections created", total)
    return total
