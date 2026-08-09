"""Social Setting / Sitz im Leben (dim 8).

Tags passages with their social setting (patriarchal nomadic, wilderness
wandering, monarchy court, temple cultic, wisdom school, prophetic court,
exile/diaspora, restoration community, synagogue/Greco-Roman, persecuted
church) into a `passage_social_tags` table, then connects passages sharing a
setting (type='shared_setting').

Tags are curated book/era-level attributions; confidence is kept low (0.45)
since social setting is a reconstruction.
"""

import logging

from ._common import upsert

logger = logging.getLogger(__name__)

# ── Curated social settings (start, end, setting) ────────────────────
# Each setting has 2+ passages across books so same-setting connections fire.
SOCIAL_TAGS = [
    ("gen.12.1", "gen.50.26", "patriarchal_nomadic"),
    ("heb.11.8", "heb.11.19", "patriarchal_nomadic"),
    ("exo.1.1", "deu.34.12", "wilderness_wandering"),
    ("psa.78.1", "psa.78.72", "wilderness_wandering"),
    ("matt.4.1", "matt.4.11", "wilderness_wandering"),
    ("josh.1.1", "judg.21.25", "conquest_settlement"),
    ("ruth.1.1", "ruth.4.22", "conquest_settlement"),
    ("1sam.1.1", "1kgs.11.43", "monarchy_court"),
    ("2chr.10.1", "2chr.36.23", "monarchy_court"),
    ("psa.1.1", "psa.150.6", "temple_cultic"),
    ("1chr.16.1", "1chr.16.43", "temple_cultic"),
    ("2chr.5.1", "2chr.7.22", "temple_cultic"),
    ("prov.1.1", "eccl.12.14", "wisdom_school"),
    ("job.1.1", "job.42.17", "wisdom_school"),
    ("song.1.1", "song.8.14", "wisdom_school"),
    ("isa.1.1", "mal.4.6", "prophetic_court"),
    ("ezek.1.1", "dan.12.13", "exile_diaspora"),
    ("psa.137.1", "psa.137.9", "exile_diaspora"),
    ("lam.1.1", "lam.5.22", "exile_diaspora"),
    ("neh.1.1", "neh.13.31", "restoration_community"),
    ("ezra.1.1", "ezra.10.44", "restoration_community"),
    ("hag.1.1", "hag.2.23", "restoration_community"),
    ("matt.1.1", "acts.28.31", "synagogue_greco_roman"),
    ("rom.1.1", "rom.16.27", "synagogue_greco_roman"),
    ("1cor.1.1", "1cor.16.24", "synagogue_greco_roman"),
    ("rev.1.1", "rev.22.21", "persecuted_church"),
    ("1pet.1.1", "1pet.5.14", "persecuted_church"),
    ("2tim.1.1", "2tim.4.22", "persecuted_church"),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS passage_social_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    setting TEXT NOT NULL,
    confidence REAL DEFAULT 0.45,
    UNIQUE(start_verse, end_verse, setting)
)
"""


def _ensure_table(conn):
    conn.execute(_SCHEMA)


def run(conn, book_ids=None) -> int:
    """Tag passages and connect passages sharing a social setting.

    Returns the number of passage_connections created.
    """
    _ensure_table(conn)
    tagged = []
    total = 0

    for start, end, setting in SOCIAL_TAGS:
        book = start.split(".")[0]
        if book_ids and book not in book_ids:
            continue
        conn.execute(
            """
            INSERT INTO passage_social_tags (start_verse, end_verse, setting)
            VALUES (?, ?, ?)
            ON CONFLICT(start_verse, end_verse, setting) DO NOTHING
            """,
            (start, end, setting),
        )
        tagged.append({"start": start, "end": end, "book": book, "setting": setting})

    for i in range(len(tagged)):
        for j in range(i + 1, len(tagged)):
            a, b = tagged[i], tagged[j]
            if a["setting"] != b["setting"]:
                continue
            if a["book"] == b["book"]:
                continue
            if upsert(
                conn, a, b, "interpretive", "shared_setting",
                strength=0.45, confidence=0.45,
                metadata={"setting": a["setting"], "source": "social_setting"},
            ):
                total += 1
    conn.commit()

    logger.info("social_setting: %d connections created", total)
    return total
