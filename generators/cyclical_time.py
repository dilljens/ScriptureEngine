"""Cyclical time generator — sabbatical_cycle + jubilee_cycle connections.

Connects events that fall in the same sabbatical (7-year) or jubilee (50-year)
cycle, based on approximate biblical chronology (Ussher/LXX tradition).

The chronology is approximate and notes that fact explicitly — these
connections are suggestive rather than definitive. Low confidence (0.35-0.45).
"""

from collections import defaultdict
from lib.db import add_connection


# Major biblical events with approximate BC dates (Ussher-LXX based)
# Format: (verse_id, event_name, approx_bc_date)
# Dates are from the existing TIMELINE_EVENTS in chronological.py
TIMELINE = [
    # Primeval
    ("gen.1.1", "Creation", 4004),
    ("gen.3.1", "The Fall", 4003),
    ("gen.4.1", "Cain and Abel", 4002),
    ("gen.5.1", "Genealogy from Adam", 4000),
    ("gen.6.9", "Noah and the Flood", 2348),
    ("gen.11.1", "Tower of Babel", 2242),

    # Patriarchs
    ("gen.12.1", "Abraham's Call", 1921),
    ("gen.17.1", "Abrahamic Covenant", 1897),
    ("gen.22.1", "Sacrifice of Isaac", 1872),
    ("gen.25.19", "Isaac's Family", 1856),
    ("gen.28.1", "Jacob's Journey", 1760),
    ("gen.37.1", "Joseph Sold", 1728),
    ("gen.41.1", "Joseph in Egypt", 1715),
    ("gen.50.1", "Death of Joseph", 1635),

    # Exodus
    ("exo.1.1", "Oppression in Egypt", 1571),
    ("exo.12.1", "The Exodus", 1491),
    ("exo.19.1", "Law at Sinai", 1491),
    ("exo.25.1", "Tabernacle Built", 1490),
    ("num.10.11", "Wilderness Journey", 1490),
    ("deu.34.1", "Death of Moses", 1451),

    # Conquest & Judges
    ("josh.1.1", "Conquest of Canaan", 1451),
    ("josh.14.1", "Division of Land", 1444),
    ("judg.1.1", "Period of Judges", 1400),
    ("ruth.1.1", "Ruth", 1150),

    # United Monarchy
    ("1sam.9.1", "Saul Becomes King", 1095),
    ("2sam.1.1", "David's Reign", 1055),
    ("1kgs.2.12", "Solomon's Reign", 1015),
    ("1kgs.6.1", "Temple Built", 1012),

    # Divided Monarchy
    ("1kgs.12.1", "Divided Kingdom", 975),
    ("1kgs.17.1", "Elijah's Ministry", 910),
    ("2kgs.2.19", "Elisha's Ministry", 895),
    ("isa.1.1", "Isaiah's Ministry", 740),
    ("jer.1.1", "Jeremiah's Ministry", 626),
    ("2kgs.24.1", "Judah's Captivity", 605),
    ("ezek.1.1", "Ezekiel's Ministry", 592),

    # Return from Exile
    ("ezra.1.1", "Return from Exile", 536),
    ("ezra.3.1", "Temple Rebuilt", 516),
    ("neh.1.1", "Nehemiah & Wall", 445),
    ("mal.1.1", "Malachi's Ministry", 430),

    # NT
    ("matt.1.1", "Birth of Jesus", 4),  # 4 BC
    ("matt.3.1", "John the Baptist", 26),  # AD 26 = -26 BC
    ("matt.4.1", "Jesus' Ministry", 27),
    ("matt.27.1", "Crucifixion", 30),
    ("matt.28.1", "Resurrection", 30),
    ("acts.2.1", "Day of Pentecost", 30),
    ("acts.9.1", "Paul's Conversion", 35),
    ("acts.13.1", "Paul's Journeys", 45),
    ("acts.15.1", "Jerusalem Council", 50),
    ("rev.1.1", "John on Patmos", 95),
]

