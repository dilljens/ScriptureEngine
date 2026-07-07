"""Sod Fill generator — populates sparse sod connection types.

Targets types with < 10 connections:
  - mercy_seat: kapporet typology (Exodus 25 → Hebrews 9)
  - heavenly_council: divine council scenes
  - theophany: visible manifestations of God
  - divine_mediator: mediator figures (Moses, Melchizedek, Christ)
  - holy_of_holies: access to the inner sanctuary
  - kingdom_priesthood: royal priesthood / Melchizedek
  - divine_marriage: temple as divine marriage
  - theosis: becoming divine through covenant
"""

import json
from lib.db import add_connection

META = json.dumps({"generator": "sod_fill"}, ensure_ascii=False)


# ─── Mercy Seat (kapporet) typology ───
MERCY_SEAT = [
    ("exo.25.17", "exo.25.22", "The mercy seat (kapporet) on the ark — the place where God meets with man"),
    ("exo.37.6", "lev.16.2", "The mercy seat overshadowed by cherubim — accessed only on Day of Atonement"),
    ("lev.16.14", "heb.9.5", "Blood sprinkled on the mercy seat — Christ's blood fulfills this"),
    ("heb.9.5", "rom.3.25", "Paul calls Christ a 'propitiation' (hilasterion = mercy seat)"),
    ("rom.3.25", "1john.2.2", "Christ is the propitiation for our sins — the same mercy seat concept"),
    ("exo.25.17", "heb.9.5", "The earthly mercy seat as a type of heaven's throne of grace"),
    ("lev.16.14", "heb.4.16", "Access to the mercy seat through blood — boldly approach the throne of grace"),
]

# ─── Heavenly Council — divine assembly scenes ───
HEAVENLY_COUNCIL = [
    ("1kgs.22.19", "job.1.6", "Micaiah sees the Lord on His throne with the host of heaven — same council scene as Job"),
    ("job.1.6", "job.2.1", "Satan (the adversary) appears among the sons of God in the council"),
    ("job.1.6", "psa.82.1", "God stands in the divine assembly — He judges among the gods"),
    ("psa.82.1", "psa.89.7", "God is feared in the council of the holy ones"),
    ("isa.6.1", "1kgs.22.19", "Isaiah's temple vision is a council scene — seraphim as the divine court"),
    ("jer.23.18", "job.15.8", "Who has stood in the council of the Lord?"),
    ("1kgs.22.19", "dan.7.10", "The Ancient of Days surrounded by thousands — the eschatological council"),
    ("dan.7.10", "rev.5.11", "Daniel's heavenly court and John's vision of the throne room"),
    ("1kgs.22.19", "rev.4.2", "Heavenly throne scene — the council witnesses God's judgments"),
]

# ─── Theophany — divine manifestations ───
THEOPHANY = [
    ("exo.3.2", "exo.3.6", "The Angel of YHWH appears in the burning bush — Moses hides his face"),
    ("exo.13.21", "exo.14.24", "Pillar of cloud and fire leading Israel — visible manifestation of divine presence"),
    ("exo.19.18", "exo.20.18", "Sinai theophany — fire, smoke, quaking, trumpet"),
    ("exo.33.18", "exo.34.6", "God passes before Moses proclaiming His name — the mercy and justice of God"),
    ("isa.6.1", "exo.24.10", "Isaiah sees the Lord high and lifted up — Moses and elders saw the God of Israel"),
    ("ezek.1.4", "ezek.1.28", "Ezekiel's vision of the divine chariot-throne — the merkabah theophany"),
    ("ezek.1.28", "rev.1.13", "Ezekiel's glory of the Lord → John's Son of Man — same divine appearance"),
    ("dan.7.9", "ezek.1.27", "Ancient of Days and Ezekiel's electrum man — same divine appearance"),
    ("dan.7.9", "rev.4.2", "Daniel's Ancient of Days vision → John's throne vision"),
    ("exo.24.10", "rev.4.3", "Sapphire pavement under God's feet → jasper and sardius stone around the throne"),
]

