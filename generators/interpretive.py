"""Interpretive generator — known interpretive traditions.

Creates connections between verses and their established interpretations
across different traditions:
  - Jewish interpretive tradition (Midrash, Talmud)
  - Christian interpretive tradition (patristic, reformation)
  - Latter-day Saint interpretive tradition
  - Critical scholarship
"""

from lib.db import add_connection


# Known interpretive connections
# Format: (source_verse, target_verse, tradition, type_name, note)
INTERPRETATIONS = [
    # Rabbinic/Midrashic connections
    ("gen.1.1", "john.1.1", "jewish", "midrashic_connection",
     "The Targum Neofiti and other Jewish traditions connect 'In the beginning' with the creation of Torah/Wisdom, paralleling John's Logos theology"),
    ("gen.1.2", "rev.12.9", "jewish", "rabbinic_midrash",
     "Rabbinic tradition identifies the serpent with the satan (ha-satan), connecting the garden narrative with end-time defeat of the adversary"),
    ("gen.1.27", "gen.2.22", "jewish", "rabbinic_midrash",
     "Midrash Rabba notes the plural 'let us make man' — rabbinic tradition often interprets this as God taking counsel with the angels"),
    ("gen.3.1", "rev.12.9", "jewish", "rabbinic_midrash",
     "Midrashim connect the serpent of Eden with the adversary figure who appears at the end of days"),
    
    # Patristic (early church fathers)
    ("gen.1.1", "john.1.1", "patristic", "patristic_reading",
     "Augustine: 'In the beginning' refers to Christ the Word — the OT creation account and John's prologue speak of the same Logos"),
    ("gen.2.7", "john.20.22", "patristic", "patristic_reading",
     "Gregory of Nyssa and other fathers see the two inbreathings (Gen 2:7 and John 20:22) as the first creation and the new creation"),
    ("exo.12.46", "john.19.36", "patristic", "patristic_reading",
     "Early fathers connected the paschal lamb's unbroken bones with Christ on the cross — a type finding its antitype"),
    ("num.21.8", "john.3.14", "patristic", "patristic_reading",
     "Justin Martyr and subsequent fathers saw the bronze serpent lifted up as a type of Christ lifted up on the cross"),
    ("jonah.1.17", "matt.12.40", "patristic", "patristic_reading",
     "Jonah in the fish three days as a type of Christ in the tomb — universally recognized by patristic writers"),
    
    # Reformation
    ("rom.1.17", "gal.3.11", "reformation", "reformation_view",
     "Luther: 'The just shall live by faith' — this verse sparked the Reformation. Luther understood Paul to be contrasting faith vs. works-righteousness, not faith vs. Torah"),
    ("rom.4.1", "gal.3.6", "reformation", "reformation_view",
     "Calvin: Abraham's faith was counted for righteousness — the covenant with Abraham was always a covenant of grace, not of works"),
    ("gen.15.6", "rom.4.3", "reformation", "reformation_view",
     "Luther and Calvin both see this as the definitive OT proof that justification is by faith, not by works of the law"),
    
    # Latter-day Saint interpretive tradition
    ("gen.1.1", "moses.2.1", "latter_day_saint", "latter_day_saint_reading",
     "JST/Book of Moses expands Genesis 1:1 to show the premortal council: 'Yea, in the beginning I created the heaven, and the earth upon which thou standest' — revealing the context of the creation as a heavenly council"),
    ("gen.1.26", "abraham.4.26", "latter_day_saint", "latter_day_saint_reading",
     "Abraham 4 expands 'Let us make man' showing the Gods (plural) counseling together — revealing the Godhead as distinct personages who work in unity"),
    ("gen.14.18", "heb.7.1", "latter_day_saint", "latter_day_saint_reading",
     "JST Genesis 14 expands the Melchizedek narrative, showing he was a high priest after the order of God, and that Abraham paid tithes to him. LDS tradition sees Melchizedek as a type of Christ's priesthood"),
    ("isa.11.1", "dc.113.1", "latter_day_saint", "latter_day_saint_reading",
     "D&C 113 provides an LDS interpretive reading of Isaiah 11 — the stem of Jesse is identified as Christ, and the rod as a servant in the lineage of Joseph"),
    ("isa.52.7", "mosiah.12.20", "latter_day_saint", "latter_day_saint_reading",
     "Abinadi (Mosiah 12-15) quotes Isaiah 52-53 to the priests of King Noah, providing an extensive interpretive reading that emphasizes Christ's atonement"),
    ("gen.48.16", "dc.132.37", "latter_day_saint", "latter_day_saint_reading",
     "D&C 132 references the Patriarchs having plural wives as a divine principle of eternal marriage and posterity"),

    # Jewish/Christian cross-reference — NT quotes OT
    ("psa.22.1", "matt.27.46", "patristic", "patristic_reading",
     "Psalm 22 is consistently read as a messianic psalm by both Jewish and Christian interpreters — Christian tradition reads it as a prophecy of the crucifixion"),
    ("psa.110.1", "matt.22.44", "jewish", "rabbinic_midrash",
     "Rabbinic tradition interprets Psalm 110 as referring to Abraham or David, while Christian tradition (following Jesus himself) reads it as referring to the Messiah"),
    ("dan.7.13", "matt.26.64", "jewish", "rabbinic_midrash",
     "The 'Son of Man' figure in Daniel 7 receives extensive interpretation in both Jewish (1 Enoch, 4 Ezra) and Christian (Gospels) tradition as a messianic figure"),
    
    # Critical scholarship
    ("gen.1.1", "gen.2.4", "critical", "critical_scholarship",
     "Source criticism identifies two creation accounts: the Priestly (Gen 1:1-2:4a) and the Yahwist (Gen 2:4b-25), from different sources with different theological emphases"),
    ("isa.1.1", "isa.39.1", "critical", "critical_scholarship",
     "Scholars identify First Isaiah (ch 1-39) as set in the 8th century BC, while chapters 40-66 are attributed to later writers (Deutero-Isaiah, Trito-Isaiah)"),
    ("gen.6.1", "gen.9.29", "critical", "critical_scholarship",
     "The Flood narrative is identified as an interweaving of J and P sources, with characteristic vocabulary and theological differences between the two"),
    ("dan.1.1", "dan.12.13", "critical", "critical_scholarship",
     "Critical scholarship dates Daniel to the Maccabean period (c. 165 BC), making it a prophecy after the fact (vaticinium ex eventu) rather than a 6th-century prediction"),
]


def run(conn, book_ids=None):
    """Generate interpretive connections.
    
    Connects verses to their interpretive traditions.
    """
    count = 0
    
    # Map interpretive type names to categories
    tradition_map = {
        "jewish": "rabbinic_midrash",
        "patristic": "patristic_reading",
        "reformation": "reformation_view",
        "latter_day_saint": "latter_day_saint_reading",
        "critical": "critical_scholarship",
    }
    
    for entry in INTERPRETATIONS:
        source, target, tradition, type_name, note = entry
        
        layer_type = tradition_map.get(tradition, "rabbinic_midrash")
        
        try:
            add_connection(conn, source, target,
                          layer="interpretive",
                          type_name=layer_type,
                          subtype=tradition,
                          strength=0.6,
                          confidence=0.5,
                          discovered_by="algorithm",
                          metadata={
                              "tradition": tradition,
                              "note": note,
                              "type": "interpretive_tradition",
                              "label": f"{tradition}: {note[:100]}",
                          })
            count += 1
        except Exception:
            pass
        
        if count % 50 == 0:
            conn.commit()
    
    conn.commit()
    print(f"  Interpretive: {count} connections across {len(set(e[3] for e in INTERPRETATIONS))} traditions")
    return count
