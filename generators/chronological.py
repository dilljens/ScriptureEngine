"""Chronological generator — timeline and genealogical connections.

Builds a biblical timeline from genealogical data and connects
events that share the same time period or chronological markers.
"""

from lib.db import add_connection


# Major biblical events with approximate dates (based on Ussher/LXX)
# Format: (event_id, description, start_verse, end_verse, period_name)
TIMELINE_EVENTS = [
    # Creation to Flood
    ("creation", "Creation", "gen.1.1", "gen.2.3", "Primeval"),
    ("fall", "The Fall", "gen.3.1", "gen.3.24", "Primeval"),
    ("cain_abel", "Cain and Abel", "gen.4.1", "gen.4.26", "Primeval"),
    ("noah", "Noah and the Flood", "gen.6.9", "gen.9.29", "Primeval"),
    ("babel", "Tower of Babel", "gen.11.1", "gen.11.9", "Primeval"),
    
    # Patriarchs
    ("abraham", "Abraham", "gen.12.1", "gen.25.11", "Patriarchs"),
    ("isaac", "Isaac", "gen.25.19", "gen.27.46", "Patriarchs"),
    ("jacob", "Jacob", "gen.28.1", "gen.35.29", "Patriarchs"),
    ("joseph", "Joseph", "gen.37.1", "gen.50.26", "Patriarchs"),
    
    # Exodus
    ("exodus_from_egypt", "Exodus from Egypt", "exo.1.1", "exo.15.21", "Exodus"),
    ("wilderness", "Wilderness Wanderings", "exo.16.1", "deu.34.12", "Exodus"),
    ("law_given", "Law given at Sinai", "exo.19.1", "exo.20.26", "Exodus"),
    ("tabernacle", "Tabernacle built", "exo.25.1", "exo.40.38", "Exodus"),
    
    # Conquest and Judges
    ("conquest", "Conquest of Canaan", "josh.1.1", "josh.24.33", "Conquest_Judges"),
    ("judges_period", "Period of the Judges", "judg.1.1", "ruth.4.22", "Conquest_Judges"),
    
    # United Monarchy
    ("saul_reign", "Saul's Reign", "1sam.9.1", "1sam.31.13", "United_Monarchy"),
    ("david_reign", "David's Reign", "2sam.1.1", "1kgs.2.11", "United_Monarchy"),
    ("solomon_reign", "Solomon's Reign", "1kgs.2.12", "1kgs.11.43", "United_Monarchy"),
    ("temple_built", "Temple Built", "1kgs.6.1", "1kgs.8.66", "United_Monarchy"),
    
    # Divided Monarchy
    ("divided_kingdom", "Divided Kingdom", "1kgs.12.1", "2kgs.10.36", "Divided_Monarchy"),
    ("northern_captivity", "Northern Kingdom Captivity", "2kgs.17.1", "2kgs.17.41", "Divided_Monarchy"),
    ("elijah_ministry", "Elijah's Ministry", "1kgs.17.1", "2kgs.2.18", "Divided_Monarchy"),
    ("elisha_ministry", "Elisha's Ministry", "2kgs.2.19", "2kgs.13.21", "Divided_Monarchy"),
    ("isaiah_ministry", "Isaiah's Ministry", "isa.1.1", "isa.66.24", "Divided_Monarchy"),
    ("jeremiah_ministry", "Jeremiah's Ministry", "jer.1.1", "jer.52.34", "Divided_Monarchy"),
    ("ezekiel_ministry", "Ezekiel's Ministry", "ezek.1.1", "ezek.48.35", "Exile"),
    ("judah_captivity", "Judah's Babylonian Captivity", "2kgs.24.1", "2chr.36.23", "Exile"),
    
    # Return from Exile
    ("return_from_exile", "Return from Exile", "ezra.1.1", "ezra.10.44", "Post_Exile"),
    ("temple_rebuilt", "Temple Rebuilt", "ezra.3.1", "ezra.6.22", "Post_Exile"),
    ("nehemiah", "Nehemiah and the Wall", "neh.1.1", "neh.13.31", "Post_Exile"),
    ("malachi", "Malachi's Ministry", "mal.1.1", "mal.4.6", "Post_Exile"),
    
    # Intertestamental (based on Apocrypha references)
    ("maccabees", "Maccabean Period", "dan.11.1", "dan.12.13", "Intertestamental"),
    
    # NT — Life of Christ
    ("jesus_birth", "Birth of Jesus", "matt.1.1", "matt.2.23", "Gospel"),
    ("john_baptist_min", "John the Baptist", "matt.3.1", "matt.3.17", "Gospel"),
    ("jesus_early", "Jesus' Early Ministry", "matt.4.1", "john.4.54", "Gospel"),
    ("sermon_mount", "Sermon on the Mount", "matt.5.1", "matt.7.29", "Gospel"),
    ("jesus_miracles", "Jesus' Miracles", "matt.8.1", "luke.9.62", "Gospel"),
    ("transfiguration", "Transfiguration", "matt.17.1", "matt.17.13", "Gospel"),
    ("passion_week", "Passion Week", "matt.21.1", "matt.27.66", "Gospel"),
    ("crucifixion", "Crucifixion and Death", "matt.27.1", "matt.27.66", "Gospel"),
    ("resurrection", "Resurrection", "matt.28.1", "matt.28.20", "Gospel"),
    ("ascension", "Ascension", "acts.1.1", "acts.1.11", "Apostolic"),
    
    # NT — Apostolic Period
    ("pentecost_nt", "Day of Pentecost", "acts.2.1", "acts.2.47", "Apostolic"),
    ("paul_conversion", "Paul's Conversion", "acts.9.1", "acts.9.31", "Apostolic"),
    ("paul_mission", "Paul's Missionary Journeys", "acts.13.1", "acts.28.31", "Apostolic"),
    ("jerusalem_council", "Jerusalem Council", "acts.15.1", "acts.15.41", "Apostolic"),
    ("john_patmos", "John on Patmos / Revelation", "rev.1.1", "rev.22.21", "Apostolic"),
    
    # Book of Mormon — Lehi through Moroni
    ("lehi_departs", "Lehi Departs Jerusalem", "1ne.1.1", "1ne.2.15", "Lehite"),
    ("lehi_arrives", "Lehi Arrives in Promised Land", "1ne.17.1", "1ne.18.25", "Lehite"),
    ("jacob_preaches", "Jacob Preaches", "jacob.1.1", "jacob.7.27", "Lehite"),
    ("enos", "Enos", "enos.1.1", "enos.1.27", "Lehite"),
    ("kings_judges", "Period of Kings and Judges", "mosiah.1.1", "alma.1.1", "Nephite"),
    ("alma_preaches", "Alma's Ministry", "alma.1.1", "alma.50.1", "Nephite"),
    ("captivity_hellaman", "Nephite Wars", "hel.1.1", "3ne.1.1", "Nephite"),
    ("christ_americas", "Christ Visits the Americas", "3ne.11.1", "3ne.28.40", "Nephite"),
    ("mormon_wars", "Mormon's Record of War", "morm.1.1", "morm.8.11", "Nephite"),
    ("moroni_final", "Moroni's Final Record", "ether.1.1", "moro.10.34", "Nephite"),
    
    # D&C — Restoration
    ("first_vision", "First Vision", "jsh.1.1", "jsh.1.26", "Restoration"),
    ("restoration", "Restoration of the Church", "dc.1.1", "dc.1.20", "Restoration"),
    ("kirtland_temple", "Kirtland Temple / Endowment", "dc.109.1", "dc.110.16", "Restoration"),
    ("nauvoo", "Nauvoo Period", "dc.124.1", "dc.132.66", "Restoration"),
    ("westward", "Westward Migration", "dc.136.1", "dc.136.42", "Restoration"),
]

