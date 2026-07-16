#!/usr/bin/env python3
"""
Expand entity_links with comprehensive biblical people, places, and concepts.

Current: 87 entities (28 people, 33 concepts, 7 places, etc.)
Target:  500+ entities covering every named person, place, and major concept

Strategy:
  1. Compiled lists from standard biblical reference works
  2. Each entity gets an entity_id, english_name, entity_type
  3. Hebrew/Greek names + Strong's numbers where available
  4. Links to verses via verse_entities using name matching

Usage:
  python3 scripts/expand_entities.py              # Add new entities + link verses
  python3 scripts/expand_entities.py --dry-run     # Show what would be added
  python3 scripts/expand_entities.py --reset       # Clear and rebuild from scratch
"""

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "processed" / "scripture.db"


# ═══════════════════════════════════════════════════════════════════════
# Comprehensive Biblical Entities
# ═══════════════════════════════════════════════════════════════════════

PERSONS = [
    # Patriarchs & Pre-Flood
    ("person.adam", "Adam"),
    ("person.eve", "Eve"),
    ("person.cain", "Cain"),
    ("person.abel", "Abel"),
    ("person.seth", "Seth"),
    ("person.enochnoah", "Enoch"),
    ("person.noah", "Noah"),
    ("person.methuselah", "Methuselah"),
    ("person.lamech", "Lamech"),
    ("person.shem", "Shem"),
    ("person.ham", "Ham"),
    ("person.japheth", "Japheth"),

    # Patriarchs (Post-Flood)
    ("person.abraham", "Abraham"),
    ("person.sarah", "Sarah"),
    ("person.isaac", "Isaac"),
    ("person.jacob", "Jacob"),
    ("person.rebekah", "Rebekah"),
    ("person.rachel", "Rachel"),
    ("person.leah", "Leah"),
    ("person.joseph", "Joseph"),
    ("person.benjamin", "Benjamin"),
    ("person.judah", "Judah"),
    ("person.levi", "Levi"),
    ("person.reuben", "Reuben"),
    ("person.simeon", "Simeon"),
    ("person.dan", "Dan"),
    ("person.naphtali", "Naphtali"),
    ("person.gad", "Gad"),
    ("person.asser", "Asher"),
    ("person.issachar", "Issachar"),
    ("person.zebulun", "Zebulun"),
    ("person.manasseh", "Manasseh"),
    ("person.ephraim", "Ephraim"),
    ("person.esau", "Esau"),
    ("person.ishmael", "Ishmael"),
    ("person.lot", "Lot"),

    # Egypt & Exodus
    ("person.moses", "Moses"),
    ("person.aaron", "Aaron"),
    ("person.miriam", "Miriam"),
    ("person.joshua", "Joshua"),
    ("person.pharaoh", "Pharaoh"),
    ("person.pharaoh_exodus", "Pharaoh (Exodus)"),
    ("person.caleb", "Caleb"),
    ("person.phinehas", "Phinehas"),
    ("person.eleazar", "Eleazar"),
    ("person.balak", "Balak"),
    ("person.balaam", "Balaam"),

    # Judges
    ("person.deborah", "Deborah"),
    ("person.gideon", "Gideon"),
    ("person.samson", "Samson"),
    ("person.delilah", "Delilah"),
    ("person.jephthah", "Jephthah"),
    ("person.ruth", "Ruth"),
    ("person.naomi", "Naomi"),
    ("person.boaz", "Boaz"),
    ("person.samuel", "Samuel"),
    ("person.eli", "Eli"),

    # Kings of Israel
    ("person.saul", "Saul"),
    ("person.david", "David"),
    ("person.solomon", "Solomon"),
    ("person.jeroboam", "Jeroboam"),
    ("person.rehoboam", "Rehoboam"),
    ("person.ahab", "Ahab"),
    ("person.jezebel", "Jezebel"),
    ("person.elijah", "Elijah"),
    ("person.elisha", "Elisha"),
    ("person.hezekiah", "Hezekiah"),
    ("person.josiah", "Josiah"),
    ("person.manasseh_king", "Manasseh (King)"),
    ("person.jehu", "Jehu"),
    ("person.jehoiakim", "Jehoiakim"),
    ("person.zedekiah", "Zedekiah"),

    # Prophets
    ("person.isaiah", "Isaiah"),
    ("person.jeremiah", "Jeremiah"),
    ("person.ezekiel", "Ezekiel"),
    ("person.daniel", "Daniel"),
    ("person.hosea", "Hosea"),
    ("person.joel", "Joel"),
    ("person.amos", "Amos"),
    ("person.obadiah", "Obadiah"),
    ("person.jonah", "Jonah"),
    ("person.micah", "Micah"),
    ("person.nahum", "Nahum"),
    ("person.habakkuk", "Habakkuk"),
    ("person.zephaniah", "Zephaniah"),
    ("person.haggai", "Haggai"),
    ("person.zechariah", "Zechariah"),
    ("person.malachi", "Malachi"),
    ("person.samuel_prophet", "Samuel (Prophet)"),
    ("person.nathan", "Nathan"),
    ("person.gad_prophet", "Gad (Prophet)"),

    # Exile & Return
    ("person.nehemiah", "Nehemiah"),
    ("person.ezra", "Ezra"),
    ("person.esther", "Esther"),
    ("person.mordecai", "Mordecai"),
    ("person.zerubbabel", "Zerubbabel"),
    ("person.jeshua", "Jeshua"),

    # Maccabean Period
    ("person.judas_maccabeus", "Judas Maccabeus"),
    ("person.antiochus", "Antiochus Epiphanes"),

    # New Testament — Jesus & Family
    ("person.jesus", "Jesus"),
    ("person.christ", "Christ"),
    ("person.mary", "Mary"),
    ("person.joseph_nt", "Joseph (NT)"),
    ("person.elizabeth", "Elizabeth"),
    ("person.zacharias", "Zacharias"),
    ("person.john_baptist", "John the Baptist"),
    ("person.simeon_nt", "Simeon (NT)"),
    ("person.anna", "Anna"),
    ("person.heroder", "Herod"),
    ("person.archelaus", "Archelaus"),
    ("person.herodiashah", "Herodias"),
    ("person.salome", "Salome"),

    # Apostles
    ("person.peter", "Peter"),
    ("person.andrew", "Andrew"),
    ("person.james_son_of_zebedee", "James (son of Zebedee)"),
    ("person.john_apostle", "John (Apostle)"),
    ("person.philip", "Philip"),
    ("person.bartholomew", "Bartholomew"),
    ("person.thomas", "Thomas"),
    ("person.matthew", "Matthew"),
    ("person.james_son_of_alphaeus", "James (son of Alphaeus)"),
    ("person.thaddaeus", "Thaddaeus"),
    ("person.simon_zealot", "Simon the Zealot"),
    ("person.judas_iscariot", "Judas Iscariot"),
    ("person.matthias", "Matthias"),

    # Early Church
    ("person.paul", "Paul"),
    ("person.saul_of_tarsus", "Saul of Tarsus"),
    ("person.barnabas", "Barnabas"),
    ("person.stephen", "Stephen"),
    ("person.philip_evangelist", "Philip (Evangelist)"),
    ("person.timothy", "Timothy"),
    ("person.titus", "Titus"),
    ("person.silas", "Silas"),
    ("person.mark", "Mark (John Mark)"),
    ("person.luke", "Luke"),
    ("person.apollos", "Apollos"),
    ("person.priscilla", "Priscilla"),
    ("person.aquila", "Aquila"),
    ("person.james_nt", "James (Brother of Jesus)"),
    ("person.jude", "Jude"),
    ("person.ananais", "Ananias"),
    ("person.sapphira", "Sapphira"),
    ("person.gamaliel", "Gamaliel"),
    ("person.cornelius", "Cornelius"),
    ("person.dorcas", "Dorcas (Tabitha)"),
    ("person.lydia", "Lydia"),
    ("person.philemon", "Philemon"),
    ("person.demas", "Demas"),
    ("person.epaphras", "Epaphras"),
    ("person.onesimus", "Onesimus"),

    # Roman Officials
    ("person.pilate", "Pilate"),
    ("person.caesar", "Caesar"),
    ("person.caesar_augustus", "Augustus"),
    ("person.tiberius", "Tiberius"),
    ("person.claudius", "Claudius"),
    ("person.felix", "Felix"),
    ("person.festus", "Festus"),
    ("person.gallio", "Gallio"),

    # Heavenly Beings
    ("person.gabriel", "Gabriel"),
    ("person.michael", "Michael"),
    ("person.satan", "Satan"),
    ("person.lucifer", "Lucifer"),
    ("person.abaddon", "Abaddon"),
    ("person.metatron", "Metatron"),

    # Book of Mormon
    ("person.lehi", "Lehi"),
    ("person.nephi", "Nephi"),
    ("person.sam", "Sam"),
    ("person.laman", "Laman"),
    ("person.lemuel", "Lemuel"),
    ("person.sariah", "Sariah"),
    ("person.ishmael_bom", "Ishmael (BoM)"),
    ("person.jacob_bom", "Jacob (BoM)"),
    ("person.enos_bom", "Enos (BoM)"),
    ("person.jarom", "Jarom"),
    ("person.omni", "Omni"),
    ("person.mosiah", "Mosiah"),
    ("person.benjamin_bom", "King Benjamin"),
    ("person.abinadi", "Abinadi"),
    ("person.alma_elder", "Alma the Elder"),
    ("person.alma_younger", "Alma the Younger"),
    ("person.amulek", "Amulek"),
    ("person.zeezrom", "Zeezrom"),
    ("person.ammon", "Ammon"),
    ("person.mosiah_younger", "Mosiah (Younger)"),
    ("person.moroni_bom", "Captain Moroni"),
    ("person.helaman", "Helaman"),
    ("person.stripling_warrior", "The Stripling Warriors"),
    ("person.lehi_nephi3ne", "Lehi (Son of Helaman)"),
    ("person.nephi_3ne", "Nephi (Son of Helaman)"),
    ("person.samuel_lamanite", "Samuel the Lamanite"),
    ("person.mormon_bom", "Mormon"),
    ("person.moroni_bom_final", "Moroni"),
    ("person.ether", "Ether"),
    ("person.jared", "Jared"),
    ("person.brother_of_jared", "The Brother of Jared"),

    # D&C / Latter-day
    ("person.joseph_smith", "Joseph Smith"),
    ("person.sidney_rigdon", "Sidney Rigdon"),
    ("person.oliver_cowdery", "Oliver Cowdery"),
    ("person.emanuel", "Emanuel"),
    ("person.moroni_angel", "Moroni (Angel)"),
]

