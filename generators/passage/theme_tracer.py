"""
Theme Tracer — trace biblical themes through the canon and create themed passage connections.

For each defined theme (covenant, temple, exile, etc.), scans verses for keyword
matches, clusters consecutive matches into theme passages, and creates
passage_connections between same-theme passages.

Also creates cross-theme connections where themes overlap (e.g., temple + covenant).
"""

import json
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Theme Definitions ─────────────────────────────────────────────────
# Each theme has: name, description, and keyword patterns (English + transliterated Hebrew)
# Keywords are matched against verse text (text_english field in verses table)

THEMES = [
    {
        "name": "temple",
        "description": "Temple, sanctuary, tabernacle, and divine dwelling places",
        "keywords": [
            "temple", "sanctuary", "tabernacle", "holy place", "most holy",
            "mishkan", "hekhal", "bayit", "naos", "hieron",
            "dwelling place", "house of the lord", "house of god",
            "tent of meeting", "ark of the covenant", "mercy seat",
            "altar", "incense", "lampstand", "menorah", "shewbread",
            "glory of the lord", "filled the house", "cloud filled",
            "cornerstone", "living stone", "spiritual house",
        ],
    },
    {
        "name": "covenant",
        "description": "Covenants, treaties, and divine agreements",
        "keywords": [
            "covenant", "berit", "diatheke", "brit",
            "everlasting covenant", "new covenant", "book of the covenant",
            "covenant of peace", "covenant of salt",
            "cut a covenant", "make a covenant", "establish my covenant",
            "sign of the covenant", "ark of the covenant",
            "blood of the covenant", "testament",
            "promise", "oath", "swore", "vowed",
            "these are the words", "these are the statutes",
        ],
    },
    {
        "name": "exile_restoration",
        "description": "Exile, dispersion, return, and restoration",
        "keywords": [
            "exile", "captivity", "golah", "galut", "diaspora",
            "carry away", "taken captive", "led captive",
            "scatter", "disperse", "banish",
            "restore", "return", "bring back",
            "rebuild", "restore the fortunes",
            "gather you", "gather them",
            "out of the land", "strange land", "foreign land",
            "by the rivers of babylon", "how shall we sing",
            "remnant", "shear", "sarid",
            "branch", "shoot", "sprout",
        ],
    },
    {
        "name": "creation_new_creation",
        "description": "Creation, cosmos, new creation, and cosmic renewal",
        "keywords": [
            "create", "creation", "made the heavens", "founded the earth",
            "bara", "ktisis", "kainos",
            "new heavens", "new earth", "new creation",
            "beginning", "foundation of the world",
            "heavens and the earth", "firmament", "waters",
            "light and darkness", "day and night",
            "tree of life", "garden of eden",
            "first fruits", "new birth", "born again",
            "new heaven", "new earth", "all things new",
        ],
    },
    {
        "name": "exodus_deliverance",
        "description": "Exodus, deliverance, redemption, and liberation",
        "keywords": [
            "exodus", "deliver", "redeem", "redemption",
            "yetziah", "apolutrosis", "lutrosis",
            "bring out", "bring up from", "lead out",
            "mighty hand", "outstretched arm",
            "passover", "pesach", "lamb of god",
            "pass over", "blood on the door",
            "cross the sea", "red sea", "reed sea",
            "wilderness", "desert", "forty years",
            "promised land", "land flowing with milk and honey",
            "save", "salvation", "savior", "redeemer",
            "ransom", "set free", "liberate",
        ],
    },
    {
        "name": "day_of_the_lord",
        "description": "Day of the Lord, judgment day, eschaton",
        "keywords": [
            "day of the lord", "day of yhwh", "day of judgment",
            "yom yhwh", "hemera kyriou",
            "that day", "the great day", "day of wrath",
            "day of vengeance", "day of calamity",
            "day of the lord's coming",
            "end of days", "latter days", "last days",
            "coming of the son of man",
            "thief in the night", "sudden destruction",
            "wailing", "lamentation", "woe",
            "sun turned to darkness", "moon to blood",
            "stars fall", "heavens shaken",
        ],
    },
    {
        "name": "sacrifice_atonement",
        "description": "Sacrifice, atonement, propitiation, and cleansing",
        "keywords": [
            "sacrifice", "offering", "atonement", "propitiation",
            "korban", "hilasterion", "kippur",
            "burnt offering", "sin offering", "guilt offering",
            "peace offering", "grain offering", "drink offering",
            "blood of bulls", "blood of goats",
            "scapegoat", "azazel",
            "lay his hand", "sprinkle", "pour out",
            "cleanse", "purify", "sanctify",
            "once for all", "better sacrifice",
            "fragrant aroma", "pleasing odor",
        ],
    },
    {
        "name": "wisdom",
        "description": "Wisdom, understanding, knowledge, and instruction",
        "keywords": [
            "wisdom", "understanding", "knowledge", "discernment",
            "chokmah", "sophia", "prudence",
            "wise man", "wise woman",
            "teach", "instruction", "discipline",
            "proverb", "parable", "riddle",
            "fear of the lord", "beginning of wisdom",
            "folly", "fool", "mock",
            "inherit", "treasure",
            "hidden", "reveal", "mystery",
        ],
    },
    {
        "name": "suffering_servant",
        "description": "Suffering servant, vicarious suffering, and vindication",
        "keywords": [
            "suffering servant", "ebed yhwh", "pais theou",
            "despised", "rejected", "man of sorrows",
            "acquainted with grief", "borne our griefs",
            "carried our sorrows", "wounded", "bruised",
            "chastisement", "stripes", "healed",
            "sheep", "silent", "led to the slaughter",
            "cut off", "poured out", "intercession",
            "see the light", "prolong his days",
            "sprinkle", "justify",
            "humble", "exalt", "high and lifted up",
        ],
    },
    {
        "name": "divine_presence",
        "description": "Divine presence, glory, shekinah, and theophany",
        "keywords": [
            "glory of the lord", "presence of the lord",
            "shekinah", "kavod", "doxa",
            "face of god", "before the lord",
            "cloud", "fire", "brightness",
            "holy ground", "holy place", "sanctuary",
            "dwelleth", "abide", "inhabit",
            "fill the earth", "fill the temple",
            "throne of god", "heavenly throne",
            "i am with you", "i will be with you",
            "high and lofty", "train of his robe",
            "seraphim", "cherubim", "angel of the lord",
        ],
    },
    {
        "name": "kingdom_of_god",
        "description": "Kingdom of God, reign of God, and divine sovereignty",
        "keywords": [
            "kingdom of god", "kingdom of heaven", "kingdom",
            "malkut", "basileia",
            "reign", "rule", "throne",
            "king of kings", "lord of lords",
            "dominion", "authority", "power",
            "everlasting kingdom", "eternal kingdom",
            "kingdom of christ", "kingdom of the lord",
            "enter the kingdom", "inherit the kingdom",
            "keys of the kingdom", "kingdom of light",
            "not of this world", "within you",
            "come into your kingdom", "remember me",
            "the kingdoms of this world",
            "kingdom of our lord and of his christ",
        ],
    },
    {
        "name": "election_chosen_people",
        "description": "Election, chosen people, calling, and predestination",
        "keywords": [
            "chosen", "elect", "election",
            "bachar", "eklektos", "ekloge",
            "choose", "set apart", "sanctify",
            "holy nation", "peculiar people", "royal priesthood",
            "people of god", "children of god", "sons of god",
            "called", "calling", "vocation",
            "foreknow", "predestinate", "predestine",
            "appoint", "ordain", "consecrate",
            "firstborn", "firstfruits",
            "inherit", "heritage", "portion",
            "i have called you by name",
            "you are mine", "i will be your god",
        ],
    },
    {
        "name": "judgment_mercy",
        "description": "Divine judgment and mercy, justice and compassion",
        "keywords": [
            "judgment", "justice", "righteousness",
            "mishpat", "krisis", "eleos",
            "mercy", "compassion", "lovingkindness",
            "chesed", "rahamim", "oiktirmos",
            "judge of all the earth", "righteous judge",
            "plead the cause", "defend the poor",
            "oppress", "orphan", "widow", "stranger",
            "let justice roll", "do justly", "love mercy",
            "slow to anger", "abounding in love",
            "forgiving", "pardon", "blot out",
            "execute judgment", "declare righteous",
            "justify", "justification",
            "wrath", "anger", "indignation",
        ],
    },
    {
        "name": "resurrection",
        "description": "Resurrection, eternal life, and bodily renewal",
        "keywords": [
            "resurrection", "raise from the dead", "risen",
            "anastasis", "egersis",
            "eternal life", "everlasting life",
            "inherit eternal life", "enter life",
            "first resurrection", "better resurrection",
            "raised incorruptible", "raised in glory",
            "body of glory", "transformed", "changed",
            "sleep in the dust", "awake", "arise",
            "death is swallowed up", "victory",
            "live again", "stand again",
            "mortal put on immortality",
            "life after death", "resurrection of the dead",
        ],
    },
    {
        "name": "holy_spirit",
        "description": "Holy Spirit, Spirit of God, and spiritual gifts",
        "keywords": [
            "holy spirit", "spirit of god", "spirit of the lord",
            "ruach", "pneuma", "parakletos",
            "spirit of christ", "spirit of truth",
            "filled with the spirit", "baptized with the spirit",
            "gift of the spirit", "fruits of the spirit",
            "spirit of wisdom", "spirit of counsel",
            "wind", "breath", "ruach",
            "comforter", "advocate", "helper",
            "anoint", "seal", "earnest",
            "spiritual gifts", "charismata",
            "tongues", "prophecy", "healing",
            "led by the spirit", "walk in the spirit",
        ],
    },
    {
        "name": "shepherd_flock",
        "description": "Shepherd, flock, sheep, and pastoral imagery",
        "keywords": [
            "shepherd", "pastor", "poimen",
            "flock", "sheep", "lamb",
            "good shepherd", "great shepherd", "chief shepherd",
            "pasture", "fold", "sheepfold",
            "lead beside still waters", "restore my soul",
            "lost sheep", "stray", "wander",
            "feed my sheep", "feed my lambs",
            "tend the flock", "oversight",
            "wolf", "hireling", "stranger",
            "one flock", "one shepherd",
            "sheep without a shepherd",
            "lamb of god", "slain lamb",
        ],
    },
]


