#!/usr/bin/env python3
"""
Seed targeted cross-canon connections for DSS + Pseudepigrapha.

Creates sod-layer connections for key thematic links that the
algorithmic generators miss (shared rare-word clusters don't
capture conceptual parallels like dualism, community-as-temple).

Usage: python3 scripts/seed_dss_cross_canon.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection


# ─── Connection groups ──────────────────────────────────────────────

CONNECTIONS = [
    # ═══════════════════════════════════════════════════════════════
    # 1. ENOCHIC WATCHER TRADITION
    # ═══════════════════════════════════════════════════════════════
    # 1 Enoch 6-16 → Genesis 6:1-4 (sons of God / Watchers)
    {"source": "1en.6.1", "target": "gen.6.1", "layer": "sod", "type": "watchers_enedochic",
     "strength": 0.7, "confidence": 0.65, "note": "1 Enoch's Watcher tradition expands Genesis 6:1-4 — sons of God as fallen angels"},
    {"source": "1en.7.1", "target": "gen.6.4", "layer": "sod", "type": "watchers_enedochic",
     "strength": 0.7, "confidence": 0.65, "note": "1 Enoch describes the giants (Nephilim) as offspring of Watchers and human women"},
    {"source": "1en.10.4", "target": "gen.6.5", "layer": "sod", "type": "watchers_enedochic",
     "strength": 0.65, "confidence": 0.6, "note": "God commands the binding of Azazel — judgment on the Watchers"},
    # 1 Enoch → 2 Peter 2 (angels sinned)
    {"source": "1en.6.1", "target": "2pet.2.4", "layer": "sod", "type": "watchers_enedochic",
     "strength": 0.8, "confidence": 0.75, "note": "2 Peter 2:4 references angels who sinned — directly alludes to 1 Enoch's Watcher tradition"},
    # 1 Enoch → Jude 14-15 (Enoch prophesied)
    {"source": "1en.1.9", "target": "jude.1.14", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.95, "confidence": 0.9, "note": "Jude 14-15 directly quotes 1 Enoch 1:9: 'Behold, the Lord comes with ten thousands of his holy ones'"},
    {"source": "1en.1.9", "target": "jude.1.15", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.95, "confidence": 0.9, "note": "Jude quotes 1 Enoch 1:9 verbatim regarding judgment on the ungodly"},
    # Book of Giants → Genesis 6
    {"source": "bookgiants.1.1", "target": "gen.6.4", "layer": "sod", "type": "watchers_enedochic",
     "strength": 0.6, "confidence": 0.5, "note": "Book of Giants (4Q530) expands the Watcher tradition found in Genesis 6:1-4"},

    # ═══════════════════════════════════════════════════════════════
    # 2. DUALISM — TWO SPIRITS (1QS 3-4)
    # ═══════════════════════════════════════════════════════════════
    # 1QS 3:13-4:26 (Two Spirits) → John 1:5 (light shines in darkness)
    {"source": "dss.1QS.13", "target": "john.1.5", "layer": "sod", "type": "divine_council",
     "strength": 0.55, "confidence": 0.4, "note": "1QS Two Spirits teaching: light vs darkness parallels John's light/darkness dualism"},
    # 1QS 3:13 → John 3:19 (men loved darkness)
    {"source": "dss.1QS.13", "target": "john.3.19", "layer": "sod", "type": "divine_council",
     "strength": 0.5, "confidence": 0.4, "note": "Community's 'sons of light' vs 'sons of darkness' parallels Johannine dualism"},
    # 1QS 4:23 (spirits struggle in hearts) → Romans 7 (war within)
    {"source": "dss.1QS.23", "target": "rom.7.23", "layer": "sod", "type": "divine_council",
     "strength": 0.45, "confidence": 0.35, "note": "Both describe an internal struggle between truth and falsehood, spirit and flesh"},
    # 1QS 3:18-19 (Prince of Light / Angel of Darkness) → 2 Cor 11:14
    {"source": "dss.1QS.18", "target": "2cor.11.14", "layer": "sod", "type": "divine_council",
     "strength": 0.5, "confidence": 0.4, "note": "Angel of Darkness disguises as light — parallel to Satan as angel of light"},

    # ═══════════════════════════════════════════════════════════════
    # 3. COMMUNITY AS TEMPLE (1QS 8-9)
    # ═══════════════════════════════════════════════════════════════
    # 1QS 8:5-6 (Council of Community as Holy of Holies) → 1 Cor 3:16
    {"source": "dss.1QS.196", "target": "1cor.3.16", "layer": "sod", "type": "temple_microcosm",
     "strength": 0.7, "confidence": 0.55, "note": "Both describe the community/assembly as God's temple — 'you are God's temple'"},
    # 1QS 8:5-6 → Eph 2:19-22 (household of God)
    {"source": "dss.1QS.196", "target": "eph.2.21", "layer": "sod", "type": "temple_microcosm",
     "strength": 0.65, "confidence": 0.5, "note": "Community as 'House of Holiness' and 'Most Holy Dwelling' parallels Eph 2:21"},
    # 1QS 9:3-5 (atonement without blood) → Heb 13:15 (sacrifice of praise)
    {"source": "dss.1QS.208", "target": "heb.13.15", "layer": "sod", "type": "temple_microcosm",
     "strength": 0.6, "confidence": 0.5, "note": "Both describe prayer and right conduct as substitutionary sacrifice"},
    # 1QS 8:13-14 (prepare the way in the wilderness) → Matt 3:3 / Mark 1:3
    {"source": "dss.1QS.200", "target": "matt.3.3", "layer": "intertextual", "type": "allusion",
     "strength": 0.8, "confidence": 0.7, "note": "Both interpret Isaiah 40:3 as a call to prepare the way — Qumran: study of Law, NT: John the Baptist"},

    # ═══════════════════════════════════════════════════════════════
    # 4. MELCHIZEDEK (11Q13)
    # ═══════════════════════════════════════════════════════════════
    # 11Q13 column 2 (Melchizedek as heavenly deliverer) → Heb 7
    {"source": "dss.11Q13.2", "target": "heb.7.1", "layer": "sod", "type": "heavenly_ascent",
     "strength": 0.7, "confidence": 0.55, "note": "Both identify Melchizedek as a heavenly/priestly figure beyond normal priesthood"},
    # 11Q13 → Psalm 110:4 (shared prooftext)
    {"source": "dss.11Q13.2", "target": "psa.110.4", "layer": "intertextual", "type": "allusion",
     "strength": 0.7, "confidence": 0.6, "note": "11Q13 and Hebrews both use Psalm 110:4 as core text for Melchizedek's eternal priesthood"},
    # 11Q13 → Lev 25 (Jubilee — shared theme)
    {"source": "dss.11Q13.1", "target": "lev.25.10", "layer": "sod", "type": "temple_ascent",
     "strength": 0.6, "confidence": 0.5, "note": "11Q13 interprets the Jubilee as eschatological release, drawing on Leviticus 25"},

    # ═══════════════════════════════════════════════════════════════
    # 5. MESSIANIC APOCALYPSE (4Q521)
    # ═══════════════════════════════════════════════════════════════
    # 4Q521 frag 2 (Messiah heals, raises dead, preaches) → Matt 11:5
    {"source": "dss.4Q521.1", "target": "matt.11.5", "layer": "intertextual", "type": "allusion",
     "strength": 0.85, "confidence": 0.75, "note": "4Q521 lists the messianic works: heal sick, raise dead, preach to poor — Jesus cites exact same list in response to John Baptist"},
    # 4Q521 → Luke 7:22 (same list)
    {"source": "dss.4Q521.1", "target": "luke.7.22", "layer": "intertextual", "type": "allusion",
     "strength": 0.85, "confidence": 0.75, "note": "Same messianic works list in Luke's parallel account"},
    # 4Q521 → Isa 35:5-6 (source of the list)
    {"source": "dss.4Q521.1", "target": "isa.35.5", "layer": "intertextual", "type": "echo",
     "strength": 0.6, "confidence": 0.55, "note": "4Q521's list echoes Isaiah 35:5-6 (blind see, deaf hear, lame leap)"},

    # ═══════════════════════════════════════════════════════════════
    # 6. SON OF GOD ARAMAIC APOCALYPSE (4Q246)
    # ═══════════════════════════════════════════════════════════════
    # 4Q246 col 1 → Luke 1:32-35 (Son of God / Son of the Most High)
    {"source": "dss.4Q246.1", "target": "luke.1.32", "layer": "intertextual", "type": "allusion",
     "strength": 0.75, "confidence": 0.65, "note": "4Q246 calls figure 'Son of God' and 'Son of the Most High' — same titles as Gabriel uses for Jesus in Luke 1:32-35"},
    # 4Q246 → Daniel 7:13-14 (one like a son of man)
    {"source": "dss.4Q246.1", "target": "dan.7.13", "layer": "intertextual", "type": "echo",
     "strength": 0.7, "confidence": 0.6, "note": "4Q246's figure receives eternal kingdom — directly alludes to Daniel 7's son of man"},

    # ═══════════════════════════════════════════════════════════════
    # 7. SONGS OF THE SABBATH SACRIFICE (4Q400-407)
    # ═══════════════════════════════════════════════════════════════
    # 4Q403 → Isaiah 6:3 (Holy holy holy)
    {"source": "dss.4Q403.1", "target": "isa.6.3", "layer": "sod", "type": "hekhalot",
     "strength": 0.75, "confidence": 0.65, "note": "Songs of Sabbath Sacrifice includes angelic 'Holy holy holy' liturgy — same as Isaiah's temple vision"},
    # 4Q405 → Ezekiel 1 (chariot throne)
    {"source": "dss.4Q405.1", "target": "ezek.1.1", "layer": "sod", "type": "merkabah",
     "strength": 0.75, "confidence": 0.65, "note": "Songs of Sabbath Sacrifice uses merkabah (chariot-throne) imagery from Ezekiel's vision"},
    # 4Q400 → Revelation 4 (heavenly temple liturgy)
    {"source": "dss.4Q400.1", "target": "rev.4.8", "layer": "sod", "type": "hekhalot",
     "strength": 0.7, "confidence": 0.6, "note": "Angelic liturgy in Sabbath Songs parallels heavenly worship scenes in Revelation 4"},
    # 4Q405 → Revelation 4 (living creatures / angelic beings)
    {"source": "dss.4Q405.1", "target": "rev.4.6", "layer": "sod", "type": "hekhalot",
     "strength": 0.65, "confidence": 0.55, "note": "Angelic beings in Sabbath Songs parallel Revelation's four living creatures around the throne"},

    # ═══════════════════════════════════════════════════════════════
    # 8. JUBILEES
    # ═══════════════════════════════════════════════════════════════
    # Jubilees 23:11 (shortened lifespan) → already in 1QS
    {"source": "jub.23.11", "target": "dss.1QS.210", "layer": "intertextual", "type": "echo",
     "strength": 0.55, "confidence": 0.45, "note": "CD (Damascus Document) quotes Jubilees 23:11 on shortened lifespan — showing Jubilees was authoritative at Qumran"},
    # Jubilees 1:27-29 (Moses on Sinai) → Exodus 24
    {"source": "jub.1.27", "target": "exo.24.12", "layer": "intertextual", "type": "midrashic_connection",
     "strength": 0.6, "confidence": 0.5, "note": "Jubilees expands Moses' Sinai ascent with angelic revelation and the heavenly tablets motif"},

    # ═══════════════════════════════════════════════════════════════
    # 9. 1QS — PSEUDEPIGRAPHA CROSS-CANON
    # ═══════════════════════════════════════════════════════════════
    # 1QS 3:13-4:26 → Gospel of John (logos/light)
    {"source": "dss.1QS.14", "target": "john.1.9", "layer": "sod", "type": "divine_council",
     "strength": 0.45, "confidence": 0.35, "note": "Both describe a 'true light' that enlightens every man — conceptual parallel between Qumran's 'light of life' and John's 'true light'"},
    # 1QS 4:20-22 → Romans 8 (walk not after flesh)
    {"source": "dss.1QS.20", "target": "rom.8.4", "layer": "sod", "type": "divine_council",
     "strength": 0.45, "confidence": 0.35, "note": "Both contrast walking according to the spirit vs walking according to the flesh"},
    # 1QS 11:2-4 → 1 Cor 1:19-31 (boasting in God)
    {"source": "dss.1QS.260", "target": "1cor.1.31", "layer": "sod", "type": "temple_microcosm",
     "strength": 0.4, "confidence": 0.3, "note": "'My justification is with God' / 'Let him who boasts, boast in the Lord' — shared theme of humility before God"},
]


SON_OF_MAN = [
    # ═══════════════════════════════════════════════════════════════
    # 10. SON OF MAN TRAJECTORY — Daniel → Revelation → Abraham
    # ═══════════════════════════════════════════════════════════════
    # Daniel 7:13 → Revelation 1:13 (one like unto Son of Man)
    {"source": "dan.7.13", "target": "rev.1.13", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.9, "confidence": 0.85, "note": "Both use 'one like the Son of Man' — Daniel's prophecy of the heavenly figure is echoed in John's vision of the glorified Christ"},
    # Daniel 7:13 → Revelation 14:14 (Son of Man on cloud)
    {"source": "dan.7.13", "target": "rev.14.14", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.9, "confidence": 0.85, "note": "Both depict 'one like the Son of Man' on/with a cloud — Daniel's prophecy is reused in John's harvest vision"},
    # Daniel 7:13-14 → Abraham 3:27 (pre-mortal Son of Man)
    {"source": "dan.7.13", "target": "abraham.3.27", "layer": "intertextual", "type": "allusion",
     "strength": 0.8, "confidence": 0.75, "note": "Abraham 3:27 'one answered like unto the Son of Man' echoes Daniel 7:13 — the same pre-mortal/divine figure who receives dominion"},
    # Daniel 7:14 → Abraham 3:27 (dominion / foreordination)
    {"source": "dan.7.14", "target": "abraham.3.27", "layer": "symbolic", "type": "person_type",
     "strength": 0.75, "confidence": 0.65, "note": "The Son of Man who receives all dominion in Daniel 7 is the same figure who volunteers in Abraham 3:27 — 'Here am I, send me'"},
    # Revelation 1:13 → Abraham 3:27 (glorified Son of Man)
    {"source": "rev.1.13", "target": "abraham.3.27", "layer": "symbolic", "type": "person_type",
     "strength": 0.7, "confidence": 0.6, "note": "The glorified Son of Man in Revelation 1:13 is the same figure who answered 'like unto the Son of Man' in Abraham 3:27"},
    # Daniel 7:13 → Matthew 26:64 (Son of Man at God's right hand)
    {"source": "dan.7.13", "target": "matt.26.64", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.95, "confidence": 0.9, "note": "Jesus quotes Daniel 7:13 directly at his trial: 'Ye shall see the Son of Man sitting on the right hand of power, and coming in the clouds of heaven'"},
    # Daniel 7:13 → Mark 14:62 (parallel account)
    {"source": "dan.7.13", "target": "mark.14.62", "layer": "intertextual", "type": "direct_quotation",
     "strength": 0.95, "confidence": 0.9, "note": "Jesus quotes Daniel 7:13 at his trial before the Sanhedrin"},
    # Revelation 1:14 (white hair like wool) → Daniel 7:9 (Ancient of Days)
    {"source": "rev.1.14", "target": "dan.7.9", "layer": "intertextual", "type": "allusion",
     "strength": 0.85, "confidence": 0.75, "note": "John describes the Son of Man with 'hair white like wool' — directly borrowing the Ancient of Days description from Daniel 7:9"},
    # Abraham 3:22-23 → Revelation (book of life / foreordination)
    {"source": "abraham.3.22", "target": "rev.13.8", "layer": "intertextual", "type": "echo",
     "strength": 0.55, "confidence": 0.45, "note": "Abraham's vision of foreordained intelligences parallels Revelation's 'Lamb slain from the foundation of the world'"},
]

def main():
    conn = get_db()
    count = 0
    
    print("Seeding cross-canon connections...")
    for c in CONNECTIONS + SON_OF_MAN:
        existing = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type=?",
            (c["source"], c["target"], c["type"])
        ).fetchone()[0]
        
        if existing == 0:
            try:
                add_connection(conn, c["source"], c["target"],
                              layer=c["layer"],
                              type_name=c["type"],
                              subtype="",
                              strength=c["strength"],
                              confidence=c["confidence"],
                              discovered_by="human",
                              metadata=json.dumps({
                                  "note": c["note"][:200],
                                  "tag": "dss_cross_canon"
                              }))
                count += 1
            except Exception as e:
                print(f"  ERROR: {c['source']} → {c['target']}: {e}")
        else:
            pass  # already exists
    
    conn.commit()
    print(f"  Created {count} new connections")
    print(f"  Total DSS cross-canon connections: {count}")
    conn.close()


if __name__ == '__main__':
    main()