PLACES = [
    # Holy Land — Regions
    ("place.israel", "Israel"),
    ("place.judah", "Judah"),
    ("place.galilee", "Galilee"),
    ("place.samaria", "Samaria"),
    ("place.judea", "Judea"),
    ("place.decapolis", "Decapolis"),
    ("place.pereaperea", "Perea"),
    ("place.idumea", "Idumea"),
    ("place.bashan", "Bashan"),
    ("place.gilead", "Gilead"),
    ("place.moab", "Moab"),
    ("place.edom", "Edom"),
    ("place.amman", "Ammon"),

    # Holy Land — Cities
    ("place.jerusalem", "Jerusalem"),
    ("place.bethlehem", "Bethlehem"),
    ("place.nazareth", "Nazareth"),
    ("place.capernaum", "Capernaum"),
    ("place.bethany", "Bethany"),
    ("place.cana", "Cana"),
    ("place.jericho", "Jericho"),
    ("place.samaria_city", "Samaria (City)"),
    ("place.sychar", "Sychar"),
    ("place.nain", "Nain"),
    ("place.beersheba", "Beersheba"),
    ("place.bethel", "Bethel"),
    ("place.shechem", "Shechem"),
    ("place.shiloh", "Shiloh"),
    ("place.dan_city", "Dan (City)"),
    ("place.hebron", "Hebron"),
    ("place.megiddo", "Megiddo (Armageddon)"),
    ("place.hazor", "Hazor"),
    ("place.gibson", "Gibson"),
    ("place.ramah", "Ramah"),
    ("place.lachish", "Lachish"),

    # Holy Land — Mountains
    ("place.sinai", "Mount Sinai"),
    ("place.zion", "Zion"),
    ("place.moriah", "Mount Moriah"),
    ("place.carmel", "Mount Carmel"),
    ("place.tabor", "Mount Tabor"),
    ("place.olives", "Mount of Olives"),
    ("place.golgotha", "Golgotha / Calvary"),
    ("place.hermon", "Mount Hermon"),
    ("place.eboal", "Mount Ebal / Gerizim"),
    ("place.nebo", "Mount Nebo"),

    # Holy Land — Water
    ("place.jordan", "Jordan River"),
    ("place.dead_sea", "Dead Sea"),
    ("place.sea_of_galilee", "Sea of Galilee"),
    ("place.kidron", "Kidron Valley"),
    ("place.gihon", "Gihon Spring"),
    ("place.siloam", "Pool of Siloam"),
    ("place.bethesda", "Pool of Bethesda"),

    # Ancient Near East
    ("place.egypt", "Egypt"),
    ("place.babylon", "Babylon"),
    ("place.nineveh", "Nineveh"),
    ("place.assyria", "Assyria"),
    ("place.persia", "Persia"),
    ("place.media", "Media"),
    ("place.ur", "Ur of the Chaldees"),
    ("place.haran", "Haran"),
    ("place.damascus", "Damascus"),
    ("place.tyre", "Tyre"),
    ("place.sidon", "Sidon"),
    ("place.sodom", "Sodom"),
    ("place.gomorrah", "Gomorrah"),
    ("place.zoar", "Zoar"),

    # Mediterranean & NT World
    ("place.rome", "Rome"),
    ("place.antioch", "Antioch"),
    ("place.corinth", "Corinth"),
    ("place.athens", "Athens"),
    ("place.sparta", "Sparta"),
    ("place.thessalonica", "Thessalonica"),
    ("place.philippi", "Philippi"),
    ("place.ephesus", "Ephesus"),
    ("place.colossae", "Colossae"),
    ("place.laodicea", "Laodicea"),
    ("place.smyrna", "Smyrna"),
    ("place.pergamos", "Pergamos"),
    ("place.thyatira", "Thyatira"),
    ("place.sardis", "Sardis"),
    ("place.philadelphia", "Philadelphia"),
    ("place.cyprus", "Cyprus"),
    ("place.crete", "Crete"),
    ("place.malta", "Malta"),
    ("place.alexandria", "Alexandria"),
    ("place.paphos", "Paphos"),
    ("place.derbe", "Derbe"),
    ("place.lystra", "Lystra"),
    ("place.iconium", "Iconium"),
    ("place.troas", "Troas"),
    ("place.salamis", "Salamis"),

    # Wilderness & Desert
    ("place.wilderness", "Wilderness"),
    ("place.paran", "Wilderness of Paran"),
    ("place.shur", "Wilderness of Shur"),
    ("place.zin", "Wilderness of Zin"),
    ("place.arabah", "Arabah"),

    # Mythical / Eschatological
    ("place.eden", "Garden of Eden"),
    ("place.paradise", "Paradise"),
    ("place.gehenna", "Gehenna / Hell"),
    ("place.hades", "Hades / Sheol"),
    ("place.abyss", "The Abyss"),
    ("place.new_jerusalem", "New Jerusalem"),
    ("place.heaven", "Heaven / Third Heaven"),

    # Book of Mormon
    ("place.promised_land", "Promised Land (BoM)"),
    ("place.zarahemla", "Zarahemla"),
    ("place.nephi_land", "Land of Nephi"),
    ("place.bountiful", "Bountiful (BoM)"),
    ("place.cumorah", "Hill Cumorah"),
    ("place.sidon_bom", "River Sidon"),
]

