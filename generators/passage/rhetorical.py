"""Rhetorical Analysis (dim 9).

Tags passages by rhetorical structure (judgment oracle, oracle against
nations, lament, hymn/praise, communal lament, covenant lawsuit, wisdom
instruction, discourse/teaching, farewell discourse, prophetic letter) into a
`passage_rhetoric_tags` table, then connects passages sharing a rhetorical
form (type='shared_rhetoric').

Tags are curated from standard form-critical classifications.
"""

import logging

from ._common import upsert

logger = logging.getLogger(__name__)

# ── Curated rhetorical tags (start, end, rhetoric) ───────────────────
RHETORIC_TAGS = [
    ("isa.1.1", "isa.5.30", "judgment_oracle"),
    ("isa.13.1", "isa.23.18", "oracle_against_nations"),
    ("jer.46.1", "jer.51.64", "oracle_against_nations"),
    ("ezek.25.1", "ezek.32.32", "oracle_against_nations"),
    ("psa.3.1", "psa.7.17", "lament"),
    ("psa.42.1", "psa.43.5", "lament"),
    ("lam.1.1", "lam.5.22", "communal_lament"),
    ("psa.8.1", "psa.8.9", "hymn_praise"),
    ("psa.29.1", "psa.29.11", "hymn_praise"),
    ("mic.6.1", "mic.6.16", "covenant_lawsuit"),
    ("hos.4.1", "hos.4.19", "covenant_lawsuit"),
    ("isa.1.2", "isa.1.20", "covenant_lawsuit"),
    ("prov.1.1", "prov.9.18", "wisdom_instruction"),
    ("job.3.1", "job.31.40", "lament_dialogue"),
    ("matt.5.1", "matt.7.29", "discourse_teaching"),
    ("john.13.1", "john.17.26", "farewell_discourse"),
    ("rev.2.1", "rev.3.22", "prophetic_letter"),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS passage_rhetoric_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    rhetoric TEXT NOT NULL,
    confidence REAL DEFAULT 0.55,
    UNIQUE(start_verse, end_verse, rhetoric)
)
"""


def _ensure_table(conn):
    conn.execute(_SCHEMA)


def run(conn, book_ids=None) -> int:
    """Tag passages and connect passages sharing a rhetorical form.

    Returns the number of passage_connections created.
    """
    _ensure_table(conn)
    tagged = []
    total = 0

    for start, end, rhetoric in RHETORIC_TAGS:
        book = start.split(".")[0]
        if book_ids and book not in book_ids:
            continue
        conn.execute(
            """
            INSERT INTO passage_rhetoric_tags (start_verse, end_verse, rhetoric)
            VALUES (?, ?, ?)
            ON CONFLICT(start_verse, end_verse, rhetoric) DO NOTHING
            """,
            (start, end, rhetoric),
        )
        tagged.append({"start": start, "end": end, "book": book, "rhetoric": rhetoric})

    for i in range(len(tagged)):
        for j in range(i + 1, len(tagged)):
            a, b = tagged[i], tagged[j]
            if a["rhetoric"] != b["rhetoric"]:
                continue
            if a["book"] == b["book"]:
                continue
            if upsert(
                conn, a, b, "interpretive", "shared_rhetoric",
                strength=0.5, confidence=0.55,
                metadata={"rhetoric": a["rhetoric"], "source": "rhetorical"},
            ):
                total += 1
    conn.commit()

    logger.info("rhetorical: %d connections created", total)
    return total
