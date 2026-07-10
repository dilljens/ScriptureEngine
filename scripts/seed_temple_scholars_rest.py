#!/usr/bin/env python3
"""Seed connections from 16 temple/scholars scholars."""

import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

CONNECTIONS = [
    # === 1. Levenson (levenson_temple) ===
    {"from_verse": "gen.1.1", "to_verse": "psa.74.12", "type": "typology", "subtype": "levenson_temple", "strength": 0.85, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "God's kingship over creation through his defeat of chaos — creation as temple building"}},
    {"from_verse": "psa.74.12", "to_verse": "isa.27.1", "type": "typology", "subtype": "levenson_temple", "strength": 0.85, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "YHWH's victory over Leviathan — Chaoskampf as the establishment of the cosmic temple"}},
    {"from_verse": "gen.1.1", "to_verse": "1kgs.8.12", "type": "typology", "subtype": "levenson_temple", "strength": 0.8, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "The temple as a microcosm of creation — Solomon declares YHWH dwells in thick darkness, the same cloud that covered Sinai"}},
    {"from_verse": "psa.48.1", "to_verse": "psa.46.4", "type": "typology", "subtype": "levenson_temple", "strength": 0.8, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "Zion as the cosmic mountain — there is a river whose streams make glad the city of God"}},
    {"from_verse": "exo.15.17", "to_verse": "psa.74.2", "type": "typology", "subtype": "levenson_temple", "strength": 0.85, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "Mount Zion as God's dwelling place — the goal of the Exodus is the temple mountain"}},
    {"from_verse": "gen.1.1", "to_verse": "isa.51.9", "type": "typology", "subtype": "levenson_temple", "strength": 0.85, "metadata": {"scholar": "Jon D. Levenson", "source": "Sinai & Zion / Creation and the Persistence of Evil", "tag": "levenson_temple", "note": "Awake, awake, put on strength, O arm of the Lord — creation as a victory over chaos and establishment of order"}},

    # === 2. Nibley (nibley_temple) ===
    {"from_verse": "gen.1.1", "to_verse": "exo.25.40", "type": "typology", "subtype": "nibley_temple", "strength": 0.85, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "The temple as a replica of the cosmos — ancient temple building was always a re-creation of the universe"}},
    {"from_verse": "gen.28.12", "to_verse": "john.1.51", "type": "typology", "subtype": "nibley_temple", "strength": 0.9, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "Jacob's ladder as axis mundi — the temple as the point of connection between heaven and earth"}},
    {"from_verse": "gen.28.12", "to_verse": "psa.24.3", "type": "typology", "subtype": "nibley_temple", "strength": 0.8, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "The ascent of the mountain/ladder — temples across cultures share the ascent motif as access to the divine presence"}},
    {"from_verse": "exo.25.1", "to_verse": "rev.21.1", "type": "typology", "subtype": "nibley_temple", "strength": 0.85, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "Ancient temples across cultures replicate the cosmos and anticipate the heavenly temple"}},
    {"from_verse": "gen.1.1", "to_verse": "psa.48.1", "type": "typology", "subtype": "nibley_temple", "strength": 0.8, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "Zion as cosmic mountain — temples throughout the ancient world were built on high places as sacred centers"}},
    {"from_verse": "rev.21.2", "to_verse": "gen.2.8", "type": "typology", "subtype": "nibley_temple", "strength": 0.85, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "The New Jerusalem as a restored paradise — temples throughout history represent the original garden"}},
    {"from_verse": "ezek.40.1", "to_verse": "exo.25.9", "type": "typology", "subtype": "nibley_temple", "strength": 0.85, "metadata": {"scholar": "Hugh Nibley", "source": "Temple and Cosmos", "tag": "nibley_temple", "note": "Ezekiel's temple vision and the tabernacle pattern — both shown on the mount, both revealed from heaven"}},

    # === 3. Dempster (dempster_dominion) ===
    {"from_verse": "gen.1.26", "to_verse": "psa.8.4", "type": "typology", "subtype": "dempster_dominion", "strength": 0.85, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "Dominion — humanity created to rule as God's vice-regents, a royal priesthood in God's cosmic temple"}},
    {"from_verse": "gen.1.26", "to_verse": "1pet.2.9", "type": "typology", "subtype": "dempster_dominion", "strength": 0.85, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "A royal priesthood — the original dominion mandate is fulfilled in the church"}},
    {"from_verse": "gen.12.1", "to_verse": "deu.12.1", "type": "typology", "subtype": "dempster_dominion", "strength": 0.8, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "Dynasty — the Abrahamic promise of land and seed leads to the Davidic dynasty"}},
    {"from_verse": "gen.12.1", "to_verse": "psa.132.11", "type": "typology", "subtype": "dempster_dominion", "strength": 0.85, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "The dynasty promise — from Abraham to David, the seed becomes the king who builds the temple"}},
    {"from_verse": "gen.1.26", "to_verse": "exo.19.6", "type": "typology", "subtype": "dempster_dominion", "strength": 0.85, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "A kingdom of priests — Adam's royal priesthood is restored at Sinai"}},
    {"from_verse": "exo.19.6", "to_verse": "rev.5.10", "type": "typology", "subtype": "dempster_dominion", "strength": 0.85, "metadata": {"scholar": "Stephen Dempster", "source": "Dominion and Dynasty", "tag": "dempster_dominion", "note": "And hath made us kings and priests unto God — the fulfillment of the dominion mandate"}},

    # === 4. Walton (walton_cosmic) ===
    {"from_verse": "gen.1.1", "to_verse": "exo.20.11", "type": "typology", "subtype": "walton_cosmic", "strength": 0.85, "metadata": {"scholar": "John H. Walton", "source": "The Lost World of Genesis One", "tag": "walton_cosmic", "note": "In six days the LORD made heaven and earth — the creation week as a temple dedication ceremony"}},
    {"from_verse": "gen.1.1", "to_verse": "psa.132.8", "type": "typology", "subtype": "walton_cosmic", "strength": 0.85, "metadata": {"scholar": "John H. Walton", "source": "The Lost World of Genesis One", "tag": "walton_cosmic", "note": "Arise, O LORD, into thy rest — God's rest on the seventh day is his enthronement in the cosmic temple"}},
    {"from_verse": "gen.2.2", "to_verse": "exo.31.17", "type": "typology", "subtype": "walton_cosmic", "strength": 0.85, "metadata": {"scholar": "John H. Walton", "source": "The Lost World of Genesis One", "tag": "walton_cosmic", "note": "God rested on the seventh day — the Sabbath as temple inauguration, God taking up residence"}},
    {"from_verse": "gen.1.1", "to_verse": "isa.66.1", "type": "typology", "subtype": "walton_cosmic", "strength": 0.8, "metadata": {"scholar": "John H. Walton", "source": "The Lost World of Genesis One", "tag": "walton_cosmic", "note": "Heaven is my throne and earth is my footstool — the cosmos as God's temple"}},
    {"from_verse": "gen.1.1", "to_verse": "psa.11.4", "type": "typology", "subtype": "walton_cosmic", "strength": 0.8, "metadata": {"scholar": "John H. Walton", "source": "The Lost World of Genesis One", "tag": "walton_cosmic", "note": "The LORD is in his holy temple — the cosmic temple is where God dwells"}},

    # === 5. Rowland / DeConick (rowland_apocalyptic / deconick_mystic) ===
    {"from_verse": "ezek.1.1", "to_verse": "rev.1.10", "type": "typology", "subtype": "rowland_apocalyptic", "strength": 0.85, "metadata": {"scholar": "Christopher Rowland", "source": "The Open Heaven", "tag": "rowland_apocalyptic", "note": "The heavenly sanctuary vision as apocalyptic template — Ezekiel's merkabah opens the door for John's apocalypse"}},
    {"from_verse": "ezek.1.1", "to_verse": "ezek.10.1", "type": "typology", "subtype": "rowland_apocalyptic", "strength": 0.9, "metadata": {"scholar": "Christopher Rowland", "source": "The Open Heaven", "tag": "rowland_apocalyptic", "note": "Ezekiel's vision of the chariot-throne — the template for apocalyptic mysticism"}},
    {"from_verse": "isa.6.1", "to_verse": "ezek.1.1", "type": "typology", "subtype": "rowland_apocalyptic", "strength": 0.85, "metadata": {"scholar": "Christopher Rowland", "source": "The Open Heaven", "tag": "rowland_apocalyptic", "note": "Isaiah's temple vision and Ezekiel's chariot vision — two foundational throne visions for Jewish and Christian mysticism"}},
    {"from_verse": "dan.7.9", "to_verse": "rev.4.2", "type": "typology", "subtype": "deconick_mystic", "strength": 0.85, "metadata": {"scholar": "April DeConick", "source": "Seek to See Him", "tag": "deconick_mystic", "note": "The heavenly court scene — from Daniel to Revelation, the same liturgical framework"}},
    {"from_verse": "2cor.12.2", "to_verse": "ezek.1.1", "type": "typology", "subtype": "deconick_mystic", "strength": 0.8, "metadata": {"scholar": "April DeConick", "source": "Seek to See Him", "tag": "deconick_mystic", "note": "Paul's ascent to the third heaven — apocalyptic mysticism in the apostle's experience"}},

    # === 6. Fletcher-Louis (fletcherlouis_temple) ===
    {"from_verse": "isa.45.23", "to_verse": "phil.2.10", "type": "typology", "subtype": "fletcherlouis_temple", "strength": 0.85, "metadata": {"scholar": "Crispin Fletcher-Louis", "source": "Luke-Acts: Angels, Christology and Soteriology", "tag": "fletcherlouis_temple", "note": "Every knee shall bow and every tongue confess — YHWH's exclusive worship applied to Jesus"}},
    {"from_verse": "dan.7.13", "to_verse": "mark.14.62", "type": "typology", "subtype": "fletcherlouis_temple", "strength": 0.9, "metadata": {"scholar": "Crispin Fletcher-Louis", "source": "Luke-Acts: Angels, Christology and Soteriology", "tag": "fletcherlouis_temple", "note": "Jesus identifies himself with Daniel's Son of Man — the divine identity claim"}},
    {"from_verse": "psa.110.1", "to_verse": "1cor.15.25", "type": "typology", "subtype": "fletcherlouis_temple", "strength": 0.85, "metadata": {"scholar": "Crispin Fletcher-Louis", "source": "Luke-Acts: Angels, Christology and Soteriology", "tag": "fletcherlouis_temple", "note": "Sit at my right hand — the session of Christ at God's right hand, the divine throne"}},
    {"from_verse": "gen.1.1", "to_verse": "john.1.1", "type": "typology", "subtype": "fletcherlouis_temple", "strength": 0.9, "metadata": {"scholar": "Crispin Fletcher-Louis", "source": "Luke-Acts: Angels, Christology and Soteriology", "tag": "fletcherlouis_temple", "note": "In the beginning — the Logos hymn places Christ in the identity of YHWH, the creator"}},

    # === 7. Day / Smith (day_canaanite / smith_divine_family) ===
    {"from_verse": "psa.74.13", "to_verse": "isa.51.9", "type": "typology", "subtype": "day_canaanite", "strength": 0.85, "metadata": {"scholar": "John Day", "source": "Yahweh and the Gods and Goddesses of Canaan", "tag": "day_canaanite", "note": "YHWH's victory over Leviathan/Rahab — the Chaoskampf motif inherited from Canaanite Baal mythology"}},
    {"from_verse": "psa.74.13", "to_verse": "job.41.1", "type": "typology", "subtype": "day_canaanite", "strength": 0.85, "metadata": {"scholar": "John Day", "source": "Yahweh and the Gods and Goddesses of Canaan", "tag": "day_canaanite", "note": "Leviathan as YHWH's opponent — the chaos monster is defeated before creation"}},
    {"from_verse": "psa.89.9", "to_verse": "hab.3.8", "type": "typology", "subtype": "day_canaanite", "strength": 0.8, "metadata": {"scholar": "John Day", "source": "Yahweh and the Gods and Goddesses of Canaan", "tag": "day_canaanite", "note": "YHWH's battle with the sea — the Chaoskampf as a foundation for temple building"}},
    {"from_verse": "deu.32.8", "to_verse": "psa.82.1", "type": "typology", "subtype": "smith_divine_family", "strength": 0.85, "metadata": {"scholar": "Mark S. Smith", "source": "The Early History of God", "tag": "smith_divine_family", "note": "The divine council of El — from the Canaanite divine assembly to YHWH's council"}},
    {"from_verse": "exo.15.11", "to_verse": "psa.89.6", "type": "typology", "subtype": "smith_divine_family", "strength": 0.85, "metadata": {"scholar": "Mark S. Smith", "source": "The Early History of God", "tag": "smith_divine_family", "note": "Who among the gods is like thee, O LORD? — YHWH's supremacy over the divine council"}},

    # === 8. VanderKam / Boccaccini (vanderkam_dss / boccaccini_enoch) ===
    {"from_verse": "gen.5.24", "to_verse": "jub.4.17", "type": "typology", "subtype": "vanderkam_dss", "strength": 0.85, "metadata": {"scholar": "James C. VanderKam", "source": "The Dead Sea Scrolls Today", "tag": "vanderkam_dss", "note": "Enoch's translation as the beginning of Enochic Judaism — Jubilees expands the brief Genesis account"}},
    {"from_verse": "gen.5.24", "to_verse": "1enoch.14.8", "type": "typology", "subtype": "vanderkam_dss", "strength": 0.9, "metadata": {"scholar": "James C. VanderKam", "source": "The Dead Sea Scrolls Today", "tag": "vanderkam_dss", "note": "Enoch's heavenly journey — the first detailed account of human ascent to the divine throne"}},
    {"from_verse": "dan.7.13", "to_verse": "1enoch.46.1", "type": "typology", "subtype": "boccaccini_enoch", "strength": 0.85, "metadata": {"scholar": "Gabriele Boccaccini", "source": "Enoch and the Messiah Son of Man", "tag": "boccaccini_enoch", "note": "Daniel's Son of Man and Enoch's Chosen One — the Enochic Son of Man tradition"}},
    {"from_verse": "lev.26.3", "to_verse": "1enoch.1.1", "type": "typology", "subtype": "boccaccini_enoch", "strength": 0.8, "metadata": {"scholar": "Gabriele Boccaccini", "source": "Enoch and the Messiah Son of Man", "tag": "boccaccini_enoch", "note": "Covenant blessing and curse as the framework for Enochic Judaism — the Enochic worldview"}},
    {"from_verse": "gen.6.1", "to_verse": "1enoch.6.1", "type": "typology", "subtype": "boccaccini_enoch", "strength": 0.85, "metadata": {"scholar": "Gabriele Boccaccini", "source": "Enoch and the Messiah Son of Man", "tag": "boccaccini_enoch", "note": "The Watcher tradition — from Genesis 6 to the full Enochic angelology"}},

    # === 9. Himmelfarb / Stuckenbruck (himmelfarb_ascent / stuckenbruck_angel) ===
    {"from_verse": "isa.6.1", "to_verse": "rev.4.1", "type": "typology", "subtype": "himmelfarb_ascent", "strength": 0.85, "metadata": {"scholar": "Martha Himmelfarb", "source": "Ascent to Heaven in Jewish and Christian Apocalypses", "tag": "himmelfarb_ascent", "note": "The heavenly temple vision — from Isaiah to John, visions of God's throne in the temple"}},
    {"from_verse": "ezek.1.1", "to_verse": "1enoch.14.8", "type": "typology", "subtype": "himmelfarb_ascent", "strength": 0.85, "metadata": {"scholar": "Martha Himmelfarb", "source": "Ascent to Heaven in Jewish and Christian Apocalypses", "tag": "himmelfarb_ascent", "note": "Enoch's heavenly journey as a template for Jewish apocalyptic ascent"}},
    {"from_verse": "gen.6.1", "to_verse": "1enoch.12.1", "type": "typology", "subtype": "stuckenbruck_angel", "strength": 0.85, "metadata": {"scholar": "Loren T. Stuckenbruck", "source": "Angel Veneration and Christology", "tag": "stuckenbruck_angel", "note": "The Watchers' judgment — from Genesis 6 to the full Enochic Watcher tradition"}},

    # === 10. Bauckham (bauckham_christology) ===
    {"from_verse": "isa.45.23", "to_verse": "phil.2.10", "type": "typology", "subtype": "bauckham_christology", "strength": 0.9, "metadata": {"scholar": "Richard Bauckham", "source": "Jesus and the God of Israel", "tag": "bauckham_christology", "note": "Every knee shall bow and every tongue confess — YHWH's exclusive worship applied to Jesus"}},
    {"from_verse": "dan.7.13", "to_verse": "mark.14.62", "type": "typology", "subtype": "bauckham_christology", "strength": 0.9, "metadata": {"scholar": "Richard Bauckham", "source": "Jesus and the God of Israel", "tag": "bauckham_christology", "note": "Jesus identifies himself with Daniel's Son of Man — the divine identity claim"}},
    {"from_verse": "psa.110.1", "to_verse": "1cor.15.25", "type": "typology", "subtype": "bauckham_christology", "strength": 0.85, "metadata": {"scholar": "Richard Bauckham", "source": "Jesus and the God of Israel", "tag": "bauckham_christology", "note": "Sit at my right hand — the session of Christ at God's right hand, the divine throne"}},
    {"from_verse": "gen.1.1", "to_verse": "john.1.1", "type": "typology", "subtype": "bauckham_christology", "strength": 0.9, "metadata": {"scholar": "Richard Bauckham", "source": "Jesus and the God of Israel", "tag": "bauckham_christology", "note": "In the beginning — the Logos hymn places Christ in the identity of YHWH, the creator"}},

    # === 11. Mettinger / Weinfeld (mettinger_presence / weinfeld_deut) ===
    {"from_verse": "exo.40.34", "to_verse": "1kgs.8.11", "type": "typology", "subtype": "mettinger_presence", "strength": 0.9, "metadata": {"scholar": "Tryggve Mettinger", "source": "The Dethronement of Sabaoth", "tag": "mettinger_presence", "note": "The glory of YHWH filling the tabernacle and the temple — the Shekinah presence"}},
    {"from_verse": "1kgs.8.11", "to_verse": "ezek.10.4", "type": "typology", "subtype": "mettinger_presence", "strength": 0.9, "metadata": {"scholar": "Tryggve Mettinger", "source": "The Dethronement of Sabaoth", "tag": "mettinger_presence", "note": "The glory of YHWH departing the temple — Ezekiel's vision of the Kabod leaving"}},
    {"from_verse": "ezek.10.4", "to_verse": "ezek.43.4", "type": "typology", "subtype": "mettinger_presence", "strength": 0.9, "metadata": {"scholar": "Tryggve Mettinger", "source": "The Dethronement of Sabaoth", "tag": "mettinger_presence", "note": "The glory of YHWH returns to the eschatological temple — Ezekiel's vision of restoration"}},
    {"from_verse": "gen.2.2", "to_verse": "deu.12.9", "type": "typology", "subtype": "weinfeld_deut", "strength": 0.85, "metadata": {"scholar": "Moshe Weinfeld", "source": "Deuteronomy and the Deuteronomic School", "tag": "weinfeld_deut", "note": "God's rest from creation and Israel's rest in the land — the rest theology"}},
    {"from_verse": "deu.12.9", "to_verse": "psa.132.8", "type": "typology", "subtype": "weinfeld_deut", "strength": 0.85, "metadata": {"scholar": "Moshe Weinfeld", "source": "Deuteronomy and the Deuteronomic School", "tag": "weinfeld_deut", "note": "Arise, O LORD, into thy rest — the temple as the place of divine rest"}},
]