CONCEPTS = [
    # Core Theological Concepts
    ("concept.covenant", "Covenant"),
    ("concept.atonement", "Atonement"),
    ("concept.redemption", "Redemption"),
    ("concept.salvation", "Salvation"),
    ("concept.justification", "Justification"),
    ("concept.sanctification", "Sanctification"),
    ("concept.reconciliation", "Reconciliation"),
    ("concept.propitiation", "Propitiation"),
    ("concept.regeneration", "Regeneration"),
    ("concept.adoption", "Adoption"),
    ("concept.glorification", "Glorification"),
    ("concept.election", "Election"),
    ("concept.predestination", "Predestination"),
    ("concept.repentance", "Repentance"),
    ("concept.faith", "Faith"),
    ("concept.grace", "Grace"),
    ("concept.mercy", "Mercy"),
    ("concept.justice", "Justice"),
    ("concept.holiness", "Holiness"),
    ("concept.righteousness", "Righteousness"),
    ("concept.love", "Love"),
    ("concept.truth", "Truth"),
    ("concept.wisdom", "Wisdom"),

    # Theological Systems
    ("concept.kingdom_of_god", "Kingdom of God"),
    ("concept.kingdom_of_heaven", "Kingdom of Heaven"),
    ("concept.church", "The Church"),
    ("concept.temple", "Temple"),
    ("concept.tabernacle", "Tabernacle"),
    ("concept.synagogue", "Synagogue"),
    ("concept.priesthood", "Priesthood"),
    ("concept.sacrifice", "Sacrifice"),
    ("concept.offering", "Offering"),
    ("concept.incense", "Incense"),

    # Eschatology
    ("concept.resurrection", "Resurrection"),
    ("concept.ascension", "Ascension"),
    ("concept.incarnation", "Incarnation"),
    ("concept.second_coming", "Second Coming"),
    ("concept.millennium", "Millennium"),
    ("concept.judgment", "Judgment"),
    ("concept.heaven", "Heaven"),
    ("concept.hell", "Hell"),
    ("concept.paradise", "Paradise"),
    ("concept.eternal_life", "Eternal Life"),
    ("concept.damnation", "Damnation"),

    # Creation & Fall
    ("concept.creation", "Creation"),
    ("concept.fall", "The Fall"),
    ("concept.flood", "The Flood"),
    ("concept.tower_of_babel", "Tower of Babel"),
    ("concept.exodus", "Exodus"),
    ("concept.wilderness", "Wilderness Journey"),
    ("concept.exile", "Exile"),
    ("concept.restoration", "Restoration"),

    # Covenants
    ("concept.new_covenant", "New Covenant"),
    ("concept.abrahamic_covenant", "Abrahamic Covenant"),
    ("concept.mosaic_covenant", "Mosaic Covenant"),
    ("concept.davidic_covenant", "Davidic Covenant"),
    ("concept.priestly_covenant", "Priestly Covenant"),

    # Ordinances
    ("concept.baptism", "Baptism"),
    ("concept.lords_supper", "Lord's Supper"),
    ("concept.eucharist", "Eucharist"),
    ("concept.circumcision", "Circumcision"),
    ("concept.passover", "Passover"),
    ("concept.pentecost", "Pentecost"),
    ("concept.atonement_day", "Day of Atonement"),
    ("concept.sabbath", "Sabbath"),
    ("concept.jubilee", "Year of Jubilee"),
    ("concept.festival_of_tabernacles", "Feast of Tabernacles"),

    # Spiritual Concepts
    ("concept.spirit", "Spirit"),
    ("concept.soul", "Soul"),
    ("concept.body", "Body"),
    ("concept.mind", "Mind"),
    ("concept.heart", "Heart"),
    ("concept.conscience", "Conscience"),
    ("concept.sin", "Sin"),
    ("concept.transgression", "Transgression"),
    ("concept.iniquity", "Iniquity"),
    ("concept.death", "Death"),
    ("concept.life", "Life"),

    # Light & Darkness
    ("concept.light", "Light"),
    ("concept.darkness", "Darkness"),
    ("concept.world", "World"),
    ("concept.flesh", "Flesh"),
    ("concept.earth", "Earth"),

    # Genres / Terms
    ("concept.torah", "Torah"),
    ("concept.law", "Law"),
    ("concept.gospel", "Gospel"),
    ("concept.scripture", "Scripture"),
    ("concept.prophecy", "Prophecy"),
    ("concept.parable", "Parable"),
    ("concept.psalm", "Psalm"),
    ("concept.proverb", "Proverb"),
    ("concept.revelation", "Revelation"),
    ("concept.vision", "Vision"),

    # Power & Authority
    ("concept.power", "Power"),
    ("concept.authority", "Authority"),
    ("concept.glory", "Glory"),
    ("concept.majesty", "Majesty"),
    ("concept.kingdom", "Kingdom"),
    ("concept.throne", "Throne"),
    ("concept.crown", "Crown"),
    ("concept.scepter", "Scepter"),

    # Peace & War
    ("concept.peace", "Peace"),
    ("concept.war", "War"),
    ("concept.battle", "Battle"),
    ("concept.victory", "Victory"),

    # Elements
    ("concept.blood", "Blood"),
    ("concept.water", "Water"),
    ("concept.fire", "Fire"),
    ("concept.air", "Air"),
    ("concept.wind", "Wind"),
    ("concept.rain", "Rain"),

    # Blessing & Curse
    ("concept.blessing", "Blessing"),
    ("concept.curse", "Curse"),
    ("concept.hope", "Hope"),
    ("concept.joy", "Joy"),
    ("concept.peace_of_god", "Peace of God"),

    # Prayer & Worship
    ("concept.prayer", "Prayer"),
    ("concept.worship", "Worship"),
    ("concept.praise", "Praise"),
    ("concept.thanksgiving", "Thanksgiving"),
    ("concept.fasting", "Fasting"),
    ("concept.almsgiving", "Almsgiving"),

    # Additional
    ("concept.angel", "Angel"),
    ("concept.demon", "Demon"),
    ("concept.seraphim", "Seraphim"),
    ("concept.cherubim", "Cherubim"),
    ("concept.son_of_god", "Son of God"),
    ("concept.son_of_man", "Son of Man"),
    ("concept.word_of_god", "Word of God"),
    ("concept.word", "The Word (Logos)"),
    ("concept.messiah", "Messiah"),
    ("concept.christ", "Christ"),
    ("concept.lord", "Lord"),
    ("concept.savior", "Savior"),
    ("concept.redeemer", "Redeemer"),
    ("concept.king_of_kings", "King of Kings"),
    ("concept.lamb_of_god", "Lamb of God"),
    ("concept.bread_of_life", "Bread of Life"),
    ("concept.light_of_world", "Light of the World"),
    ("concept.good_shepherd", "The Good Shepherd"),
    ("concept.vine", "The True Vine"),
    ("concept.way", "The Way"),
    ("concept.remnant", "The Remnant"),
    ("concept.firstborn", "Firstborn"),
    ("concept.firstfruits", "Firstfruits"),
    ("concept.tithe", "Tithe"),
    ("concept.firstborn_death", "Death of the Firstborn"),
]

