"""Geographic generator — location-based connections.

Connects verses that mention the same biblical location.
Uses a seed gazetteer of known place names.

Simple approach: find every verse containing any of the known place names,
then connect all verses mentioning the same place.
"""

import re
from collections import defaultdict
from lib.db import add_connection


# Seed gazetteer of biblical place names
GAZETTEER = {
    "Jerusalem": ["Jerusalem", "Zion", "the city of David"],
    "Bethlehem": ["Bethlehem", "Beth-lehem", "Ephrath"],
    "Nazareth": ["Nazareth", "Nazarene"],
    "Capernaum": ["Capernaum"],
    "Jericho": ["Jericho"],
    "Hebron": ["Hebron", "Mamre"],
    "Beersheba": ["Beersheba", "Beer-sheba"],
    "Bethel": ["Bethel", "Beth-el"],
    "Gilgal": ["Gilgal"],
    "Shiloh": ["Shiloh"],
    "Samaria": ["Samaria"],
    "Galilee": ["Galilee", "Galilean"],
    "Judea": ["Judea", "Judaea"],
    "Egypt": ["Egypt", "Egyptian"],
    "Babylon": ["Babylon", "Babylonian"],
    "Nineveh": ["Nineveh", "Ninevite"],
    "Sodom": ["Sodom", "Sodomite"],
    "Gomorrah": ["Gomorrah"],
    "Sinai": ["Sinai", "Horeb"],
    "Zion": ["Zion", "Sion"],
    "Golgotha": ["Golgotha", "Calvary"],
    "Gethsemane": ["Gethsemane"],
    "Jordan": ["Jordan"],
    "Red Sea": ["Red Sea"],
    "Dead Sea": ["Dead Sea", "Salt Sea"],
    "Mediterranean": ["Mediterranean", "Great Sea", "utmost sea"],
    "Wilderness": ["wilderness of", "desert of"],
    "Canaan": ["Canaan", "Canaanite", "land of promise"],
    "Goshen": ["Goshen"],
    "Mount of Olives": ["Mount of Olives", "Olivet"],
    "Armageddon": ["Armageddon", "Megiddo"],
    "Patmos": ["Patmos"],
    "Damascus": ["Damascus"],
    "Tyre": ["Tyre"],
    "Sidon": ["Sidon"],
    "Antioch": ["Antioch"],
    "Corinth": ["Corinth", "Corinthian"],
    "Ephesus": ["Ephesus", "Ephesian"],
    "Philippi": ["Philippi", "Philippian"],
    "Thessalonica": ["Thessalonica", "Thessalonian"],
    "Rome": ["Rome", "Roman"],
    "Harran": ["Haran", "Charran"],
    "Ur": ["Ur of the Chaldees"],
    "Shinar": ["Shinar", "Babel"],
    "Assyria": ["Assyria", "Assyrian"],
    "Ethiopia": ["Ethiopia", "Ethiopian", "Cush"],
}


def run(conn, book_ids=None):
    """Generate geographic connections.

    For each place name in the gazetteer, find all verses mentioning it,
    then connect verses that share the same place.

    Returns count of connections created.
    """
    count = 0

    # Get all verses
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT id, text_english FROM verses
            WHERE text_english != '' AND book_id IN ({placeholders})
        """, book_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, text_english FROM verses WHERE text_english != ''
        """).fetchall()

    print(f"  Scanning {len(rows)} verses for place names...")

    # Build a place→verses index
    place_verses = defaultdict(set)
    for r in rows:
        text_lower = r["text_english"].lower()
        for place, search_terms in GAZETTEER.items():
            for term in search_terms:
                if term.lower() in text_lower:
                    place_verses[place].add(r["id"])
                    break  # One match per place per verse

    # Connect verses that share the same place
    for place, verses in place_verses.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)
        # Use hub-and-spoke to avoid N² explosion for very common places
        if len(verse_list) > 20:
            hub = verse_list[0]
            for v in verse_list[1:]:
                try:
                    add_connection(conn, hub, v,
                                  layer="geographic",
                                  type_name="same_location",
                                  subtype=place.lower().replace(" ", "_"),
                                  strength=0.6,
                                  confidence=0.7,
                                  discovered_by="algorithm",
                                  metadata={"location": place})
                    count += 1
                except Exception:
                    pass
        else:
            # Full mesh for less common places
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    try:
                        add_connection(conn, verse_list[i], verse_list[j],
                                      layer="geographic",
                                      type_name="same_location",
                                      subtype=place.lower().replace(" ", "_"),
                                      strength=0.6,
                                      confidence=0.7,
                                      discovered_by="algorithm",
                                      metadata={"location": place})
                        count += 1
                    except Exception:
                        pass

    conn.commit()
    print(f"  Geographic: {count} connections across {len(place_verses)} places")
    return count