# ─── Divine Mediator — figures who stand between God and man ───
DIVINE_MEDIATOR = [
    ("exo.32.30", "exo.32.32", "Moses offers his own life as atonement — a mediator between God and Israel"),
    ("exo.32.32", "rom.9.3", "Moses wishes to be blotted out for Israel → Paul wishes himself accursed for his brethren"),
    ("exo.32.30", "heb.8.6", "Moses as mediator of the old covenant → Christ as mediator of the new"),
    ("exo.32.32", "1tim.2.5", "Moses' intercession foreshadows the one mediator between God and men"),
    ("gen.14.18", "heb.7.1", "Melchizedek as priest of the Most High → Christ as high priest after Melchizedek's order"),
    ("heb.7.25", "rom.8.34", "Christ ever lives to make intercession for us"),
    ("num.16.48", "num.16.48", "Aaron stands between the living and the dead with his censer — a type of mediation"),
    ("1sam.12.23", "jer.15.1", "Samuel and Moses as intercessors — powerful mediatorial figures"),
]

# ─── Holy of Holies — access to the inner sanctuary ───
HOLY_OF_HOLIES = [
    ("exo.26.33", "lev.16.2", "The veil separates the holy place from the most holy — only the high priest enters"),
    ("lev.16.2", "heb.9.3", "The second veil leads to the Holy of Holies — Christ enters the true one"),
    ("exo.26.31", "matt.27.51", "The veil of the temple was rent — access to the Holy of Holies opened"),
    ("lev.16.12", "heb.9.7", "The high priest enters with blood — Christ enters with his own blood"),
    ("exo.25.22", "heb.9.24", "Mercy seat in the earthly Holy of Holies → heaven itself"),
    ("1kgs.6.16", "rev.11.19", "The oracle (inner sanctuary) of Solomon's temple → the heavenly temple opened"),
    ("1kgs.8.6", "rev.15.5", "The ark in the Holy of Holies → the temple of the tabernacle in heaven"),
]

# ─── Kingdom Priesthood / Melchizedek ───
KINGDOM_PRIESTHOOD = [
    ("exo.19.6", "1pet.2.9", "Israel called a kingdom of priests → believers are a royal priesthood"),
    ("exo.19.6", "rev.1.6", "A kingdom of priests → Christ has made us kings and priests unto God"),
    ("exo.19.6", "rev.5.10", "Kings and priests on the earth — the same promise fulfilled"),
    ("1pet.2.5", "1pet.2.9", "A holy priesthood → a royal priesthood — the identity of believers"),
    ("gen.14.18", "psa.110.4", "Melchizedek, king of Salem and priest of God → priesthood forever"),
    ("psa.110.4", "heb.5.6", "Psalm 110 quoted in Hebrews — the Melchizedek priesthood of Christ"),
    ("isa.61.6", "rev.20.6", "Priests of the Lord → priests of God and of Christ"),
    ("num.3.10", "exo.40.15", "The Aaronic priesthood — guardians of the sanctuary"),
]

# ─── Divine Marriage — hieros gamos ───
DIVINE_MARRIAGE = [
    ("isa.54.5", "jer.31.32", "God as husband to Israel — the marriage covenant"),
    ("jer.31.32", "hos.2.16", "The marriage bond between God and His people"),
    ("hos.2.19", "isa.62.5", "God betroths Israel in righteousness — as a bridegroom rejoices over his bride"),
    ("rev.19.7", "rev.21.2", "The marriage of the Lamb — the church as the bride"),
    ("rev.19.7", "matt.22.2", "The marriage supper of the Lamb — the kingdom as a wedding feast"),
    ("isa.54.5", "rev.21.2", "God as husband in the old covenant → the New Jerusalem as the bride"),
    ("song.3.11", "rev.19.7", "The marriage of Solomon — type of the marriage of the Lamb"),
    ("eph.5.32", "gen.2.24", "Paul calls marriage a great mystery concerning Christ and the church"),
]