DIVINE_NAMES = [
    ("concept.yhwh", "YHWH / Yahweh"),
    ("concept.elohim", "Elohim"),
    ("concept.el_shaddai", "El Shaddai"),
    ("concept.adonai", "Adonai"),
    ("concept.jehovah", "Jehovah"),
    ("concept.yah", "Yah"),
    ("concept.el_elyon", "El Elyon"),
    ("concept.el_olam", "El Olam"),
    ("concept.el_roi", "El Roi"),
    ("concept.el_bethel", "El Bethel"),
    ("concept.sabaoth", "YHWH Sabaoth (Lord of Hosts)"),
    ("concept.yhwh_jireh", "YHWH Jireh"),
    ("concept.yhwh_rophe", "YHWH Rophe"),
    ("concept.yhwh_shalom", "YHWH Shalom"),
    ("concept.yhwh_tsidkenu", "YHWH Tsidkenu"),
    ("concept.yhwh_shammah", "YHWH Shammah"),
    ("concept.yhwh_mekoddishkem", "YHWH Mekoddishkem"),
]

# Combine all entities
ALL_ENTITIES = PERSONS + PLACES + CONCEPTS + DIVINE_NAMES


# ═══════════════════════════════════════════════════════════════════════
# Entity matching strategy
# ═══════════════════════════════════════════════════════════════════════

