"""Geographic subtypes generator — connects verses through geographic themes.

Beyond simple same_location (any place mention), this generator creates
typed geographic connections for specific geographic concepts:
  - journey_path: Part of the same journey route
  - wilderness_sojourn: Wilderness experience connections
  - exile_route: Exile/deportation connections
  - promised_land: Land/covenant land connections
  - mountain_of_god: Sinai/Zion/temple mount connections
  - temple_location: Temple/House of the Lord connections
  - garden_presence: Eden/temple/presence connections

Each uses keyword and entity-based pre-filtering.
"""

import re
from collections import defaultdict
from lib.db import add_connection


# Keyword gazetteers for each geographic subtype
GEO_SUBTYPES = {
    "journey_path": {
        "keywords": [
            "journey", "travel", "way", "road", "path", "wilderness",
            "went forth", "departed", "journeyed", "marched",
            "בדרך", "מסע", "דרך",
        ],
        "description": "Journey route connections",
        "strength": 0.6,
        "confidence": 0.55,
    },
    "wilderness_sojourn": {
        "keywords": [
            "wilderness", "desert", "waste", "howling", "solitary",
            "forty years", "forty days", "wandering",
            "מִדְבָּר", "עֲרָבָה", "יְשִׁימוֹן",
        ],
        "description": "Wilderness experience connections",
        "strength": 0.65,
        "confidence": 0.6,
    },
    "exile_route": {
        "keywords": [
            "captivity", "exile", "carried away", "deported",
            "babylon", "assyria", "dispersed", "scattered",
            "גָּלוּת", "שְׁבִי", "גָּלָה",
        ],
        "description": "Exile and deportation connections",
        "strength": 0.65,
        "confidence": 0.6,
    },
    "promised_land": {
        "keywords": [
            "promised land", "land of promise", "canaan",
            "land flowing", "inheritance", "possession",
            "holy land", "land of israel",
            "אֶרֶץ יִשְׂרָאֵל", "אֶרֶץ הַבְּרִית",
        ],
        "description": "Covenant land connections",
        "strength": 0.6,
        "confidence": 0.6,
    },
    "mountain_of_god": {
        "keywords": [
            "mount sinai", "mount horeb", "mount zion",
            "mount moriah", "mount of olives", "mount of the lord",
            "mountain of god", "holy mountain", "mount",
            "הַר סִינַי", "הַר יְהוָה", "צִיּוֹן",
        ],
        "description": "Sacred mountain connections",
        "strength": 0.65,
        "confidence": 0.6,
    },
    "temple_location": {
        "keywords": [
            "temple", "house of the lord", "sanctuary",
            "tabernacle", "holy place", "holy house",
            "בֵּית יְהוָה", "מִקְדָּשׁ", "הֵיכָל",
        ],
        "description": "Temple/house of the Lord connections",
        "strength": 0.65,
        "confidence": 0.65,
    },
    "garden_presence": {
        "keywords": [
            "garden of eden", "garden of the lord",
            "paradise", "presence of the lord",
            "tree of life", "river of water of life",
            "גַּן עֵדֶן", "פַּרְדֵּס",
        ],
        "description": "Eden/divine presence connections",
        "strength": 0.7,
        "confidence": 0.65,
    },
}


def run(conn, book_ids=None):
    """Generate geographic subtype connections.

    For each geographic subtype, find verses matching the keyword patterns,
    then connect verses sharing the same subtype.

    Returns count of connections created.
    """
    count = 0

    # Get all verses
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT id, text_english, text_hebrew FROM verses
            WHERE (text_english != '' OR text_hebrew != '')
            AND book_id IN ({placeholders})
        """, book_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, text_english, text_hebrew FROM verses
            WHERE text_english != '' OR text_hebrew != ''
        """).fetchall()

    print(f"  Scanning {len(rows)} verses for geographic subtypes...", flush=True)

    # Build subtype→verses index
    subtype_verses = defaultdict(set)
    for r in rows:
        text = (r["text_english"] or "") + " " + (r["text_hebrew"] or "")
        text_lower = text.lower()
        for subtype_name, subtype_info in GEO_SUBTYPES.items():
            for kw in subtype_info["keywords"]:
                if kw.lower() in text_lower:
                    subtype_verses[subtype_name].add(r["id"])
                    break

    # Connect verses sharing the same subtype
    for subtype_name, verses in subtype_verses.items():
        if len(verses) < 2:
            continue

        info = GEO_SUBTYPES[subtype_name]
        verse_list = sorted(verses)

        # Hub-and-spoke for larger groups
        if len(verse_list) <= 15:
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    try:
                        add_connection(conn, verse_list[i], verse_list[j],
                                      layer="geographic",
                                      type_name=subtype_name,
                                      subtype=subtype_name,
                                      strength=info["strength"],
                                      confidence=info["confidence"],
                                      discovered_by="algorithm",
                                      metadata={
                                          "subtype": subtype_name,
                                          "description": info["description"],
                                          "total_mentions": len(verses),
                                      })
                        count += 1
                    except Exception:
                        pass
        else:
            hub = verse_list[0]
            for v in verse_list[1:]:
                try:
                    add_connection(conn, hub, v,
                                  layer="geographic",
                                  type_name=subtype_name,
                                  subtype=subtype_name,
                                  strength=info["strength"],
                                  confidence=info["confidence"],
                                  discovered_by="algorithm",
                                  metadata={
                                      "subtype": subtype_name,
                                      "description": info["description"],
                                      "total_mentions": len(verses),
                                  })
                    count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  Geographic Subtypes: {count} connections across {len(subtype_verses)} subtypes")
    return count
