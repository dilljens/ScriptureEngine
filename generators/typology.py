"""Typology generator — systematic type/antitype connections.

Creates connections between OT types and their NT antitypes (or BoM/D&C
fulfillments). Uses explicit '"as X, so also Y"' patterns and well-known
typological pairs from biblical scholarship.

Connections are created in the 'symbolic' layer with type='type_antitype'.
"""

import json
from lib.db import add_connection

# ─── Classic Typological Pairs ───
# Each pair: (name, type_start, type_end, antitype_start, antitype_end,
#             subtype, strength, confidence, description)

TYPES = [
    # Person as Type
    ("Adam → Christ", "gen.2.7", "gen.3.24", "rom.5.14", "rom.5.21",
     "person_type", 0.85, 0.75, "Paul explicitly calls Adam a 'type' (typos) of Christ"),
    ("Adam → Christ (Last Adam)", "gen.2.7", "gen.3.24", "1cor.15.45", "1cor.15.49",
     "person_type", 0.85, 0.75, "Paul: 'The first man Adam became a living being; the last Adam became a life-giving spirit'"),
    ("Melchizedek → Christ", "gen.14.18", "gen.14.20", "heb.7.1", "heb.7.28",
     "person_type", 0.85, 0.75, "Hebrews develops Melchizedek as a type of Christ's eternal priesthood"),
    ("Melchizedek → Christ (Psalm 110)", "psa.110.4", "psa.110.4", "heb.7.17", "heb.7.17",
     "person_type", 0.9, 0.8, "'You are a priest forever according to the order of Melchizedek'"),
    ("Moses → Christ (Prophet)", "deu.18.15", "deu.18.19", "acts.3.22", "acts.3.23",
     "person_type", 0.85, 0.75, "Moses promised a prophet like him — Peter and Stephen identify this as Christ"),
    ("David → Christ (King)", "psa.2.7", "psa.2.12", "acts.13.33", "acts.13.37",
     "person_type", 0.8, 0.7, "Davidic king as type of Messiah — Psalm 2 quoted in Acts"),
    ("Joshua → Jesus (name typology)", "josh.1.1", "josh.1.9", "heb.4.8", "heb.4.10",
     "person_type", 0.6, 0.5, "Hebrews: Joshua (Yeshua) gave Israel rest, but a greater rest remains in Christ"),
    ("Jonah → Christ (Resurrection)", "jonah.1.17", "jonah.2.10", "matt.12.40", "matt.12.41",
     "person_type", 0.9, 0.8, "Jesus explicitly says Jonah is a type: 'as Jonah was three days... so the Son of Man'"),

    # Event as Type
    ("Passover → Crucifixion", "exo.12.1", "exo.12.51", "john.19.14", "john.19.36",
     "event_type", 0.8, 0.7, "Jesus crucified at Passover — the Lamb of God fulfills the Passover type"),
    ("Passover Lamb → Christ", "exo.12.3", "exo.12.13", "1cor.5.7", "1cor.5.8",
     "event_type", 0.85, 0.75, "Paul: 'Christ our Passover is sacrificed for us'"),
    ("Exodus → Redemption in Christ", "exo.14.1", "exo.15.21", "luke.9.31", "luke.9.31",
     "event_type", 0.7, 0.6, "Jesus' 'departure' (exodos) at the Transfiguration — Luke uses the Exodus word"),
    ("Red Sea → Baptism", "exo.14.21", "exo.14.31", "1cor.10.1", "1cor.10.2",
     "event_type", 0.8, 0.7, "Paul: 'Our fathers were all baptized into Moses in the cloud and in the sea'"),
    ("Manna → Bread of Life", "exo.16.4", "exo.16.36", "john.6.31", "john.6.51",
     "institution_type", 0.8, 0.7, "Jesus: 'I am the bread of life' — contrasting Manna with Himself"),
    ("Water from Rock → Christ", "exo.17.6", "exo.17.7", "1cor.10.4", "1cor.10.4",
     "object_type", 0.85, 0.75, "Paul: 'They drank from the spiritual rock, and that rock was Christ'"),
    ("Tabernacle → Heaven", "exo.25.8", "exo.25.9", "heb.8.5", "heb.9.24",
     "institution_type", 0.8, 0.7, "Hebrews: the tabernacle is a 'copy and shadow of heavenly things'"),
    ("Day of Atonement → Christ's Atonement", "lev.16.1", "lev.16.34", "heb.9.11", "heb.9.28",
     "event_type", 0.8, 0.7, "Christ enters the heavenly Holy of Holies as the ultimate High Priest"),
    ("Bronze Serpent → Cross", "num.21.8", "num.21.9", "john.3.14", "john.3.15",
     "object_type", 0.9, 0.8, "Jesus: 'As Moses lifted up the serpent, so must the Son of Man be lifted up'"),

    # Institution as Type
    ("Sabbath → Christ's Rest", "gen.2.2", "gen.2.3", "heb.4.9", "heb.4.11",
     "institution_type", 0.7, 0.6, "The Sabbath rest is a type of the eternal rest in Christ"),
    ("Circumcision → Baptism", "gen.17.10", "gen.17.14", "col.2.11", "col.2.12",
     "institution_type", 0.7, 0.6, "Baptism is the 'circumcision of Christ' — the spiritual fulfillment"),
    ("Earthly Temple → Heavenly Temple", "1kgs.6.1", "1kgs.8.66", "rev.21.22", "rev.22.5",
     "institution_type", 0.7, 0.6, "John sees no temple in the New Jerusalem — God and the Lamb are the temple"),

    # Non-Scriptural Typology (D&C)
    ("Melchizedek Priesthood → Restoration", "gen.14.18", "gen.14.20", "dc.110.13", "dc.110.16",
     "person_type", 0.8, 0.7, "Melchizedek Priesthood restored in D&C 110 by the same Melchizedek figure"),
    ("Enoch's Zion → Latter-day Zion", "gen.5.22", "gen.5.24", "dc.76.66", "dc.76.70",
     "institution_type", 0.6, 0.5, "Enoch's Zion as type of the latter-day Zion"),
    ("Enoch's City → New Jerusalem", "gen.5.24", "gen.5.24", "moses.7.62", "moses.7.69",
     "event_type", 0.7, 0.6, "Enoch's city of Zion as type of the New Jerusalem"),
]


def run(conn, book_ids=None):
    """Create typology connections."""
    count = 0
    metadata = json.dumps({"generator": "typology", "tag": "typology"}, ensure_ascii=False)
    
    for (name, ts, te, ats, ate, subtype, strength, confidence, note) in TYPES:
        # Check if already exists
        existing = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE layer='symbolic' AND type='type_antitype' AND subtype=?",
            (subtype,)
        ).fetchone()[0]
        
        # Create connection from type's start verse to antitype's start verse
        try:
            add_connection(conn, ts, ats,
                          layer="symbolic",
                          type_name="type_antitype",
                          subtype=subtype,
                          strength=strength,
                          confidence=confidence,
                          discovered_by="human",
                          metadata=json.dumps({
                              "note": note[:200],
                              "type": {"name": name, "start": ts, "end": te},
                              "antitype": {"start": ats, "end": ate},
                              "tag": "typology",
                          }, ensure_ascii=False))
            count += 1
        except Exception as e:
            pass
    
    conn.commit()
    print(f"  Typology: {count} type/antitype pairs")
    return count