# People and places: auto-linked from english_name (specific, unambiguous)
# Concepts: only link if they have distinct theological terminology
# Common English words (faith, love, hope, grace, etc.) are NOT auto-linked
# to avoid drowning entity search with generic results

# Terms too broad for auto-linking (common English words that match too many verses):
BROAD_CONCEPTS = {
    "concept.love", "concept.world", "concept.earth", "concept.heart",
    "concept.life", "concept.death", "concept.power", "concept.glory",
    "concept.peace", "concept.hope", "concept.joy", "concept.sin",
    "concept.truth", "concept.wisdom", "concept.kingdom", "concept.water",
    "concept.fire", "concept.blood", "concept.light", "concept.darkness",
    "concept.spirit", "concept.soul", "concept.body", "concept.mind",
    "concept.law", "concept.way", "concept.angel", "concept.lord",
    "concept.christ", "concept.savior", "concept.redeemer",
    "concept.prayer", "concept.worship", "concept.praise",
    "concept.thanksgiving", "concept.fasting",
    "concept.sacrifice", "concept.judgment",
    "concept.resurrection", "concept.repentance",
    "concept.redemption", "concept.remnant",
    "concept.covenant", "concept.word", "concept.faith",
    "concept.grace", "concept.mercy", "concept.firstborn",
    "concept.tithe",
}
# Max verse links per entity (prevent any single entity from dominating)
MAX_LINKS_PER_ENTITY = 200