def main():
    db = get_db()

    # Clean up any previously inserted connections from this script
    tags = [
        'levenson_temple', 'nibley_temple', 'dempster_dominion', 'walton_cosmic',
        'rowland_apocalyptic', 'deconick_mystic', 'fletcherlouis_temple',
        'day_canaanite', 'smith_divine_family', 'vanderkam_dss',
        'himmelfarb_ascent', 'boccaccini_enoch', 'bauckham_christology',
        'stuckenbruck_angel', 'mettinger_presence', 'weinfeld_deut'
    ]
    for tag in tags:
        db.execute(
            "DELETE FROM connections WHERE metadata LIKE ?",
            (f'%"tag": "{tag}"%',)
        )
    db.commit()
    print("Cleaned up existing connections with our tags")

    inserted = 0
    skipped = 0
    for c in CONNECTIONS:
        try:
            db.execute(
                """INSERT OR IGNORE INTO connections
                   (source_verse, target_verse, type, subtype, strength, layer, discovered_by, metadata)
                   VALUES (?, ?, ?, ?, ?, 'sod', 'human', ?)""",
                (c["from_verse"], c["to_verse"], c["type"],
                 c.get("subtype", ""), c["strength"], json.dumps(c["metadata"])),
            )
            if db.total_changes > 0:
                inserted += 1
        except Exception as e:
            skipped += 1
            print(f"  SKIP ({c['from_verse']} -> {c['to_verse']}): {e}")
    db.commit()
    print(f"Inserted {inserted} new connections ({skipped} skipped)")

    # Verify
    tags = [
        'levenson_temple', 'nibley_temple', 'dempster_dominion', 'walton_cosmic',
        'rowland_apocalyptic', 'deconick_mystic', 'fletcherlouis_temple',
        'day_canaanite', 'smith_divine_family', 'vanderkam_dss',
        'himmelfarb_ascent', 'boccaccini_enoch', 'bauckham_christology',
        'stuckenbruck_angel', 'mettinger_presence', 'weinfeld_deut'
    ]
    print("\n=== Verification by tag ===")
    grand_total = 0
    for tag in tags:
        c = db.execute(
            "SELECT COUNT(*) FROM connections WHERE metadata LIKE ?",
            (f'%"tag": "{tag}"%',)
        ).fetchone()[0]
        print(f"  {tag}: {c}")
        grand_total += c
    print(f"  TOTAL: {grand_total}")

    total_all = db.execute(
        "SELECT COUNT(*) FROM connections WHERE metadata LIKE '%\"tag\":%'"
    ).fetchone()[0]
    print(f"  TOTAL connections with any tag: {total_all}")
    db.close()


if __name__ == "__main__":
    main()
