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


# ═══════════════════════════════════════════════════════════════
# 10A. ONE LIKE UNTO THE SON OF MAN — a distinct divine figure
#     (potentially Michael). NOT Christ — see 10B for Christ as Son of Man.
#     Connects the figure who appears in Daniel 7, Revelation 1 & 14,
#     and Abraham 3, using the distinctive phrase "one like unto the Son of Man."
# ═══════════════════════════════════════════════════════════════
# Theological note: "one LIKE unto" = a being who resembles/appears-as
# the Son of Man but may be a distinct personage (Michael/Adam).
# Christ IS the Son of Man (his own title). The distinction is between
# appearance (like unto) and identity (is).
# ═══════════════════════════════════════════════════════════════

ONE_LIKE_UNTO_SON_OF_MAN = [
    # Daniel 7:13 → Revelation 1:13 (same distinctive phrase)
    {"source": "dan.7.13", "target": "rev.1.13", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.9, "confidence": 0.85,
     "note": "Both use 'one LIKE the Son of Man' / 'one LIKE unto the Son of Man' — the same distinctive phrase for a divine being appearing in human-like form. NOT necessarily Christ (who IS the Son of Man, not like one)."},
    # Daniel 7:13 → Revelation 14:14 (same phrase, cloud imagery)
    {"source": "dan.7.13", "target": "rev.14.14", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.9, "confidence": 0.85,
     "note": "Both depict 'one like the Son of Man' on/with a cloud. The cloud is a divine chariot-throne merkabah motif. This figure comes TO the Ancient of Days — he is NOT the Ancient of Days."},
    # Daniel 7:13-14 → Abraham 3:27 (pre-mortal divine figure)
    {"source": "dan.7.13", "target": "abraham.3.27", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.85, "confidence": 0.8,
     "note": "Abraham 3:27 'one answered LIKE unto the Son of Man: Here am I, send me' echoes Daniel 7:13 'one LIKE the Son of Man came with the clouds.' Same distinctive phrase. This is Michael/Adam who volunteers, not Christ who is sent."},
    # Revelation 1:13 → Abraham 3:27 (same phrase in vision)
    {"source": "rev.1.13", "target": "abraham.3.27", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.7, "confidence": 0.65,
     "note": "Both John and Abraham see a figure 'like unto the Son of Man' in the divine council. This is the same figure — Michael/Adam — who stands as the 'one like' in the presence of God."},
    # Revelation 1:14 → Daniel 7:9 (Ancient of Days imagery)
    {"source": "rev.1.14", "target": "dan.7.9", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.85, "confidence": 0.75,
     "note": "John borrows the Ancient of Days description (white hair like wool, throne of fire) to describe the 'one like unto the Son of Man.' This shows the 'one like' shares in the divine appearance but is a distinct figure. NOT the Father (Ancient of Days) and NOT the Son (Son of Man)."},
    # Revelation 14:14 → Abraham 3:27 (harvest / volunteer)
    {"source": "rev.14.14", "target": "abraham.3.27", "layer": "sod", "type": "name_symbolic",
     "subtype": "one_like_unto_son_of_man",
     "strength": 0.65, "confidence": 0.55,
     "note": "The 'one like unto the Son of Man' in both visions serves a critical role in the divine plan. Abraham sees him volunteer; John sees him executing the harvest judgment."},
]

# ═══════════════════════════════════════════════════════════════
# 10B. SON OF MAN — Christ's self-title
#     Jesus consistently calls himself "the Son of Man" in the Gospels.
#     This is his OWN title. It derives from Daniel 7 but Jesus applies
#     it to himself (Matthew 26:64), identifying himself as the figure
#     from Daniel's vision. In Ezekiel, ben-adam = mortal, but Christ
#     transforms it into a divine title.
# ═══════════════════════════════════════════════════════════════