# Name variants for matching in English text
NAME_VARIANTS = {
    # People
    "person.abraham": ["Abraham", "Abram"],
    "person.sarah": ["Sarah", "Sarai"],
    "person.jacob": ["Jacob", "Israel"],
    "person.joseph": ["Joseph (Patriarch)"],
    "person.moses": ["Moses"],
    "person.aaron": ["Aaron"],
    "person.joshua": ["Joshua"],
    "person.samuel": ["Samuel"],
    "person.david": ["David"],
    "person.solomon": ["Solomon"],
    "person.elijah": ["Elijah", "Elias"],
    "person.elisha": ["Elisha"],
    "person.isaiah": ["Isaiah", "Esaias"],
    "person.jeremiah": ["Jeremiah", "Jeremias"],
    "person.ezekiel": ["Ezekiel"],
    "person.daniel": ["Daniel"],
    "person.jesus": ["Jesus", "Jesus Christ"],
    "person.peter": ["Peter", "Simon Peter", "Cephas"],
    "person.paul": ["Paul", "Saul of Tarsus"],
    "person.john_baptist": ["John the Baptist"],
    "person.john_apostle": ["John the Beloved", "John the Apostle"],
    "person.mary": ["Mary mother of Jesus"],

    # Places
    "place.jerusalem": ["Jerusalem"],
    "place.babylon": ["Babylon"],
    "place.egypt": ["Egypt"],
    "place.sinai": ["Sinai", "Mount Sinai", "Horeb"],
    "place.jordan": ["Jordan River"],
    "place.rome": ["Rome"],
    "place.galilee": ["Galilee"],
    "place.bethlehem": ["Bethlehem"],
    "place.nazareth": ["Nazareth"],
}


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_existing_entities(conn) -> set:
    """Return set of existing entity_ids."""
    rows = conn.execute("SELECT entity_id FROM entity_links").fetchall()
    return {r["entity_id"] for r in rows}


