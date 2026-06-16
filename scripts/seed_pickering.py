#!/usr/bin/env python3
"""Seed chronological/numerical patterns from Farrell & Rhonda Pickering's work.

Based on their analysis of Daniel's numbers, Isaiah's timeline, and the
moedim (appointed times) framework as presented at propheticappointments.com
and on the Latter-day Media YouTube channel.

This encodes the STRUCTURAL FRAMEWORK (dates, durations, sequences) without
reproducing their copyrighted chart artwork.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection


# Daniel 9 timeline — the 70 weeks (shevua)
# These connect Daniel's prophecy to Christ's ministry
DANIEL_TIMELINE = [
    # 70 weeks prophecy — decree to rebuild → Messiah
    ("dan.9.24", "ezra.7.11",
     "Daniel 70 weeks: The decree to rebuild (Artaxerxes to Ezra, 457 BC) starts the 70-week countdown"),
    ("dan.9.25", "nehemiah.2.1",
     "Daniel 9:25: From the decree to rebuild Jerusalem unto Messiah the Prince — 69 weeks (483 years)"),
    ("dan.9.25", "luke.3.21",
     "Daniel 9:25: Messiah's baptism/anointing in AD 27 marks the end of 69 weeks — the 'beginning of the gospel of Jesus Christ'"),
    ("dan.9.26", "matt.27.50",
     "Daniel 9:26: After 69 weeks, Messiah cut off (crucified) at the Passover, AD 30"),
    ("dan.9.27", "matt.26.28",
     "Daniel 9:27: The covenant confirmed for one week (7 years) — Christ's ministry from AD 27-34"),
    ("dan.9.27", "acts.7.58",
     "Daniel 9:27: In the midst of the week, sacrifice and oblation cease — typified by Stephen's martyrdom"),
]

# Daniel 12 — the end-time numbers
DANIEL_NUMBERS = [
    ("dan.12.7", "rev.12.14",
     "A time, times, and half a time = 1260 days/3.5 years — parallel Daniel and Revelation"),
    ("dan.12.12", "rev.11.3",
     "1335 days — Daniel's number connects to Revelation's 1260 days plus a 75-day interval"),
    ("dan.12.11", "matt.24.15",
     "1290 days from the abomination of desolation — Jesus references Daniel's number in the Olivet Discourse"),
    ("dan.12.4", "rev.22.10",
     "Sealed until the time of the end — contrast: Daniel sealed, Revelation unsealed"),
]

# Moedim (feast) connections — fall feasts as prophetic of second coming
MOEDIM_CONNECTIONS = [
    ("lev.23.24", "rev.8.1",
     "Yom Teruah (Feast of Trumpets) — the 'half hour of silence' before the trumpets of judgment"),
    ("lev.23.27", "rev.20.1",
     "Yom Kippur (Day of Atonement) — the final judgment and atonement at the end of days"),
    ("lev.23.34", "rev.21.1",
     "Feast of Tabernacles (Sukkot) — God dwelling with His people in the New Jerusalem"),
    ("lev.23.15", "acts.2.1",
     "Shavuot (Pentecost) — first fruits fulfilled in the outpouring of the Spirit"),
    ("exo.12.11", "matt.26.26",
     "Passover — fulfilled in Christ's last supper and crucifixion"),
    ("lev.23.10", "matt.28.1",
     "First Fruits — fulfilled in Christ's resurrection"),
]

# The ½ hour of silence pattern
SILENCE_PATTERN = [
    ("dan.9.27", "rev.8.1",
     "Daniel's 'midst of the week' and Revelation's 'half hour of silence' — a reversal point in the prophetic timeline"),
    ("2esdras.7.43", "rev.8.1",
     "2 Esdras 7: 'The day of judgment is the end of the age' — a 'half day' of silence precedes judgment"),
]

# 7,000-year framework (from Pickerings' Millennial Timeline)
MILLENNIAL_TIMELINE = [
    ("gen.2.2", "gen.6.1",
     "Day 1 of earth's timeline (7,000-year framework: 6 days of labor + 1 day of rest)"),
    ("gen.6.1", "gen.12.1",
     "Day 2"),  # Simplified for encoding
]


def main():
    conn = get_db()
    print("=" * 60)
    print("  Farrell & Rhonda Pickering — Prophetic Patterns")
    print("=" * 60)

    all_connections = [
        ("chronological", "prophetic_timeline", "pickering_daniel", DANIEL_TIMELINE),
        ("numerical", "sacred_number", "pickering_daniel_numbers", DANIEL_NUMBERS),
        ("chronological", "feast_connection", "pickering_moedim", MOEDIM_CONNECTIONS),
        ("structural", "chiastic", "silence_pattern", SILENCE_PATTERN),
    ]

    total = 0
    for layer, conn_type, subtype, data in all_connections:
        for source, target, note in data:
            try:
                add_connection(conn, source, target,
                              layer=layer, type_name=conn_type, subtype=subtype,
                              strength=0.5, confidence=0.4,
                              discovered_by="algorithm",
                              metadata={"source": "Pickering", "note": note[:200]})
                total += 1
            except Exception:
                pass

    conn.commit()
    chron_total = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='chronological'").fetchone()["c"]
    print(f"  Added {total} Pickering connections")
    print(f"  Chronological layer total: {chron_total}")
    conn.close()

if __name__ == "__main__":
    main()
