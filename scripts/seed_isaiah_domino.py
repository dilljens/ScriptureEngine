#!/usr/bin/env python3
"""Seed Isaiah's 30 Domino Events from Giliadi's framework.

The domino sequence: each event is a 4-stage cycle (A→J→R→S).
Each event overlaps with the next: event N's Salvation becomes
event N+1's Apostasy (the domino effect).

This seeds 30 events derived from the chapter-level summaries
on Giliadi's website, which map each chapter to a specific role
in the domino sequence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import add_connection, get_db

# ─── 30 Domino Events ───
# Each event: (name, A_start, J_start, R_start, S_end)
# A=Apostasy, J=Judgment, R=Restoration, S=Salvation
# Each event overlaps with the next (S of event N = A of event N+1)

DOMINO_30 = [
    # Cycle 1: Israel's Ancient Apostasy (Isa 1-12)
    ("1. Covenant Breaking",    "isa.1.1", "isa.2.1", "isa.4.1", "isa.5.30"),
    ("2. Call of Isaiah",      "isa.5.30", "isa.6.1", "isa.7.1", "isa.8.22"),
    ("3. Assyrian Threat",     "isa.8.22", "isa.9.1", "isa.10.1", "isa.12.6"),

    # Cycle 2: Nations' Humiliation (Isa 13-27)
    ("4. Babylon's Pride",     "isa.12.6", "isa.13.1", "isa.14.1", "isa.14.32"),
    ("5. Nations' Burden",     "isa.14.32", "isa.15.1", "isa.17.1", "isa.18.7"),
    ("6. Egypt's Collapse",    "isa.18.7", "isa.19.1", "isa.20.1", "isa.21.17"),
    ("7. World's Chaos",       "isa.21.17", "isa.22.1", "isa.23.1", "isa.23.18"),

    # Cycle 3: Universal Judgment (Isa 24-33)
    ("8. Earth's Destruction", "isa.23.18", "isa.24.1", "isa.25.1", "isa.26.21"),
    ("9. Ephraim's Error",     "isa.26.21", "isa.28.1", "isa.29.1", "isa.30.33"),
    ("10. Egypt's False Trust","isa.30.33", "isa.31.1", "isa.32.1", "isa.33.24"),

    # Cycle 4: World's Day of Judgment (Isa 34-40)
    ("11. Nations' Slaughter", "isa.33.24", "isa.34.1", "isa.35.1", "isa.35.10"),
    ("12. Assyria's Siege",    "isa.35.10", "isa.36.1", "isa.37.1", "isa.38.22"),
    ("13. Hezekiah's Trial",   "isa.38.22", "isa.39.1", "isa.39.1", "isa.39.8"),

    # Cycle 5: New Exodus (Isa 40-46)
    ("14. Comfort to Zion",    "isa.39.8", "isa.40.1", "isa.41.1", "isa.41.29"),
    ("15. Servant's Call",     "isa.41.29", "isa.42.1", "isa.43.1", "isa.43.28"),
    ("16. Idolatry's Folly",   "isa.43.28", "isa.44.1", "isa.45.1", "isa.46.13"),

    # Cycle 6: Babylon's Fall (Isa 47-52)
    ("17. Babylon's Humiliation","isa.46.13", "isa.47.1", "isa.48.1", "isa.48.22"),
    ("18. Servant's Mission",   "isa.48.22", "isa.49.1", "isa.50.1", "isa.50.11"),
    ("19. Zion's Awakening",    "isa.50.11", "isa.51.1", "isa.52.1", "isa.52.15"),

    # Cycle 7: Servant's Atonement (Isa 53-59)
    ("20. Servant's Suffering", "isa.52.15", "isa.53.1", "isa.54.1", "isa.54.17"),
    ("21. Covenant Invitation", "isa.54.17", "isa.55.1", "isa.56.1", "isa.57.21"),
    ("22. True Worship",        "isa.57.21", "isa.58.1", "isa.59.1", "isa.59.21"),

    # Cycle 8: Millennial Zion (Isa 60-66)
    ("23. Zion's Glory",        "isa.59.21", "isa.60.1", "isa.61.1", "isa.62.12"),
    ("24. Vengeance & Redemp.", "isa.62.12", "isa.63.1", "isa.64.1", "isa.64.12"),
    ("25. New Creation",        "isa.64.12", "isa.65.1", "isa.66.1", "isa.66.14"),
    ("26. Final Separation",    "isa.66.14", "isa.66.15", "isa.66.18", "isa.66.24"),
]

# Remaining 4 events at subtler granularity within existing cycles
DOMINO_30_EXTRA = [
    ("27. Veil of Ignorance",  "isa.24.1", "isa.25.1", "isa.26.1", "isa.27.13"),
    ("28. False Peace",        "isa.28.1", "isa.29.1", "isa.30.1", "isa.30.33"),
    ("29. Remnant's Faith",    "isa.10.1", "isa.10.5", "isa.11.1", "isa.12.6"),
    ("30. Last Day's Harvest", "isa.63.1", "isa.63.7", "isa.65.1", "isa.66.24"),
]


def seed_domino_30(conn):
    """Seed all 30 domino events with AJRS connections and chain overlaps."""
    all_events = DOMINO_30 + DOMINO_30_EXTRA
    total = 0

    for name, a_start, j_start, r_start, s_end in all_events:
        # Create the 4-stage internal connections
        stages = [
            ("apostasy", a_start, j_start),
            ("judgment", j_start, r_start),
            ("restoration", r_start, s_end),
        ]
        for stage_name, src, dst in stages:
            try:
                add_connection(conn, src, dst,
                              layer="chronological", type_name="prophetic_timeline",
                              subtype="giliadi_domino",
                              strength=0.7, confidence=0.65,
                              discovered_by="algorithm",
                              metadata={
                                  "scholar": "Avraham Gileadi",
                                  "domino_event": name,
                                  "stage": stage_name,
                                  "structure": "AJRS_30_domino",
                              })
                total += 1
            except Exception:
                pass

        # Also link A↔S (beginning to end of each event)
        try:
            add_connection(conn, a_start, s_end,
                          layer="structural", type_name="chiastic",
                          subtype="giliadi_domino",
                          strength=0.5, confidence=0.5,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "domino_event": name,
                              "structure": "event_enclosure",
                          })
            total += 1
        except Exception:
            pass

    # Chain overlaps: each event's S → next event's A
    for i in range(len(all_events) - 1):
        s_current = all_events[i][4]  # S_end
        a_next = all_events[i + 1][1]  # A_start of next
        try:
            add_connection(conn, s_current, a_next,
                          layer="chronological", type_name="prophetic_timeline",
                          subtype="giliadi_domino_chain",
                          strength=0.6, confidence=0.55,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "pattern": "30_domino_overlap",
                              "from_event": all_events[i][0],
                              "to_event": all_events[i + 1][0],
                          })
            total += 1
        except Exception:
            pass

    return total


def main():
    conn = get_db()
    print("=" * 60)
    print("  SEEDING 30 DOMINO EVENTS (Isaiah)")
    print("=" * 60)
    print(flush=True)

    # Clear previous domino connections
    conn.execute("DELETE FROM connections WHERE subtype IN ('giliadi_domino', 'giliadi_domino_chain') AND json_extract(metadata, '$.structure') LIKE '%30_domino%'")
    conn.commit()

    c = seed_domino_30(conn)
    conn.commit()
    print(f"  Seeded {c} domino connections")

    # Verify
    total = conn.execute("SELECT COUNT(*) as c FROM connections WHERE subtype IN ('giliadi_domino', 'giliadi_domino_chain')").fetchone()["c"]
    print(f"  Total domino connections in DB: {total}")

    conn.close()


if __name__ == "__main__":
    main()
