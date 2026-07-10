#!/usr/bin/env python3
"""Seed Sod-layer connections from L. Michael Morales's ascent theology."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import get_db, add_connection

CONNECTIONS = [
    # Psalm 24 — The entrance liturgy question
    ("psa.24.3", "psa.15.1", "temple_ascent", "who_shall_ascend",
     "Morales: 'Who shall ascend the mountain of YHWH?' and 'Who shall abide in thy tabernacle?' — the same entrance liturgy question frames both psalms"),
    ("psa.24.3", "gen.28.17", "temple_ascent", "who_shall_ascend",
     "Morales: 'How dreadful is this place! This is none other but the house of God, and this is the gate of heaven' — Jacob at Bethel experiences the ascent question"),
    ("psa.24.3", "exo.19.3", "temple_ascent", "mountain_of_god",
     "Morales: Moses ascending Sinai to meet God — the prototypical ascent narrative. 'Moses went up unto God, and the LORD called unto him out of the mountain'"),
    ("psa.24.3", "isa.33.14", "temple_ascent", "who_shall_ascend",
     "Morales: 'Who among us shall dwell with the devouring fire?' — the entrance liturgy question reframed for the eschatological Zion"),
    
    # Ascent of Sinai — the mountain of God
    ("exo.19.12", "heb.12.18", "temple_ascent", "mountain_of_god",
     "Morales: Mount Sinai as a type of the heavenly Mount Zion — the unapproachable mountain versus 'ye are come unto Mount Sion, the city of the living God, the heavenly Jerusalem'"),
    ("exo.19.18", "deu.4.11", "temple_ascent", "mountain_of_god",
     "Morales: Sinai burning with fire and covered with smoke — the mountain as theophany, the template for prophetic calls and temple visions"),
    ("exo.24.9", "exo.19.3", "temple_ascent", "mountain_of_god",
     "Morales: 'They saw the God of Israel' — the elders ascending Sinai to eat and drink in God's presence, the first biblical ascent narrative"),
    
    # Tabernacle as Sinai continued
    ("exo.25.8", "exo.40.34", "temple_ascent", "tabernacle_as_sinai",
     "Morales: The tabernacle was the mobile Sinai — God's presence leaving the mountain to dwell with Israel. 'Let them make me a sanctuary, that I may dwell among them' and 'the glory of the LORD filled the tabernacle'"),
    ("exo.40.34", "1kgs.8.10", "temple_ascent", "tabernacle_as_sinai",
     "Morales: The same glory that filled the tabernacle filled Solomon's temple — continuity of divine presence from Sinai to Zion"),
    
    # Day of Atonement — the annual ascent
    ("lev.16.1", "lev.16.34", "holy_of_holies", "atonement_ascent",
     "Morales: The Day of Atonement is the only day the high priest can ascend to the Holy of Holies — the annual enactment of the ascent question"),
    ("lev.16.2", "exo.30.10", "holy_of_holies", "atonement_ascent",
     "Morales: The veil separating the Holy from the Holy of Holies is the boundary that only the High Priest can cross, once a year, with blood"),
    
    # Zion / temple mount as cosmic mountain
    ("psa.48.1", "isa.2.2", "cosmic_mountain", "zion_as_cosmic_mountain",
     "Morales: 'Great is the LORD, and greatly to be praised in the city of our God, in the mountain of his holiness' — Zion as the cosmic mountain, the navel of the earth"),
    ("psa.48.2", "ezek.40.2", "cosmic_mountain", "zion_as_cosmic_mountain",
     "Morales: 'Beautiful for situation, the joy of the whole earth, is Mount Zion' — Ezekiel's temple vision on a 'very high mountain' identifies the eschatological temple with Zion"),
    
    # Ascent to Zion in the Psalms of Ascents
    ("psa.120.1", "psa.122.1", "temple_ascent", "psalms_of_ascents",
     "Morales: The Songs of Ascents (Psalms 120-134) are the pilgrimage liturgy — the people ascending to Zion for the feasts, fulfilling the entrance liturgy"),
    ("psa.122.1", "psa.24.3", "temple_ascent", "psalms_of_ascents",
     "Morales: 'I was glad when they said unto me, Let us go into the house of the LORD' — the pilgrimage to Zion answers the question 'Who shall ascend?'"),
    
    # Christ as the ascent
    ("john.1.51", "gen.28.12", "temple_ascent", "christ_as_ascent",
     "Morales: Jesus says 'Ye shall see heaven open, and the angels of God ascending and descending upon the Son of Man' — he is the new Bethel, the gate of heaven"),
    ("john.3.13", "john.1.51", "temple_ascent", "christ_as_ascent",
     "Morales: 'No man hath ascended up to heaven, but he that came down from heaven, even the Son of Man' — Jesus is the only one who has made the true ascent"),
    
    # Hebrews — the heavenly ascent
    ("heb.4.14", "lev.16.1", "temple_ascent", "heavenly_ascent",
     "Morales: 'Seeing then that we have a great high priest, that is passed into the heavens, Jesus the Son of God' — Christ's ascension is the true Day of Atonement"),
    ("heb.9.24", "exo.25.9", "temple_ascent", "heavenly_ascent",
     "Morales: 'For Christ is not entered into the holy places made with hands, which are the figures of the true, but into heaven itself' — the heavenly tabernacle"),
    ("heb.10.19", "lev.16.2", "temple_ascent", "heavenly_ascent",
     "Morales: 'Having therefore, brethren, boldness to enter into the holiest by the blood of Jesus' — the new and living way through the veil"),
    
    # Revelation — the final ascent
    ("rev.21.2", "gen.2.8", "eden_temple", "new_jerusalem_ascent",
     "Morales: The New Jerusalem coming down from heaven — the reverse of Eden's expulsion. The mountain of God descends to dwell with man"),
    ("rev.21.22", "1kgs.8.27", "temple_eschaton", "no_temple_there",
     "Morales: 'I saw no temple therein: for the Lord God Almighty and the Lamb are the temple of it' — the goal of the ascent is to dwell with God without need of a temple"),
    ("rev.22.1", "ezek.47.1", "temple_eschaton", "river_of_life",
     "Morales: The river of life proceeding from the throne of God and the Lamb — the fulfillment of Ezekiel's temple river, the water of life from Eden"),
    
    # Exodus motif as ascent
    ("exo.15.13", "psa.77.20", "temple_ascent", "exodus_as_ascent",
     "Morales: 'Thou in thy mercy hast led forth the people which thou hast redeemed: thou hast guided them in thy strength unto thy holy habitation' — the Exodus as ascent to the mountain of God"),
    ("exo.15.17", "1kgs.8.13", "temple_ascent", "exodus_as_ascent",
     "Morales: 'Thou shalt bring them in, and plant them in the mountain of thine inheritance, in the place, O LORD, which thou hast made for thee to dwell in' — the goal of the Exodus is the temple mountain"),
    
    # Isaiah's temple vision
    ("isa.6.1", "exo.24.9", "temple_ascent", "prophetic_temple_vision",
     "Morales: Isaiah's vision of YHWH in the temple — 'I saw also the Lord sitting upon a throne, high and lifted up' — a new Sinai vision at the temple"),
    ("isa.6.5", "exo.33.20", "temple_ascent", "prophetic_temple_vision",
     "Morales: 'Woe is me! for I am undone... for mine eyes have seen the King, the LORD of hosts' — the ascent question's answer: no one can see God and live, yet Isaiah sees and lives"),
]

def main():
    conn = get_db()
    print("=" * 60)
    print("  L. Michael Morales — Ascent of the Mountain of the Lord")
    print("=" * 60)
    
    count = 0
    for source, target, conn_type, subtype, note in CONNECTIONS:
        try:
            existing = conn.execute(
                "SELECT COUNT(*) FROM connections WHERE source_verse = ? AND target_verse = ? AND type = ? AND subtype = ?",
                (source, target, conn_type, subtype)
            ).fetchone()[0]
            
            if existing == 0:
                add_connection(conn, source, target, layer="sod",
                              type_name=conn_type, subtype=subtype,
                              strength=0.55, confidence=0.45,
                              discovered_by="human",
                              metadata={"scholar": "L. Michael Morales",
                                       "note": note[:200],
                                       "source": "Who Shall Ascend the Mountain of the Lord"})
                count += 1
        except Exception:
            pass
    
    conn.commit()
    total_sod = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='sod'").fetchone()["c"]
    print(f"  Added {count} new Morales ascent connections")
    print(f"  Sod layer total: {total_sod}")
    conn.close()

if __name__ == "__main__":
    main()