# ─── Theosis — becoming divine through covenant ───
THEOSIS = [
    ("psa.82.6", "john.10.34", "'Ye are gods, children of the Most High' — Jesus quotes this"),
    ("john.10.34", "2pet.1.4", "Partakers of the divine nature — the basis of theosis"),
    ("psa.82.6", "1john.3.2", "Sons of God — we shall be like Him"),
    ("2pet.1.4", "rom.8.17", "Partakers of divine nature → joint-heirs with Christ"),
    ("1john.3.2", "eph.4.13", "We shall see Him as He is → the measure of the fullness of Christ"),
    ("rom.8.17", "heb.12.10", "Joint-heirs with Christ → partakers of His holiness"),
    ("gen.1.26", "1john.3.2", "Made in God's image → we shall be like Him — theosis from beginning to eschaton"),
    ("moses.1.39", "dc.76.58", "God's work and glory — to bring to pass the immortality and eternal life of man"),
]

# ─── Angelophanies — angelic theophany / divine messenger appearances ───
ANGELOPHANY = [
    ("gen.16.7", "gen.16.13", "Angel of YHWH appears to Hagar — she names God 'El Roi' (the God who sees)"),
    ("gen.18.1", "gen.18.2", "Three men appear to Abraham — one is YHWH himself"),
    ("gen.22.11", "gen.22.15", "Angel of YHWH stops Abraham — speaks as God ('I know that you fear God')"),
    ("gen.32.24", "gen.32.30", "Jacob wrestles with a man — 'I have seen God face to face'"),
    ("exo.3.2", "exo.3.6", "Angel of YHWH in the bush — identified as the God of Abraham, Isaac, and Jacob"),
    ("exo.14.19", "exo.14.24", "Angel of God leads Israel — the pillar of cloud is the angel of His Presence"),
    ("josh.5.13", "josh.5.15", "Captain of the Lord's host appears to Joshua — holy ground"),
    ("judg.6.11", "judg.6.22", "Angel of YHWH appears to Gideon — 'I have seen the angel of the Lord face to face'"),
    ("judg.13.3", "judg.13.22", "Angel of YHWH appears to Manoah and his wife — 'We have seen God'"),
    ("1kgs.19.5", "1kgs.19.8", "Angel of YHWH appears to Elijah — twice touches him"),
    ("dan.3.25", "dan.3.28", "The fourth man in the fire — 'like the Son of God', God sent his angel and delivered"),
    ("dan.10.5", "dan.10.10", "The man in linen — a divine messenger who receives worship"),
]

ALL_GROUPS = {
    "mercy_seat": (MERCY_SEAT, 0.6, 0.5),
    "heavenly_council": (HEAVENLY_COUNCIL, 0.6, 0.5),
    "theophany": (THEOPHANY, 0.6, 0.5),
    "divine_mediator": (DIVINE_MEDIATOR, 0.55, 0.45),
    "holy_of_holies": (HOLY_OF_HOLIES, 0.6, 0.5),
    "kingdom_priesthood": (KINGDOM_PRIESTHOOD, 0.55, 0.45),
    "divine_marriage": (DIVINE_MARRIAGE, 0.55, 0.45),
    "theosis": (THEOSIS, 0.55, 0.45),
    "angelophany": (ANGELOPHANY, 0.7, 0.6),
}


def run(conn, book_ids=None):
    total = 0
    for type_name, (pairs, strength, confidence) in ALL_GROUPS.items():
        count = 0
        for src, tgt, note in pairs:
            existing = conn.execute(
                "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type=?",
                (src, tgt, type_name)
            ).fetchone()[0]
            if existing == 0:
                try:
                    add_connection(conn, src, tgt,
                                  layer="sod",
                                  type_name=type_name,
                                  subtype="",
                                  strength=strength,
                                  confidence=confidence,
                                  discovered_by="human",
                                  metadata=json.dumps({
                                      "note": note[:200],
                                      "generator": "sod_fill"
                                  }, ensure_ascii=False))
                    count += 1
                except Exception as e:
                    pass
        conn.commit()
        total += count
        print(f"  {type_name:25s}: {count} connections")
    print(f"  Total sod fill connections: {total}")
    return total