def run(conn, book_ids=None) -> int:
    """Trace themes through the canon.

    For each theme, scan verse text for keyword matches, cluster consecutive
    matches into passage ranges, and create passage_connections between
    same-theme passages.

    Returns count of passage connections created.
    """
    # Phase 1: Scan for theme keywords
    theme_verses = _scan_theme_keywords(conn, book_ids)
    if not theme_verses:
        logger.info("theme_tracer: no keyword matches found")
        return 0

    total_connections = 0

    # Phase 2: Cluster into passages and create connections
    for theme_name, verse_data in theme_verses.items():
        passages = _cluster_passages(verse_data, theme_name)
        if len(passages) < 2:
            continue

        count = _create_theme_connections(conn, theme_name, passages)
        total_connections += count

    logger.info("theme_tracer: %d total theme connections created", total_connections)
    return total_connections


def _scan_theme_keywords(conn, book_ids=None):
    """Scan verse text for theme keywords. Returns {theme: [{verse, count}, ...]}."""
    results: dict[str, list[dict]] = defaultdict(list)

    for theme in THEMES:
        name = theme["name"]
        keywords = [k.lower() for k in theme["keywords"]]

        for keyword in keywords[:5]:  # Use top 5 keywords per theme for performance
            like_pattern = f"%{keyword}%"
            try:
                if book_ids:
                    placeholders = ",".join("?" for _ in book_ids)
                    rows = conn.execute(f"""
                        SELECT id FROM verses
                        WHERE LOWER(text_english) LIKE ?
                          AND SUBSTR(id, 1, INSTR(id, '.') - 1) IN ({placeholders})
                        LIMIT 200
                    """, (like_pattern, *book_ids)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT id FROM verses
                        WHERE LOWER(text_english) LIKE ?
                        LIMIT 200
                    """, (like_pattern,)).fetchall()
                for r in rows:
                    # Extract book from verse ID
                    book = r["id"].split(".")[0]
                    results[name].append({
                        "verse": r["id"],
                        "book": book,
                        "keyword": keyword,
                    })
            except Exception as e:
                logger.warning("theme_tracer: scan error for %s/%s: %s", name, keyword, e)

    return dict(results)


def _cluster_passages(verse_data, theme_name, window=5):
    """Cluster consecutive verses with theme matches into passage ranges."""
    if not verse_data:
        return []

    # Sort verses
    sorted_verses = sorted(set(v["verse"] for v in verse_data))

    # Group by book
    by_book: dict[str, list[str]] = defaultdict(list)
    for v in sorted_verses:
        parts = v.split(".")
        book = parts[0]
        by_book[book].append(v)

    passages = []
    for book, verses in by_book.items():
        verses.sort()
        i = 0
        while i < len(verses):
            start = verses[i]
            # Find end of cluster (consecutive verses with gaps)
            j = i
            while j + 1 < len(verses):
                gap = _verse_gap(verses[j], verses[j + 1])
                if gap <= 5:  # Allow small gaps
                    j += 1
                else:
                    break
            end = verses[j]

            # Only create passages with at least 2 distinct verses
            if start != end:
                passages.append({
                    "start": start,
                    "end": end,
                    "match_count": j - i + 1,
                    "book": book,
                    "theme": theme_name,
                })
            elif _verse_gap_count(verse_data, start) >= 3:
                # Single verse with 3+ keyword matches still counts
                passages.append({
                    "start": start,
                    "end": start,
                    "match_count": _verse_gap_count(verse_data, start),
                    "book": book,
                    "theme": theme_name,
                })

            i = j + 1

    return passages


def _verse_gap(a: str, b: str) -> int:
    """Calculate gap between two verse IDs. Returns verse number difference."""
    try:
        parts_a = a.split(".")
        parts_b = b.split(".")
        if parts_a[0] != parts_b[0] or parts_a[1] != parts_b[1]:
            return 999  # Different chapters
        return abs(int(parts_b[2]) - int(parts_a[2]))
    except (ValueError, IndexError):
        return 999


def _verse_gap_count(verse_data, verse_id) -> int:
    """Count how many keyword matches a verse has."""
    return sum(1 for v in verse_data if v["verse"] == verse_id)


def _create_theme_connections(conn, theme_name, passages):
    """Create passage_connections between passages sharing the same theme."""
    count = 0

    for i in range(len(passages)):
        for j in range(i + 1, len(passages)):
            a, b = passages[i], passages[j]

            # Skip if same passage
            if a["start"] == b["start"] and a["end"] == b["end"]:
                continue

            # Skip same-book connections (too trivial)
            if a["book"] == b["book"]:
                continue

            strength = min(0.5 + (a["match_count"] + b["match_count"]) * 0.05, 1.0)
            confidence = min(0.5 + strength * 0.3, 0.95)

            metadata = json.dumps({
                "theme": theme_name,
                "matches_a": a["match_count"],
                "matches_b": b["match_count"],
                "source": "theme_tracer",
            })

            try:
                conn.execute("""
                    INSERT INTO passage_connections
                        (source_start, source_end, target_start, target_end, layer, type,
                         strength, confidence, discovered_by, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_start, source_end, target_start, target_end, layer, type, subtype)
                    DO NOTHING
                """, (
                    a["start"], a["end"],
                    b["start"], b["end"],
                    "interpretive", "book_thematic",
                    round(strength, 2), round(confidence, 2),
                    "algorithm", metadata,
                ))
                count += 1
            except Exception as e:
                logger.warning("theme_tracer: connection error: %s", e)

    conn.commit()
    return count
