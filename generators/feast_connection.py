"""Feast connection generator — feast_connection connections.

Connects verses that mention the same biblical feast or holy day.
Uses a gazetteer of feast names in both English and Hebrew.

Two types of connections:
  1. Same feast mentions across the canon (e.g., Passover in Exodus and Matthew)
  2. OT institution → NT fulfillment pairings (e.g., Lev 23 Passover → Matt 26 Last Supper)
"""

from collections import defaultdict

from lib.db import add_connection

# Feast gazetteer: feast_name -> [search terms in English and Hebrew]
FEAST_GAZETTEER = {
    "passover": {
        "terms": [
            "passover", "pass over", "paschal", "pesach", "pesah",
            "חַג הַפֶּסַח", "פֶּסַח", "פסח",
        ],
        "description": "Passover — remembrance of deliverance from Egypt",
    },
    "unleavened_bread": {
        "terms": [
            "unleavened bread", "matzah", "matzo", "mazzoth",
            "חַג הַמַּצּוֹת", "מַצָּה",
        ],
        "description": "Feast of Unleavened Bread — seven days following Passover",
    },
    "firstfruits": {
        "terms": [
            "firstfruits", "first fruits", "first-fruits", "bikkurim",
            "בִּכּוּרִים",
        ],
        "description": "Feast of Firstfruits — offering of the first barley harvest",
    },
    "pentecost": {
        "terms": [
            "pentecost", "shavuot", "shavuoth", "feast of weeks", "feast of harvest",
            "day of firstfruits", "שָׁבֻעוֹת", "שבועות",
        ],
        "description": "Feast of Weeks / Pentecost — 50 days after Firstfruits",
    },
    "trumpets": {
        "terms": [
            "trumpets", "feast of trumpets", "yom teruah", "rosh hashanah",
            "יוֹם תְּרוּעָה", "תְּרוּעָה",
            "זִכְרוֹן תְּרוּעָה",
        ],
        "description": "Feast of Trumpets — memorial of blowing of trumpets",
    },
    "atonement": {
        "terms": [
            "day of atonement", "yom kippur", "kippur",
            "יוֹם כִּפֻּר", "יוֹם הַכִּפֻּרִים", "כִּפֻּרִים",
        ],
        "description": "Day of Atonement / Yom Kippur — holiest day of the year",
    },
    "tabernacles": {
        "terms": [
            "tabernacles", "feast of booths", "feast of ingathering",
            "sukkot", "succoth", "succot",
            "חַג הַסֻּכּוֹת", "סֻכָּה", "סוכות",
        ],
        "description": "Feast of Tabernacles / Booths — 7-day harvest festival",
    },
    "dedication": {
        "terms": [
            "feast of dedication", "hanukkah", "chanukah", "hanukka",
            "חֲנֻכָּה", "חנוכה", "חַג הַחֲנֻכָּה",
        ],
        "description": "Feast of Dedication / Hanukkah — rededication of the Temple",
    },
    "purim": {
        "terms": [
            "purim", "lots",
            "פּוּרִים",
        ],
        "description": "Purim — deliverance from Haman's plot",
    },
    "new_moon": {
        "terms": [
            "new moon", "new moons", "monthly", "rosh chodesh",
            "רֹאשׁ חֹדֶשׁ", "חֹדֶשׁ",
        ],
        "description": "New Moon — monthly observance",
    },
    "sabbath": {
        "terms": [
            "sabbath", "sabbath day", "shabbat",
            "שַׁבָּת", "שַׁבָּת",
        ],
        "description": "Sabbath — weekly day of rest",
    },
    "sabbatical_year": {
        "terms": [
            "sabbatical year", "year of release", "shmita", "shmittah",
            "שְׁמִטָּה",
        ],
        "description": "Sabbatical Year / Shmita — every 7th year",
    },
    "jubilee": {
        "terms": [
            "jubilee", "year of jubilee", "jubile", "yovel", "jubilees",
            "יוֹבֵל",
        ],
        "description": "Year of Jubilee — every 50th year, liberty proclaimed",
    },
    "passover_haggadah": {
        "terms": [
            "haggadah", "seder", "last supper", "lord's supper",
        ],
        "description": "Passover Seder / Last Supper — the ritual meal",
    },
}


def run(conn, book_ids=None):
    """Generate feast connections.

    For each feast in the gazetteer, find all verses mentioning it,
    then connect verses that share the same feast.

    Returns count of connections created.
    """
    count = 0

    # Get all verses with text
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

    print(f"  Scanning {len(rows)} verses for feast names...")

    # Build a feast->verses index
    feast_verses = defaultdict(set)
    for r in rows:
        text = (r["text_english"] or "") + " " + (r["text_hebrew"] or "")
        text_lower = text.lower()
        for feast_name, feast_info in FEAST_GAZETTEER.items():
            for term in feast_info["terms"]:
                if term.lower() in text_lower:
                    feast_verses[feast_name].add(r["id"])
                    break  # One match per feast per verse

    # Connect verses that share the same feast
    for feast_name, verses in feast_verses.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)
        feast_info = FEAST_GAZETTEER[feast_name]

        # Hub-and-spoke for very common feasts (sabbath)
        if len(verse_list) > 30:
            hub = verse_list[0]
            for v in verse_list[1:]:
                try:
                    add_connection(conn, hub, v,
                                  layer="chronological",
                                  type_name="feast_connection",
                                  subtype=feast_name,
                                  strength=0.55,
                                  confidence=0.6,
                                  discovered_by="algorithm",
                                  metadata={
                                      "feast": feast_name,
                                      "description": feast_info["description"],
                                      "total_mentions": len(verses),
                                  })
                    count += 1
                except Exception:
                    pass
        else:
            # Full mesh for less common feasts
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    try:
                        add_connection(conn, verse_list[i], verse_list[j],
                                      layer="chronological",
                                      type_name="feast_connection",
                                      subtype=feast_name,
                                      strength=0.6,
                                      confidence=0.65,
                                      discovered_by="algorithm",
                                      metadata={
                                          "feast": feast_name,
                                          "description": feast_info["description"],
                                          "total_mentions": len(verses),
                                      })
                        count += 1
                    except Exception:
                        pass

    conn.commit()
    print(f"  Feast Connections: {count} connections across {len(feast_verses)} feasts")
    return count