PERIOD_MAP = {
    "Primeval": 0, "Patriarchs": 1, "Exodus": 2, "Conquest_Judges": 3,
    "United_Monarchy": 4, "Divided_Monarchy": 5, "Exile": 6, "Post_Exile": 7,
    "Intertestamental": 8, "Gospel": 9, "Apostolic": 10,
    "Lehite": 11, "Nephite": 12, "Restoration": 13,
}


def run(conn, book_ids=None):
    """Generate chronological connections.
    
    Connects events that share the same time period and creates
    a timeline structure.
    """
    count = 0
    batch = []
    
    # Step 1: Connect events in the same period
    print("  Building chronological connections...", flush=True)
    
    # Group events by period
    period_events = {}
    for event in TIMELINE_EVENTS:
        period = event[4]
        if period not in period_events:
            period_events[period] = []
        period_events[period].append(event)
    
    # Connect events in the same period
    for period, events in period_events.items():
        period_order = PERIOD_MAP.get(period, 0)
        
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                # Connect the events' start verses
                try:
                    add_connection(conn, events[i][2], events[j][2],
                                  layer="chronological",
                                  type_name="same_time_period",
                                  subtype=period,
                                  strength=0.7,
                                  confidence=0.6,
                                  discovered_by="algorithm",
                                  metadata={
                                      "period": period,
                                      "period_order": period_order,
                                      "event_a": events[i][0],
                                      "event_b": events[j][0],
                                  })
                    count += 1
                except Exception:
                    pass
        
        # Connect successive events in sequence (prophetic_timeline)
        for i in range(len(events) - 1):
            try:
                add_connection(conn, events[i][3], events[i + 1][2],
                              layer="chronological",
                              type_name="prophetic_timeline",
                              subtype=period,
                              strength=0.65,
                              confidence=0.55,
                              discovered_by="algorithm",
                              metadata={
                                  "period": period,
                                  "period_order": period_order,
                                  "from_event": events[i][0],
                                  "to_event": events[i + 1][0],
                              })
                count += 1
            except Exception:
                pass
    
    # Step 2: Connect period transitions (dispensation connections)
    for i in range(len(TIMELINE_EVENTS) - 1):
        current_period = TIMELINE_EVENTS[i][4]
        next_period = TIMELINE_EVENTS[i + 1][4]
        
        if current_period != next_period:
            try:
                add_connection(conn, TIMELINE_EVENTS[i][3], TIMELINE_EVENTS[i + 1][2],
                              layer="chronological",
                              type_name="dispensation",
                              subtype=f"{current_period}_to_{next_period}",
                              strength=0.6,
                              confidence=0.5,
                              discovered_by="algorithm",
                              metadata={
                                  "from_period": current_period,
                                  "to_period": next_period,
                                  "from_event": TIMELINE_EVENTS[i][0],
                                  "to_event": TIMELINE_EVENTS[i + 1][0],
                              })
                count += 1
            except Exception:
                pass
    
    conn.commit()
    print(f"  Chronological: {count} connections")
    return count
