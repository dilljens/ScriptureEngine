"""Source / Critical Layers (dim 6).

Tags passages with their critical source attribution (J/E/D/P, Deutero/Trito
Isaiah, Psalms books, Deuteronomistic History, apocalyptic corpora) into a
`passage_source_tags` table, then connects passages sharing a source label
(type='shared_source').

Tags are curated scholarly consensus attributions — no LLM, no new ingests.
"""

import logging

from ._common import upsert

logger = logging.getLogger(__name__)

# ── Curated source attributions (start, end, source_label, note) ─────
# Book/chapter-level consensus attributions. Contested cases are excluded.
SOURCE_TAGS = [
    ("gen.1.1", "gen.2.3", "P (Priestly)", "creation account"),
    ("gen.2.4", "gen.3.24", "J (Yahwist)", "garden narrative"),
    ("gen.12.1", "gen.25.18", "J/E (Abraham cycle)", "patriarchal narrative"),
    ("exo.2.1", "exo.4.31", "E (Elohist)", "Moses call"),
    ("exo.25.1", "lev.27.34", "P (Priestly)", "cultic legislation"),
    ("deu.1.1", "deu.34.12", "D (Deuteronomist)", "deuteronomic code"),
    ("josh.1.1", "josh.24.33", "Deuteronomistic History", "conquest"),
    ("judg.1.1", "judg.21.25", "Deuteronomistic History", "judges cycle"),
    ("1sam.1.1", "2kgs.25.30", "Deuteronomistic History", "monarchy narrative"),
    ("isa.1.1", "isa.39.8", "Isaiah 1-39", "proto-isaiah"),
    ("isa.40.1", "isa.55.13", "Deutero-Isaiah", "second isaiah"),
    ("isa.56.1", "isa.66.24", "Trito-Isaiah", "third isaiah"),
    ("psa.1.1", "psa.41.13", "Psalms Book I", "davidic collection"),
    ("psa.42.1", "psa.72.20", "Psalms Book II", "korah/asaph collection"),
    ("psa.73.1", "psa.89.52", "Psalms Book III", "asaph collection"),
    ("psa.90.1", "psa.106.48", "Psalms Book IV", "mosaic collection"),
    ("psa.107.1", "psa.150.6", "Psalms Book V", "hallel collection"),
    ("prov.1.1", "prov.9.18", "Wisdom instruction", "sapiential"),
    ("dan.1.1", "dan.12.13", "Apocalyptic", "daniel apocalypse"),
    ("rev.1.1", "rev.22.21", "Apocalyptic", "john apocalypse"),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS passage_source_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    source_label TEXT NOT NULL,
    note TEXT DEFAULT '',
    confidence REAL DEFAULT 0.7,
    UNIQUE(start_verse, end_verse, source_label)
)
"""


def _ensure_table(conn):
    conn.execute(_SCHEMA)


def run(conn, book_ids=None) -> int:
    """Tag passages and connect passages sharing a source attribution.

    Returns the number of passage_connections created.
    """
    _ensure_table(conn)
    tagged = []  # {"start", "end", "book", "label"}
    total = 0

    for start, end, label, note in SOURCE_TAGS:
        book = start.split(".")[0]
        if book_ids and book not in book_ids:
            continue
        conn.execute(
            """
            INSERT INTO passage_source_tags (start_verse, end_verse, source_label, note)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(start_verse, end_verse, source_label) DO NOTHING
            """,
            (start, end, label, note),
        )
        tagged.append({"start": start, "end": end, "book": book, "label": label})

    for i in range(len(tagged)):
        for j in range(i + 1, len(tagged)):
            a, b = tagged[i], tagged[j]
            if a["label"] != b["label"]:
                continue
            if a["book"] == b["book"]:
                continue
            if upsert(
                conn, a, b, "interpretive", "shared_source",
                strength=0.55, confidence=0.7,
                metadata={"source_label": a["label"], "source": "source_layers"},
            ):
                total += 1
    conn.commit()

    logger.info("source_layers: %d connections created", total)
    return total
