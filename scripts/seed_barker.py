#!/usr/bin/env python3
"""Seed interpretive connections from Margaret Barker's Temple Theology."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection

INTERPRETATIONS = [
    # Divine Council — angels as sons of God
    ("job.1.6", "psa.82.1", "jewish", "rabbinic_midrash",
     "Barker: The divine council (sons of God presenting themselves before YHWH) is the original temple theology — a heavenly court mirroring the earthly temple"),
    ("psa.82.6", "john.10.34", "jewish", "rabbinic_midrash",
     "Barker: Jesus quotes Psalm 82 'Ye are gods' to argue that divine sonship is inherent in the original covenant — theosis was temple theology"),
    ("1kgs.22.19", "isa.6.1", "jewish", "rabbinic_midrash",
     "Barker: Micaiah's vision of the heavenly council and Isaiah's temple vision are the same theology — YHWH as Divine King surrounded by his heavenly court"),

    # The Lady Wisdom
    ("prov.8.22", "john.1.1", "jewish", "rabbinic_midrash",
     "Barker: Wisdom (Hokhmah) was a distinct divine being in First Temple theology — 'created at the beginning' parallels John's Logos theology"),
    ("prov.8.30", "col.1.15", "patristic", "patristic_reading",
     "Barker: Wisdom as the 'master workman' at creation corresponds to Paul's Christ as 'firstborn of every creature' — early Christian Wisdom Christology"),

    # The Second God / Angel of YHWH
    ("exo.23.21", "gen.16.7", "jewish", "rabbinic_midrash",
     "Barker: The angel in whom YHWH's name dwells (Ex 23) is the 'lesser YHWH' — same figure as the Angel of the Lord who speaks as God"),
    ("exo.23.21", "mal.3.1", "jewish", "rabbinic_midrash",
     "Barker: The 'messenger of the covenant' in Malachi is the same Divine Angel — 'the Lord whom ye seek shall suddenly come to his temple'"),
    ("dan.7.13", "rev.1.13", "patristic", "patristic_reading",
     "Barker: Daniel's 'Son of Man' coming with clouds is the same figure as Revelation's Son of Man — the Divine Angel who receives dominion"),

    # Temple as microcosm
    ("exo.25.9", "heb.9.24", "jewish", "rabbinic_midrash",
     "Barker: The tabernacle was 'the pattern of things in the heavens' — the earthly temple was a microcosm of the heavenly temple, and temple rituals re-enacted cosmic events"),
    ("gen.1.1", "exo.25.40", "jewish", "rabbinic_midrash",
     "Barker: The seven days of creation correspond to the seven-branched lampstand — the temple was a model of the created order"),
    ("isa.66.1", "acts.7.49", "patristic", "patristic_reading",
     "Barker: Stephen's quotation of Isaiah 66 — 'Heaven is my throne, earth is my footstool' — reflects the temple-cosmos identification"),

    # Day of Atonement
    ("lev.16.1", "heb.9.7", "jewish", "rabbinic_midrash",
     "Barker: The Day of Atonement was the central ritual of First Temple theology — the high priest entering the Holy of Holies is the type of Christ entering heaven"),
    ("lev.16.8", "rev.20.2", "jewish", "rabbinic_midrash",
     "Barker: The two goats — one for YHWH, one for Azazel — represent the two powers in heaven. Azazel, originally a divine being, becomes Satan in later tradition"),
    ("lev.16.14", "1jn.2.1", "patristic", "patristic_reading",
     "Barker: The blood sprinkled on the mercy seat — Christ as our Advocate (Paraclete) with the Father is the heavenly Day of Atonement"),

    # Melchizedek Priesthood
    ("gen.14.18", "heb.7.1", "jewish", "rabbinic_midrash",
     "Barker: Melchizedek as 'priest of El Elyon (God Most High)' represents the pre-Levitical, original priesthood — the order of the Son of God"),
    ("psa.110.4", "heb.7.17", "jewish", "rabbinic_midrash",
     "Barker: 'Thou art a priest forever after the order of Melchizedek' — this is not a new order but the restoration of the original temple priesthood"),
    ("exo.19.6", "1pet.2.9", "jewish", "rabbinic_midrash",
     "Barker: 'A kingdom of priests' — the original covenant envisioned all Israel as priests. The Levitical priesthood was a later restriction"),

    # Josiah's Reform — suppression of temple theology
    ("2kgs.23.1", "jer.1.1", "critical", "critical_scholarship",
     "Barker: Josiah's reform (621 BC) suppressed the temple theology — destroyed the symbols (Nehushtan, Asherah, etc.) and centralized worship. Jeremiah began his ministry during this period"),
    ("2kgs.23.4", "deu.12.1", "critical", "critical_scholarship",
     "Barker: Deuteronomy was the lawbook found in the temple — it reflects the reform's theology: one sanctuary, no divine council, no Asherah. This shaped the Second Temple religion"),
    ("2kgs.23.15", "1kgs.12.28", "critical", "critical_scholarship",
     "Barker: Jeroboam's golden calves were not 'idols' in a pagan sense but were associated with the cherubim throne — Josiah's destruction of Bethel removed this tradition"),

    # Theosis / becoming divine
    ("2pet.1.4", "psa.82.6", "patristic", "patristic_reading",
     "Barker: 'Partakers of the divine nature' (2 Pet 1:4) and 'Ye are gods' (Ps 82:6) reflect the temple theology of theosis — humans can become divine through covenant"),
    ("john.10.34", "psa.82.6", "patristic", "patristic_reading",
     "Barker: Jesus' use of Psalm 82 at John 10:34 is the key text for early Christian theosis — 'if he called them gods unto whom the word of God came'"),
    ("rom.8.29", "1jn.3.2", "patristic", "patristic_reading",
     "Barker: 'Conformed to the image of his Son' and 'we shall be like him' represent theosis — becoming part of the divine family through Christ"),

    # Enochic tradition and the Watchers
    ("gen.6.1", "jude.1.6", "jewish", "rabbinic_midrash",
     "Barker: The 'sons of God' taking wives from 'daughters of men' — 1 Enoch expands this into the Watcher tradition, which is essential background for Jude and 2 Peter"),
    ("gen.6.4", "1pet.3.19", "patristic", "patristic_reading",
     "Barker: 'Spirits in prison' (1 Pet 3:19) refers to the imprisoned Watchers of Enochic tradition — Christ preaching to them in the spirit is part of this temple theology"),
]

INTERP_TYPES = {
    "jewish": "rabbinic_midrash",
    "patristic": "patristic_reading",
    "critical": "critical_scholarship",
}

def main():
    conn = get_db()
    print("=" * 60)
    print("  Margaret Barker — Temple Theology")
    print("=" * 60)
    
    count = 0
    for source, target, tradition, typ, note in INTERPRETATIONS:
        try:
            add_connection(conn, source, target, layer="interpretive",
                          type_name=INTERP_TYPES.get(tradition, "rabbinic_midrash"),
                          subtype="barker_temple_theology", strength=0.55, confidence=0.45,
                          discovered_by="algorithm",
                          metadata={"tradition": tradition, "note": note[:200],
                                   "scholar": "Margaret Barker", "source": "Temple Theology"})
            count += 1
        except Exception:
            pass
    
    conn.commit()
    interp_total = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='interpretive'").fetchone()["c"]
    print(f"  Added {count} Barker connections")
    print(f"  Interpretive layer total: {interp_total}")
    conn.close()

if __name__ == "__main__":
    main()