# For BC dates: negative = BC, positive = AD
# For sabbatical cycle calculation:
#   Cycle year = (date - reference_year) % 7
#   where reference_year is a known sabbatical year

# Known sabbatical year in biblical chronology:
# 445 BC (Nehemiah) is traditionally a sabbatical year
# So reference = -445 (or 445 BC)
SABBATICAL_REFERENCE = -445

# Jubilee cycle: every 50 years
# Reference jubilee: 445 BC is also a jubilee year in some traditions
JUBILEE_REFERENCE = -445


def run(conn, book_ids=None):
    """Generate sabbatical cycle and jubilee cycle connections.

    Assigns approximate dates to major biblical events, calculates
    which sabbatical/jubilee cycle year they fall in, and connects
    events sharing the same cycle.

    Low confidence (0.35-0.45) — the dating is approximate.

    Returns count of connections created.
    """
    count = 0

    # Filter by book_ids if provided
    if book_ids:
        filtered = [(v, n, d) for v, n, d in TIMELINE if v.split(".")[0] in book_ids]
    else:
        filtered = TIMELINE

    if not filtered:
        return 0

    # Calculate cycle year for each event
    sabbatical_groups = defaultdict(list)
    jubilee_groups = defaultdict(list)

    for verse_id, event_name, bc_date in filtered:
        # For sabbatical: cycle year 1-7
        years_since_ref = bc_date - SABBATICAL_REFERENCE
        sabb_cycle = ((years_since_ref % 7) + 7) % 7  # 0-6
        sabb_year = sabb_cycle + 1  # 1-7

        # For jubilee: cycle number (year 1-50)
        years_since_jub = bc_date - JUBILEE_REFERENCE
        jub_cycle = ((years_since_jub % 50) + 50) % 50
        jub_year = jub_cycle + 1  # 1-50

        sabbatical_groups[sabb_year].append((verse_id, event_name, bc_date))
        jubilee_groups[jub_year].append((verse_id, event_name, bc_date))

    # Create connections within each sabbatical cycle year
    for cycle_year, events in sabbatical_groups.items():
        if len(events) < 2:
            continue

        events.sort(key=lambda x: x[2])
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                try:
                    add_connection(conn, events[i][0], events[j][0],
                                  layer="chronological",
                                  type_name="sabbatical_cycle",
                                  subtype=f"cycle_year_{cycle_year}",
                                  strength=0.35,
                                  confidence=0.35,
                                  discovered_by="algorithm",
                                  metadata={
                                      "cycle_year": cycle_year,
                                      "cycle_type": "sabbatical",
                                      "note": f"Both occur in sabbatical cycle year {cycle_year} "
                                              f"(Ussher-LXX chronology, approximate)",
                                      "event_a": events[i][1],
                                      "event_b": events[j][1],
                                      "date_a": events[i][2],
                                      "date_b": events[j][2],
                                  })
                    count += 1
                except Exception:
                    pass

    # Create connections within each jubilee cycle year
    for cycle_year, events in jubilee_groups.items():
        if len(events) < 2:
            continue

        events.sort(key=lambda x: x[2])
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                try:
                    add_connection(conn, events[i][0], events[j][0],
                                  layer="chronological",
                                  type_name="jubilee_cycle",
                                  subtype=f"jubilee_year_{cycle_year}",
                                  strength=0.35,
                                  confidence=0.4,
                                  discovered_by="algorithm",
                                  metadata={
                                      "cycle_year": cycle_year,
                                      "cycle_type": "jubilee",
                                      "note": f"Both occur in jubilee cycle year {cycle_year} "
                                              f"(Ussher-LXX chronology, approximate)",
                                      "event_a": events[i][1],
                                      "event_b": events[j][1],
                                      "date_a": events[i][2],
                                      "date_b": events[j][2],
                                  })
                    count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  Cyclical Time: {count} connections "
          f"(sabbatical: {sum(len(v) for v in sabbatical_groups.values())} events, "
          f"jubilee: {sum(len(v) for v in jubilee_groups.values())} events)")
    return count
