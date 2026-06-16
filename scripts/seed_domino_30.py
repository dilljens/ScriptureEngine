#!/usr/bin/env python3
"""Seed Gileadi's 30 domino events from IsaiahExplained.com.

Each domino event is an ancient type that prefigures an end-time event.
Events overlap in an ABC/BCD/CDE chain — each event connects to the next,
and events appear in multiple combinations creating the domino effect.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection

# Gileadi's 30 Ancient Types of End-Time Events
# (event_name, key_verse_for_type, end_time_fulfillment_verse, domino_to_next)
DOMINO_EVENTS = [
    ("1. Israel's Apostasy", "isa.1.2", "isa.1.31", "isa.3.14",
     "Modern apostasy of God's covenant people — the catalyst that triggers all domino events"),
    ("2. The Tower of Babel", "gen.11.4", "gen.11.9", "isa.25.2",
     "Globalist utopian project — a 'city with a tower' modern Babylon society"),
    ("3. The Babylonian Captivity", "jer.39.1", "jer.39.10", "isa.47.6",
     "End-time captivity of God's people by a coercive new world order"),
    ("4. The Call of Abraham", "gen.12.1", "gen.12.5", "isa.41.8",
     "The righteous are called out of Babylon, as Abraham was called out of Ur"),
    ("5. Lot's Deliverance from Sodom", "gen.19.1", "gen.19.17", "isa.65.8",
     "A proxy savior delivers the righteous before destruction, as Abraham saved Lot"),
    ("6. The Destruction of Sodom and Gomorrah", "gen.19.23", "gen.19.28", "isa.34.9",
     "Worldwide fire and brimstone judgment on the wicked"),
    ("7. Cosmic Disturbance", "2sam.22.8", "2sam.22.16", "isa.24.18",
     "The heavens shaken, sun/moon darken, earth reels at God's coming"),
    ("8. Primordial Chaos", "gen.1.1", "gen.1.2", "isa.40.12",
     "Creation reverses — tohu wabohu returns as God de-creates wicked institutions"),
    ("9. Assyria's World Conquest", "isa.10.5", "isa.10.14", "isa.14.13",
     "An end-time archtyrant conquers the world by military force, boasting like Assyria"),
    ("10. The Flood", "gen.6.9", "gen.9.29", "isa.54.9",
     "A 'flood of fire' — destruction by the Assyrian alliance, like Noah's flood"),
    ("11. Assyria's Invasion of the Promised Land", "isa.7.1", "isa.7.25", "isa.5.26",
     "The archtyrant invades God's people's land as Assyria invaded Judah"),
    ("12. The Egyptian Bondage", "exo.1.1", "exo.2.25", "isa.52.5",
     "God's people enslaved by a superpower, as Israel was enslaved in Egypt"),
    ("13. Israel's Exodus out of Egypt", "exo.12.1", "exo.15.21", "isa.51.9",
     "A new exodus — God delivers His people from bondage through His servant"),
    ("14. Israel's Wandering in the Wilderness", "exo.16.1", "deu.34.12", "isa.35.1",
     "A brief wilderness sojourn that purifies and prepares God's people"),
    ("15. Israel's Pilgrimage to Zion", "psa.84.1", "psa.84.12", "isa.2.2",
     "All nations stream to Zion — the great pilgrimage to God's mountain"),
    ("16. Jehovah's Protective Cloud", "exo.13.21", "exo.14.31", "isa.4.5",
     "God's glory cloud protects His elect when He comes in judgment"),
    ("17. Assyria's Siege of Jerusalem", "2kgs.18.13", "2kgs.19.37", "isa.37.30",
     "The archtyrant besieges God's people, Hezekiah intercedes like the end-time servant"),
    ("18. The Passover", "exo.12.1", "exo.12.51", "isa.31.5",
     "The angel of death passes over God's elect as in Egypt — a new Passover"),
    ("19. Jehovah's Descent on the Mount", "exo.19.1", "exo.20.26", "isa.25.6",
     "God descends on Mount Zion as He descended on Sinai — the theophany"),
    ("20. Jehovah's Consuming Fire", "lev.9.24", "lev.10.7", "isa.10.16",
     "Fire from God consumes the wicked and the Assyrian alliance"),
    ("21. Israel's Conquest of the Promised Land", "josh.1.1", "josh.24.33", "isa.41.13",
     "God's people take possession of their promised lands"),
    ("22. Israel's Victory over Midian", "judg.7.1", "judg.8.28", "isa.10.26",
     "The few defeat the many — a small righteous remnant overthrows oppressors"),
    ("23. Cyrus' Universal Conquests", "ezra.1.1", "ezra.1.11", "isa.41.2",
     "A servant like Cyrus is raised up from the east to deliver God's people"),
    ("24. The Davidic Monarchy", "2sam.7.1", "2sam.7.29", "isa.55.3",
     "A descendant of David sits on the throne — the Davidic covenant fulfilled"),
    ("25. Rebuilding of the Temple", "ezra.3.1", "ezra.6.22", "isa.60.1",
     "The temple is rebuilt in the millennial age"),
    ("26. The Reign of the Judges", "judg.2.1", "judg.21.25", "isa.1.24",
     "God raises up deliverers — righteous judges rule God's people"),
    ("27. Jehovah's Covenant", "exo.24.1", "exo.24.18", "isa.54.10",
     "The everlasting covenant of peace is established with God's people"),
    ("28. Zion as Jehovah's Residence", "psa.48.1", "psa.48.14", "isa.60.14",
     "God dwells in Zion — His permanent residence on earth"),
    ("29. The Creation", "gen.1.1", "gen.2.3", "isa.65.17",
     "A new heaven and a new earth — re-creation after judgment"),
    ("30. Paradise", "gen.2.8", "gen.3.24", "isa.51.3",
     "Paradise restored — the garden of Eden becomes Zion, God dwells with His people"),
]


def main():
    conn = get_db()
    print("=" * 60)
    print("  GILEADI'S 30 DOMINO EVENTS")
    print("=" * 60)
    print()
    
    count = 0
    
    print("--- Event List ---")
    for i, event in enumerate(DOMINO_EVENTS):
        name, type_verse, end_verse, connect_to, note = event
        print(f"  {name:45s} {type_verse:15s}")
    print()
    
    # Create connections
    print("--- Creating Domino Chain Connections ---")
    
    for i, event in enumerate(DOMINO_EVENTS):
        name, type_verse, end_verse, connect_to, note = event
        
        # Connect the ancient type to its end-time fulfillment
        try:
            add_connection(conn, type_verse, end_verse,
                          layer="chronological",
                          type_name="prophetic_timeline",
                          subtype="gileadi_domino",
                          strength=0.75, confidence=0.7,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "event": name,
                              "type": "ancient_type → end_time_fulfillment",
                              "source": "IsaiahExplained.com",
                          })
            count += 1
        except Exception:
            pass
        
        # Connect this event to the next (domino chain: domino N → domino N+1)
        if i < len(DOMINO_EVENTS) - 1:
            next_name = DOMINO_EVENTS[i + 1][0]
            try:
                add_connection(conn, end_verse, DOMINO_EVENTS[i + 1][1],
                              layer="chronological",
                              type_name="prophetic_timeline",
                              subtype="gileadi_domino_chain",
                              strength=0.6, confidence=0.55,
                              discovered_by="algorithm",
                              metadata={
                                  "scholar": "Avraham Gileadi",
                                  "event": name,
                                  "next_event": next_name,
                                  "type": "domino transition",
                                  "note": f"Domino {i+1} → Domino {i+2}",
                              })
                count += 1
            except Exception:
                pass
    
    conn.commit()
    
    # Stats
    chrono = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='chronological'").fetchone()["c"]
    total = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()["c"]
    print(f"  Created {count} domino connections")
    print(f"  Chronological layer: {chrono}")
    print(f"  Total connections: {total}")
    conn.close()


if __name__ == "__main__":
    main()
