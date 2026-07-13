"""Mukdam u'Meuchar (מוקדם ומאוחר) — Non-Chronological Order Detection.

The rabbinic principle that the Torah does not always follow chronological order.
Earlier events can be narrated after later ones, and vice versa. This generator
identifies well-known cases and creates connections that flag the chronological
anomaly.
"""

import json

CASES = [
    ("gen.38.1", "gen.39.1",
     "Joseph narrative interruption",
     "Genesis 38 interrupts the Joseph story at the point where Joseph is sold into Egypt and then resumes as if no time passed. Chronologically Gen 38 spans many years. The placement is thematic rather than chronological.",
     "Midrash Rabbah, Genesis 85:1; Rashi on Gen 38:1"),
    ("gen.36.31", "1sam.8.5",
     "Kings of Edom — anachronistic",
     "Genesis 36:31 mentions kings reigning over Israel before kings actually reigned. This is a classic anachronism — a later reality mentioned in an earlier context.",
     "Rashi on Gen 36:31; Ibn Ezra"),
    ("gen.35.8", "gen.35.16",
     "Deborah's death — displaced notice",
     "Deborah Rebekah's nurse died, but the narrative is following Jacob. The notice is probably recorded here because it happened during this period, but its placement is associative rather than chronological.",
     "Sforno on Gen 35:8"),
    ("exo.6.14", "exo.6.28",
     "Genealogy interrupting call narrative",
     "Exodus 6:14-27 inserts a genealogy in the middle of Moses' call narrative, interrupting the flow. The placement demonstrates Moses' priestly lineage.",
     "Rashi on Exo 6:14; Nachmanides"),
    ("num.7.1", "num.8.1",
     "Tabernacle offerings — chronological displacement",
     "Numbers 7 describes the 12 days of tribal offerings at the dedication of the Tabernacle, which happened earlier chronologically. Placed here by thematic association.",
     "Rashi on Num 7:1; Ibn Ezra"),
    ("num.9.1", "num.10.11",
     "Second Passover — chronological marker",
     "Numbers 9:1 records the second Passover in the first month of the second year, chronologically BEFORE the census of Numbers 1:1. Placed here for thematic logic.",
     "Rashi on Num 9:1; Midrash Sifre"),
    ("lev.24.10", "lev.24.1",
     "Blasphemer narrative interrupting legal code",
     "The story of the blasphemer interrupts ritual instructions. The placement illustrates the legal principle being taught.",
     "Rashi on Lev 24:10"),
    ("deu.10.6", "num.20.25",
     "Aaron's death — prophetic prolepsis",
     "Deuteronomy 10:6 mentions Aaron's death before the actual account in Numbers 20. A proleptic summary for instructional purposes.",
     "Rashi on Deut 10:6; Talmud Yoma 5a"),
    ("jer.21.1", "jer.37.1",
     "Jeremiah's prophecies — thematic organization",
     "Jeremiah 21 begins with Zedekiah during the siege, chronologically after earlier chapters. The book is organized thematically.",
     "Talmud Pesachim 6b"),
]


def run(conn, book_ids=None):
    """Generate Mukdam u'Meuchar (non-chronological order) connections."""
    count = 0
    batch = []
    conn.execute("DELETE FROM connections WHERE subtype LIKE 'mukdam_umeuchar_%'")
    conn.commit()

    for i, (later, earlier, name, description, reference) in enumerate(CASES):
        subtype = f"mukdam_umeuchar_{i+1:02d}"
        batch.append((
            later, earlier,
            "interpretive", "rabbinic_midrash", subtype,
            0.7, 0.65, "algorithm",
            json.dumps({"chain_name": "Mukdam u'Meuchar", "case_name": name, "anomaly_type": "non_chronological", "description": description[:200], "rabbinic_reference": reference})
        ))
        count += 1
        if len(batch) >= 50:
            _batch_insert(conn, batch)
            batch = []

    if batch:
        _batch_insert(conn, batch)
    print(f"  Mukdam u'Meuchar: {count} connections")
    return count


def _batch_insert(conn, batch):
    conn.executemany("INSERT OR IGNORE INTO connections (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
    conn.commit()
