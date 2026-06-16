"""Typology connector — links type/antitype pairs across the canon.

Typology is the study of how persons, events, institutions, and objects
in earlier scripture prefigure and foreshadow later realities.
"""

from ..db import add_connection


TYPOLOGY_TYPES = {
    "Adam": "person_type",
    "Eve": "person_type",
    "Melchizedek": "person_type",
    "Moses": "person_type",
    "David": "person_type",
    "Jonah": "person_type",
    "Elijah": "person_type",
    "Joshua": "person_type",
    "Passover": "event_type",
    "Exodus": "event_type",
    "Flood": "event_type",
    "Wilderness": "event_type",
    "Tabernacle": "institution_type",
    "Day of Atonement": "institution_type",
    "Serpent_bronze": "object_type",
    "Manna": "object_type",
    "Rock/water": "object_type",
    "Cities of Refuge": "object_type",
    "Brazen Altar": "object_type",
    "Golden Lampstand": "object_type",
    "Veil of Temple": "object_type",
}


def generate_typology_connections(conn):
    """Generate symbolic connections for all typology pairs in the typology table.

    Also discovers additional type references from known type-antitype patterns.
    """
    count = 0

    # Step 1: Read all typology pairs from the seed data
    rows = conn.execute("""
        SELECT * FROM typology
    """).fetchall()

    for row in rows:
        type_name = row["type_name"]
        antitype_name = row["antitype_name"]
        type_verse = row["type_verse"]
        antitype_verse = row["antitype_verse"]

        conn_type = TYPOLOGY_TYPES.get(type_name, "shared_symbol")

        try:
            add_connection(conn, type_verse, antitype_verse,
                          layer="symbolic",
                          type_name=conn_type,
                          subtype=type_name.lower().replace(" ", "_").replace("/", "_"),
                          strength=0.85,
                          confidence=0.9,
                          discovered_by="algorithm",
                          metadata={
                              "type": type_name,
                              "antitype": antitype_name,
                              "description": row["description"],
                          })
            count += 1
        except Exception:
            pass

    # Step 2: Find additional NT/allusion references to OT types
    # For each major type, search for NT verses that reference it
    type_search_terms = {
        "Adam": ["Adam", "first man", "Ἀδάμ"],
        "Moses": ["Moses", "lawgiver", "Μωυσῆς"],
        "David": ["David", "son of David", "Δαυίδ"],
        "Melchizedek": ["Melchizedek", "Μελχισεδέκ"],
        "Jonah": ["Jonah", "Ἰωνᾶς"],
        "Elijah": ["Elijah", "Ἠλίας"],
        "Joshua": ["Joshua", "Ἰησοῦς"],
        "Passover": ["passover", "Πάσχα"],
        "Exodus": ["exodus", "ἔξοδος"],
        "Tabernacle": ["tabernacle", "tent", "σκηνή"],
        "wilderness_sojourn": ["wilderness"],
    }

    for type_name, terms in type_search_terms.items():
        for term in terms:
            # Find verses mentioning this type theme
            refs = conn.execute("""
                SELECT id, text_english FROM verses
                WHERE text_english LIKE ? AND book_id IN ('matt','mark','luke','john','acts','rom','1cor','2cor','gal','eph','phil','col','1thes','2thes','1tim','2tim','titus','philem','heb','james','1pet','2pet','1john','2john','3john','jude','rev')
                LIMIT 20
            """, (f"%{term}%",)).fetchall()

            for ref in refs:
                # Find the seed typology entries for this type
                seeds = conn.execute("""
                    SELECT antitype_verse FROM typology WHERE type_name = ?
                """, (type_name,)).fetchall()
                for seed in seeds:
                    # Don't duplicate existing typology connections
                    exists = conn.execute("""
                        SELECT id FROM connections
                        WHERE source_verse = ? AND target_verse = ? AND layer = 'symbolic'
                    """, (ref["id"], seed["antitype_verse"])).fetchone()
                    if not exists:
                        try:
                            add_connection(conn, ref["id"], seed["antitype_verse"],
                                          layer="symbolic",
                                          type_name="shared_symbol",
                                          subtype=f"type_{type_name.lower()}",
                                          strength=0.4,
                                          confidence=0.3,
                                          discovered_by="algorithm",
                                          metadata={
                                              "note": f"Potential reference to the {type_name} type. AI review needed.",
                                              "type": type_name,
                                          })
                            count += 1
                        except Exception:
                            pass
                    break  # One reference per found verse is enough

    conn.commit()
    return count
