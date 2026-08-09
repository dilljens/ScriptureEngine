"""Covenant Structure — match treaty/covenant-form passages across the canon.

Ancient Near Eastern treaty form has recognizable elements: preamble,
stipulations, blessings, curses, and witnesses. This generator scores curated
covenant-form passages (Sinai, Deuteronomy, Joshua 24, Nehemiah renewal,
Jeremiah 31, Sermon on the Mount, Hebrews, Ezekiel) against those element
keyword sets, then connects passages sharing at least two elements.

This is a discovery generator (passage-level): outputs go to
passage_connections with type='covenant_structure'.
"""

import logging

from ._common import upsert

logger = logging.getLogger(__name__)

# ── Curated covenant-form passages ───────────────────────────────────
COVENANT_PASSAGES = [
    {"name": "Sinai", "start": "exo.19.1", "end": "exo.24.18"},
    {"name": "Deuteronomic", "start": "deu.4.1", "end": "deu.30.20"},
    {"name": "Joshua covenant", "start": "josh.24.1", "end": "josh.24.28"},
    {"name": "Nehemiah renewal", "start": "neh.9.1", "end": "neh.10.39"},
    {"name": "New covenant", "start": "jer.31.31", "end": "jer.31.40"},
    {"name": "Ezekiel covenant", "start": "ezek.36.24", "end": "ezek.37.14"},
    {"name": "Sermon on the Mount", "start": "matt.5.1", "end": "matt.7.29"},
    {"name": "Hebrews covenant", "start": "heb.8.1", "end": "heb.10.25"},
]

# ── Treaty elements with keyword probes ──────────────────────────────
ELEMENTS = {
    "preamble": ["i am the lord", "i am yhwh", "i am the lord your god",
                 "heard", "speak"],
    "stipulations": ["you shall", "thou shalt", "commandment", "statutes",
                     "judgments", "obey", "keep"],
    "blessings": ["bless", "blessing", "prosper", "if you obey", "good land"],
    "curses": ["curse", "cursed", "wrath", "punish", "plague", "if you do not obey", "sword"],
    "witness": ["witness", "testify", "heaven and earth", "sign"],
}


def _passage_text(conn, start, end):
    """All text_english for a verse range, space-joined, lowercased.

    Uses book/chapter/verse arithmetic, NOT id BETWEEN — verse ids are text,
    so BETWEEN is lexically wrong across multi-digit chapters (deu.4.1 is
    lexically greater than deu.30.20).
    """
    sb, sc, sv = start.split(".")
    eb, ec, ev = end.split(".")
    if sb != eb:
        return ""
    sc, ec = int(sc), int(ec)
    rows = conn.execute(
        """
        SELECT text_english FROM verses
        WHERE book_id = ? AND (
            (chapter = ? AND verse >= ?) OR
            (chapter > ? AND chapter < ?) OR
            (chapter = ? AND verse <= ?)
        )
        """,
        (sb, sc, int(sv), sc, ec, ec, int(ev)),
    ).fetchall()
    return " ".join(r["text_english"] for r in rows).lower()


def _signature(conn, passage):
    """Elements present (>= 2 keyword hits) in a passage's text."""
    text = _passage_text(conn, passage["start"], passage["end"])
    present = []
    for element, keywords in ELEMENTS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits >= 2:
            present.append(element)
    return frozenset(present)


def run(conn, book_ids=None) -> int:
    """Connect curated covenant-form passages sharing treaty elements.

    Returns the number of passage_connections created.
    """
    passages = [
        {**p, "book": p["start"].split(".")[0], "signature": None}
        for p in COVENANT_PASSAGES
    ]
    if book_ids:
        passages = [p for p in passages if p["book"] in book_ids]

    total = 0
    for p in passages:
        p["signature"] = _signature(conn, p)

    for i in range(len(passages)):
        for j in range(i + 1, len(passages)):
            a, b = passages[i], passages[j]
            if not a["signature"] or not b["signature"]:
                continue
            shared = a["signature"] & b["signature"]
            if len(shared) < 2:
                continue
            strength = min(0.4 + len(shared) * 0.15, 0.9)
            if upsert(
                conn, a, b, "interpretive", "covenant_structure",
                strength=strength, confidence=0.5,
                metadata={"shared_elements": sorted(shared),
                          "source": "covenant_structure"},
            ):
                total += 1
    conn.commit()

    logger.info("covenant_structure: %d connections created", total)
    return total