SON_OF_MAN_CHRIST = [
    # Daniel 7:13 → Matthew 26:64 (Jesus applies Daniel's figure to himself)
    {"source": "dan.7.13", "target": "matt.26.64", "layer": "intertextual", "type": "direct_quotation",
     "subtype": "son_of_man_christ",
     "strength": 0.95, "confidence": 0.9,
     "note": "Jesus explicitly quotes Daniel 7:13 at his trial, applying the 'one like the Son of Man' to HIMSELF. This is the hermeneutical key: Jesus identifies himself as the Son of Man figure from Daniel 7."},
    # Daniel 7:13 → Mark 14:62 (parallel)
    {"source": "dan.7.13", "target": "mark.14.62", "layer": "intertextual", "type": "direct_quotation",
     "subtype": "son_of_man_christ",
     "strength": 0.95, "confidence": 0.9,
     "note": "Jesus quotes Daniel 7:13 at his trial before the Sanhedrin in Mark's parallel account."},
    # Matthew 26:64 → Acts 7:56 (Son of Man standing)
    {"source": "matt.26.64", "target": "acts.7.56", "layer": "intertextual", "type": "allusion",
     "subtype": "son_of_man_christ",
     "strength": 0.8, "confidence": 0.7,
     "note": "Stephen sees the Son of Man 'standing on the right hand of God' — the same figure Jesus identified himself as: the Son of Man who received dominion in Daniel 7."},
    # Ezekiel's son-of-man (prophetic title) → Jesus' Son of Man (divine title)
    {"source": "ezek.2.1", "target": "matt.8.20", "layer": "intertextual", "type": "midrashic_connection",
     "subtype": "son_of_man_christ",
     "strength": 0.4, "confidence": 0.3,
     "note": "Ezekiel is called 'son of man' (ben-adam = mortal) 93 times. Jesus takes this phrase and transforms it into his distinctive divine title. The continuity is in the phrase, the discontinuity is in meaning."},
    # Revelation 14:14 → Matthew 13:41 (Son of Man harvest/angels)
    {"source": "rev.14.14", "target": "matt.13.41", "layer": "intertextual", "type": "echo",
     "subtype": "son_of_man_christ",
     "strength": 0.5, "confidence": 0.4,
     "note": "The Son of Man sends forth his angels to gather the harvest — Jesus teaches this in the parable of the wheat and tares, and Revelation 14 shows it in vision. Different figures, same function."},
    # Christ as Son of Man (Daniel 7:13-14 fulfilled in Christ)
    {"source": "dan.7.14", "target": "rev.11.15", "layer": "intertextual", "type": "echo",
     "subtype": "son_of_man_christ",
     "strength": 0.7, "confidence": 0.6,
     "note": "The dominion given to the 'one like the Son of Man' in Daniel 7 finds ultimate fulfillment in Christ's eternal kingdom proclaimed in Revelation 11:15."},
    # The Son of Man's coming on clouds (Christ's own words)
    {"source": "matt.24.30", "target": "dan.7.13", "layer": "intertextual", "type": "direct_quotation",
     "subtype": "son_of_man_christ",
     "strength": 0.9, "confidence": 0.85,
     "note": "Jesus describes his own return as the Son of Man 'coming on the clouds of heaven' — directly quoting Daniel 7:13 and identifying himself as that figure."},
]

def main():
    conn = get_db()
    count = 0
    
    all_connections = CONNECTIONS + ONE_LIKE_UNTO_SON_OF_MAN + SON_OF_MAN_CHRIST
    print(f"Seeding {len(all_connections)} cross-canon connections...")
    for c in all_connections:
        subtype = c.get("subtype", "")
        existing = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type=? AND subtype=?",
            (c["source"], c["target"], c["type"], subtype)
        ).fetchone()[0]
        
        if existing == 0:
            try:
                add_connection(conn, c["source"], c["target"],
                              layer=c["layer"],
                              type_name=c["type"],
                              subtype=subtype,
                              strength=c["strength"],
                              confidence=c["confidence"],
                              discovered_by="human",
                              metadata=json.dumps({
                                  "note": c["note"][:200],
                                  "tag": "son_of_man_trajectory"
                              }, ensure_ascii=False))
                count += 1
            except Exception as e:
                print(f"  ERROR: {c['source']} → {c['target']}: {e}")
        else:
            pass  # already exists
    
    conn.commit()
    print(f"  Created {count} new connections")
    print(f"  Total connections seeded: {count}")
    conn.close()


if __name__ == '__main__':
    main()