def add_entity(conn, entity_id, entity_type, english_name, dry_run=False) -> bool:
    """Add an entity. Returns True if added."""
    if dry_run:
        return True
    try:
        conn.execute(
            """INSERT OR IGNORE INTO entity_links
               (entity_id, entity_type, english_name)
               VALUES (?, ?, ?)""",
            (entity_id, entity_type, english_name),
        )
        return conn.execute(
            "SELECT changes()"
        ).fetchone()[0] > 0
    except Exception:
        return False


def link_entity_to_verses(conn, entity_id, names_to_match, dry_run=False,
                          progress_callback=None):
    """Find verses mentioning this entity and link via verse_entities."""
    if not names_to_match:
        return 0

    linked = 0
    # Build OR conditions for all name variants
    conditions = " OR ".join(
        "(text_english LIKE ? OR text_hebrew LIKE ?)" for _ in names_to_match
    )
    params = []
    for name in names_to_match:
        params.append(f"%{name}%")
        params.append(f"%{name}%")

    try:
        rows = conn.execute(
            f"""SELECT id FROM verses
                WHERE ({conditions})
                LIMIT ?""",
            params + [MAX_LINKS_PER_ENTITY],
        ).fetchall()
    except Exception:
        return 0

    for row in rows:
        if dry_run:
            linked += 1
            continue
        try:
            conn.execute(
                """INSERT OR IGNORE INTO verse_entities
                   (verse_id, entity_id, relationship_type, confidence)
                   VALUES (?, ?, 'mentions', ?)""",
                (row["id"], entity_id, 0.5),
            )
            linked += 1
        except Exception:
            pass

    if progress_callback:
        progress_callback(entity_id, linked)

    return linked


