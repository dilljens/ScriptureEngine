#!/usr/bin/env python3
"""Seed entity alignment — Hebrew↔Greek↔English name equivalences.

Populates the entity_links table with known name mappings.
Links Strong's numbers across Hebrew and Greek for unified search.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db

# Known Strong's Hebrew ↔ Strong's Greek equivalences
# Format: (entity_id, type, english, hebrew, hebrew_strongs, greek, greek_strongs)
STRONGS_LINKS = [
    ("god", "deity", "God", "אלהים", "H0430", "θεός", "G2316"),
    ("yhwh", "divine_name", "LORD/YHWH", "יהוה", "H3068", "κύριος", "G2962"),
    ("jesus", "person", "Jesus", "יהושע", "H3091", "Ἰησοῦς", "G2424"),
    ("christ", "title", "Christ", "משיח", "H4899", "Χριστός", "G5547"),
    ("moses", "person", "Moses", "משה", "H4872", "Μωυσῆς", "G3475"),
    ("abraham", "person", "Abraham", "אברהם", "H0085", "Ἀβραάμ", "G0011"),
    ("isaac", "person", "Isaac", "יצחק", "H3327", "Ἰσαάκ", "G2464"),
    ("jacob", "person", "Jacob", "יעקב", "H3290", "Ἰακώβ", "G2384"),
    ("israel", "nation", "Israel", "ישראל", "H3478", "Ἰσραήλ", "G2474"),
    ("david", "person", "David", "דוד", "H1732", "Δαυίδ", "G1138"),
    ("adam", "person", "Adam", "אדם", "H0120", "Ἀδάμ", "G0076"),
    ("eve", "person", "Eve", "חוה", "H2332", "Εὔα", "G2096"),
    ("noah", "person", "Noah", "נח", "H5146", "Νῶε", "G3575"),
    ("abraham", "person", "Abraham", "אברהם", "H0085", "Ἀβραάμ", "G0011"),
    ("sarah", "person", "Sarah", "שרה", "H8283", "Σάρρα", "G4564"),
    ("isaiah", "person", "Isaiah", "ישעיהו", "H3470", "Ἠσαΐας", "G2268"),
    ("jeremiah", "person", "Jeremiah", "ירמיהו", "H3414", "Ἱερεμίας", "G2408"),
    ("ezekiel", "person", "Ezekiel", "יחזקאל", "H3168", "Ἰεζεκιήλ", "G2383"),
    ("daniel", "person", "Daniel", "דניאל", "H1840", "Δανιήλ", "G1158"),
    ("joshua", "person", "Joshua", "יהושע", "H3091", "Ἰησοῦς", "G2424"),
    ("samuel", "person", "Samuel", "שמואל", "H8050", "Σαμουήλ", "G4545"),
    ("jerusalem", "place", "Jerusalem", "ירושלים", "H3389", "Ἱερουσαλήμ", "G2419"),
    ("zion", "place", "Zion", "ציון", "H6726", "Σιών", "G4622"),
    ("egypt", "place", "Egypt", "מצרים", "H4714", "Αἴγυπτος", "G0125"),
    ("babylon", "place", "Babylon", "בבל", "H0894", "Βαβυλών", "G0897"),
    ("jordan", "place", "Jordan", "ירדן", "H3383", "Ἰορδάνης", "G2446"),
    ("sinai", "place", "Sinai", "סיני", "H5514", "Σινά", "G4614"),
    ("galilee", "place", "Galilee", "גליל", "H1551", "Γαλιλαία", "G1056"),
    ("heaven", "concept", "Heaven", "שמים", "H8064", "οὐρανός", "G3772"),
    ("earth", "concept", "Earth", "ארץ", "H0776", "γῆ", "G1093"),
    ("spirit", "concept", "Spirit", "רוח", "H7307", "πνεῦμα", "G4151"),
    ("angel", "being", "Angel", "מלאך", "H4397", "ἄγγελος", "G0032"),
    ("kingdom", "concept", "Kingdom", "מלכות", "H4438", "βασιλεία", "G0932"),
    ("covenant", "concept", "Covenant", "ברית", "H1285", "διαθήκη", "G1242"),
    ("torah", "concept", "Law/Torah", "תורה", "H8451", "νόμος", "G3551"),
    ("prophet", "title", "Prophet", "נביא", "H5030", "προφήτης", "G4396"),
    ("priest", "title", "Priest", "כהן", "H3548", "ἱερεύς", "G2409"),
    ("king", "title", "King", "מלך", "H4428", "βασιλεύς", "G0935"),
    ("servant", "title", "Servant", "עבד", "H5650", "δοῦλος", "G1401"),
    ("son_of_man", "title", "Son of Man", "בן אדם", "H0112", "υἱὸς ἀνθρώπου", "G5207"),
    ("messiah", "title", "Messiah", "משיח", "H4899", "Χριστός", "G5547"),
    ("holy_ghost", "divine_name", "Holy Spirit", "רוח הקודש", "H7307", "πνεῦμα ἅγιον", "G4151"),
    ("satan", "being", "Satan", "שטן", "H7854", "σατανᾶς", "G4567"),
    ("satan", "being", "Devil", "שטן", "H7854", "διάβολος", "G1228"),
    ("elijah", "person", "Elijah", "אליהו", "H0452", "Ἠλίας", "G2243"),
    ("elisha", "person", "Elisha", "אלישע", "H0477", "Ἐλισσαῖος", "G1666"),
    ("john_baptist", "person", "John the Baptist", "יוחנן", None, "Ἰωάννης βαπτιστής", "G0910"),
    ("peter", "person", "Peter", "כיפא", None, "Πέτρος", "G4074"),
    ("paul", "person", "Paul", "שאול", "H7586", "Παῦλος", "G3972"),
    ("matt", "person", "Matthew", "מתתיהו", "G4991", "Ματθαῖος", "G3156"),
    ("john_apostle", "person", "John", "יוחנן", None, "Ἰωάννης", "G2491"),
    ("luke", "person", "Luke", "", None, "Λουκᾶς", "G3065"),
    ("mary", "person", "Mary", "מרים", "H4813", "Μαρία", "G3137"),
    ("joseph", "person", "Joseph", "יוסף", "H3130", "Ἰωσήφ", "G2501"),
    ("pharaoh", "title", "Pharaoh", "פרעה", "H6547", "Φαραώ", "G5328"),
    ("caesar", "title", "Caesar", "קיסר", None, "Καῖσαρ", "G2541"),
    ("herod", "person", "Herod", "הורדוס", None, "Ἡρῴδης", "G2264"),
    ("pilate", "person", "Pilate", "פילטוס", None, "Πιλᾶτος", "G4091"),
    ("sabbath", "concept", "Sabbath", "שבת", "H7676", "σάββατον", "G4521"),
    ("passover", "concept", "Passover", "פסח", "H6453", "πάσχα", "G3957"),
    ("pentecost", "concept", "Pentecost", "שבועות", "H7620", "πεντηκοστή", "G4005"),
    ("temple", "concept", "Temple", "היכל", "H1964", "ναός", "G3485"),
    ("synagogue", "concept", "Synagogue", "כנסת", None, "συναγωγή", "G4864"),
    ("altar", "object", "Altar", "מזבח", "H4196", "θυσιαστήριον", "G2379"),
    ("sacrifice", "concept", "Sacrifice", "זבח", "H2077", "θυσία", "G2378"),
    ("mercy", "concept", "Mercy", "חסד", "H2617", "ἔλεος", "G1656"),
    ("truth", "concept", "Truth", "אמת", "H0571", "ἀλήθεια", "G0225"),
    ("peace", "concept", "Peace", "שלום", "H7965", "εἰρήνη", "G1515"),
    ("love", "concept", "Love", "אהבה", "H0160", "ἀγάπη", "G0026"),
    ("faith", "concept", "Faith", "אמונה", "H0530", "πίστις", "G4102"),
    ("hope", "concept", "Hope", "תקוה", "H8615", "ἐλπίς", "G1680"),
    ("grace", "concept", "Grace", "חן", "H2580", "χάρις", "G5485"),
    ("righteousness", "concept", "Righteousness", "צדק", "H6664", "δικαιοσύνη", "G1343"),
    ("sin", "concept", "Sin", "חטאת", "H2403", "ἁμαρτία", "G0266"),
    ("blessing", "concept", "Blessing", "ברכה", "H1293", "εὐλογία", "G2129"),
    ("judgment", "concept", "Judgment", "משפט", "H4941", "κρίσις", "G2920"),
    ("salvation", "concept", "Salvation", "ישועה", "H3444", "σωτηρία", "G4991"),
    ("redemption", "concept", "Redemption", "גאולה", "H1353", "ἀπολύτρωσις", "G0629"),
    ("glory", "concept", "Glory", "כבוד", "H3519", "δόξα", "G1391"),
    ("power", "concept", "Power", "כוח", "H3581", "δύναμις", "G1411"),
    ("wisdom", "concept", "Wisdom", "חכמה", "H2451", "σοφία", "G4678"),
    ("word", "concept", "Word", "דבר", "H1697", "λόγος", "G3056"),
    ("life", "concept", "Life", "חיים", "H2416", "ζωή", "G2222"),
    ("death", "concept", "Death", "מות", "H4194", "θάνατος", "G2288"),
    ("light", "concept", "Light", "אור", "H0216", "φῶς", "G5457"),
    ("darkness", "concept", "Darkness", "חשך", "H2822", "σκοτία", "G4653"),
    ("fire", "element", "Fire", "אש", "H0784", "πῦρ", "G4442"),
    ("water", "element", "Water", "מים", "H4325", "ὕδωρ", "G5204"),
    ("blood", "element", "Blood", "דם", "H1818", "αἷμα", "G0129"),
]


def main():
    conn = get_db()
    print("=" * 60)
    print("  Entity Alignment — Seed Data")
    print("=" * 60)

    count = 0
    for entry in STRONGS_LINKS:
        entity_id, entity_type, english, hebrew, heb_strongs, greek, grk_strongs = entry

        # Check if already exists
        existing = conn.execute("""
            SELECT id FROM entity_links WHERE entity_id = ?
        """, (entity_id,)).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO entity_links (entity_id, entity_type, english_name, hebrew_name, hebrew_strongs, greek_name, greek_strongs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (entity_id, entity_type, english, hebrew, heb_strongs, greek, grk_strongs))
            count += 1

    conn.commit()
    print(f"  {count} entity links seeded")

    # Show stats
    total = conn.execute("SELECT COUNT(*) as c FROM entity_links").fetchone()["c"]
    types = conn.execute("SELECT entity_type, COUNT(*) as c FROM entity_links GROUP BY entity_type").fetchall()
    print(f"  Total entities: {total}")
    for r in types:
        print(f"    {r['entity_type']}: {r['c']}")

    conn.close()


if __name__ == "__main__":
    main()