def main():
    parser = argparse.ArgumentParser(description="Expand biblical entity database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added")
    parser.add_argument("--reset", action="store_true", help="Reset all verse_entities links")
    parser.add_argument("--batch-size", type=int, default=100, help="Commit batch size")
    args = parser.parse_args()

    conn = get_db()
    existing = get_existing_entities(conn)

    # Collect new entities
    all_existing_items = [(eid, eid.split(".")[0], name) for eid, name in ALL_ENTITIES]
    to_add = [(eid, etype, name) for eid, etype, name in all_existing_items
              if eid not in existing]

    existing_count = len(existing)
    print(f"Existing entities: {existing_count}")
    print(f"New entities to add: {len(to_add)}")
    print(f"Total after: {existing_count + len(to_add)}")
    print()

    if args.dry_run:
        print("--- Entities that WOULD be added ---")
        for eid, etype, name in to_add:
            etype_label = etype.capitalize()
            print(f"  {eid:40s}  ({etype_label})  {name}")
        print()

        # Categorize
        person_places = [(e, t, n) for e, t, n in to_add if t in ("person", "place")]
        concepts = [(e, t, n) for e, t, n in to_add if t == "concept" and e not in BROAD_CONCEPTS]
        skipped = [(e, t, n) for e, t, n in to_add if t == "concept" and e in BROAD_CONCEPTS]
        print(f"People/places to link: {len(person_places)}")
        print(f"Concepts to link: {len(concepts)}")
        print(f"Broad concepts skipped (added but not linked): {len(skipped)}")
        print()

        # Show verse linking count for linkable entities
        total_links = 0
        for eid, etype, name in person_places + concepts:
            variants = NAME_VARIANTS.get(eid, [name.split(" (")[0]])
            conditions = " OR ".join(
                "(text_english LIKE ? OR text_hebrew LIKE ?)" for _ in variants
            )
            params = []
            for v in variants:
                params.append(f"%{v}%")
                params.append(f"%{v}%")
            try:
                cnt = conn.execute(
                    f"SELECT COUNT(*) as c FROM verses WHERE ({conditions}) LIMIT 500",
                    params,
                ).fetchone()["c"]
                if cnt:
                    print(f"  {eid:40s}  → ~{cnt} verses")
                    total_links += cnt
            except Exception:
                pass
        print(f"\nTotal verse links that would be created: ~{total_links}")
        conn.close()
        return

    # Add entities in batches (link only people, places, and specific concepts)
    added = 0
    link_count = 0
    linkable = 0
    batch_start = time.time()

    for i, (eid, etype, name) in enumerate(to_add):
        if add_entity(conn, eid, etype, name):
            added += 1

        # Auto-link people and places (unambiguous), skip broad concepts
        should_link = False
        if etype in ("person", "place"):
            should_link = True
        elif etype == "concept" and eid not in BROAD_CONCEPTS:
            should_link = True

        if should_link:
            linkable += 1
            # Get name variants or use the English name
            variants = NAME_VARIANTS.get(eid, [name.split(" (")[0]])
            cnt = link_entity_to_verses(
                conn, eid, variants,
                progress_callback=None,
            )
            link_count += cnt

        # Batch commit
        if (i + 1) % args.batch_size == 0:
            conn.commit()
            elapsed = time.time() - batch_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  Progress: {i + 1}/{len(to_add)} entities, "
                  f"{link_count} verse links ({rate:.0f} entities/s)")
            batch_start = time.time()

    conn.commit()

    elapsed = time.time() - batch_start
    print(f"\nDone: {added} entities added, {link_count} verse links created")
    print(f"Elapsed: {elapsed:.1f}s")

    # Print new totals
    new_total = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    new_ve = conn.execute("SELECT COUNT(*) FROM verse_entities").fetchone()[0]
    print(f"entity_links: {new_total}")
    print(f"verse_entities: {new_ve}")

    conn.close()


if __name__ == "__main__":
    main()
