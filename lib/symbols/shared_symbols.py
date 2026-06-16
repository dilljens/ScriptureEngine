"""Shared symbol matcher — finds all occurrences of known symbols across the canon.

For each symbol in the reference table, this generator:
1. Finds all verses mentioning that symbol (by matching the symbol's known words)
2. Connects them as symbolic connections
3. The AI classifies symbolic vs. literal use
"""

import re
from collections import defaultdict
from ..db import add_connection


# Mapping from symbol names to English and Hebrew search terms
SYMBOL_SEARCH_TERMS = {
    "lamb": ["lamb", "lambs", "שֶׂה", "ἀρνίον", "ἀμνός"],
    "lion": ["lion", "lions", "אריה", "λέων"],
    "serpent": ["serpent", "serpents", "נחש", "ὄφις"],
    "dragon": ["dragon", "δράκων"],
    "eagle": ["eagle", "eagles", "נשר", "ἀετός"],
    "dove": ["dove", "doves", "יונה", "περιστερά"],
    "wolf": ["wolf", "wolves", "זאב", "λύκος"],
    "vine": ["vine", "vines", "גפן", "ἄμπελος"],
    "fig_tree": ["fig", "figs", "תאנה", "συκῆ"],
    "olive_tree": ["olive", "olives", "זית", "ἐλαία"],
    "bread": ["bread", "לחם", "ἄρτος"],
    "wine": ["wine", "יין", "οἶνος"],
    "fire": ["fire", "אש", "πῦρ"],
    "water": ["water", "מים", "ὕδωρ"],
    "throne": ["throne", "thrones", "כסא", "θρόνος"],
    "crown": ["crown", "crowns", "עטרה", "στέφανος"],
    "sword": ["sword", "swords", "חרב", "μάχαιρα"],
    "rock": ["rock", "rocks", "צור", "πέτρα"],
    "gold": ["gold", "זהב", "χρυσός"],
    "silver": ["silver", "כסף", "ἄργυρος"],
    "wilderness": ["wilderness", "מדבר", "ἔρημος"],
    "mountain": ["mountain", "mountains", "הר", "ὄρος"],
    "cloud": ["cloud", "clouds", "ענן", "νεφέλη"],
    "light": ["light", "אור", "φῶς"],
    "darkness": ["darkness", "חשך", "σκοτία"],
    "heart": ["heart", "hearts", "לב", "καρδία"],
    "altar": ["altar", "altars", "מזבח", "θυσιαστήριον"],
    "incense": ["incense", "קטרת", "θυμίαμα"],
    "key": ["key", "keys", "מפתח", "κλείς"],
}

# Symbols known to use Strong's numbers for precise matching
SYMBOL_STRONGS = {
    "lamb": ["H7716", "G286", "G721"],      # seh, amnos, arnion
    "lion": ["H738", "H3833", "G3023"],      # ari, labi, leon
    "serpent": ["H5175", "H8314", "G3789"],    # nachash, saraph, ophis
    "dragon": ["H8577", "G1404"],             # tannin, drakon
    "eagle": ["H5404", "H7360", "G105"],      # nesher, racham, aetos
    "dove": ["H3123", "G4058"],               # yonah, peristera
    "throne": ["H3678", "H3764", "G2362"],     # kisse, kors, thronos
    "crown": ["H5850", "H3803", "G4735"],     # atarah, kether, stephanos
    "altar": ["H4196", "G2379"],              # mizbeach, thusiasterion
    "incense": ["H7004", "G2368"],            # ketoreth, thumiama
    "fire": ["H784", "G4442"],                # esh, pur
    "water": ["H4325", "H4325", "G5204"],     # mayim, hydor
    "blood": ["H1818", "G129"],               # dam, haima
    "sword": ["H2719", "H7974", "G3162"],     # chereb, machaira
    "rock": ["H6697", "H5553", "G4073"],      # tsur, cela, petra
    "gold": ["H2091", "H1722", "G5557"],      # zahab, gold, chrysos
    "wilderness": ["H4057", "H3452", "G2048"], # midbar, yeshimon, eremos
    "mountain": ["H2022", "H2042", "G3735"],   # har, mount, oros
    "light": ["H216", "H215", "G5457"],       # or, phos
    "darkness": ["H2822", "H2816", "G4653"],   # choshek, skotia
}


def generate_shared_symbol_connections(conn, book_ids=None):
    """Generate connections between verses sharing the same symbol.

    Uses keyword matching on English text + Strong's numbers from gematria table.
    AI should review results and classify symbolic vs. literal.
    """
    count = 0

    for sym_name, terms in SYMBOL_SEARCH_TERMS.items():
        # Find all verses mentioning this symbol's keywords
        found_verses = set()
        for term in terms[:3]:  # Use first 3 search terms
            if any('\u0590' <= c <= '\u05FF' for c in term):
                # Hebrew term — search via gematria word_hebrew
                # Build a consonant-only LIKE pattern
                cons = ""
                for c in term:
                    cp = ord(c)
                    if (0x05D0 <= cp <= 0x05EA) or (0x05EF <= cp <= 0x05F2):
                        cons += c
                if cons:
                    pattern = f"%{'%'.join(cons)}%"
                    rows = conn.execute("""
                        SELECT DISTINCT g.verse_id FROM gematria g
                        WHERE g.word_hebrew LIKE ?
                    """, (pattern,)).fetchall()
                    for r in rows:
                        found_verses.add(r["verse_id"])
            else:
                # English term — search via text
                rows = conn.execute("""
                    SELECT id FROM verses WHERE text_english LIKE ?
                """, (f"%{term}%",)).fetchall()
                for r in rows:
                    found_verses.add(r["id"])

        # Also search by Strong's number if available
        if sym_name in SYMBOL_STRONGS:
            for strongs in SYMBOL_STRONGS[sym_name]:
                rows = conn.execute("""
                    SELECT DISTINCT g.verse_id FROM gematria g
                    WHERE g.lemma LIKE ?
                """, (f"%{strongs}%",)).fetchall()
                for r in rows:
                    found_verses.add(r["verse_id"])

        found_list = list(found_verses)

        # Limit: only connect the first 15 occurrences (keeps connections manageable)
        if len(found_list) > 15:
            found_list = found_list[:15]

        # Connect each occurrence to the FIRST occurrence (hub-and-spoke pattern)
        # This avoids N² explosion while still linking all occurrences together
        if len(found_list) >= 2:
            hub = found_list[0]
            for verse in found_list[1:]:
                try:
                    add_connection(conn, hub, verse,
                                  layer="symbolic",
                                  type_name="shared_symbol",
                                  subtype=sym_name,
                                  strength=0.5,
                                  confidence=0.4,
                                  discovered_by="algorithm",
                                  metadata={"symbol": sym_name,
                                           "note": f"Both mention '{sym_name}'. AI review needed to classify symbolic vs literal."})
                    count += 1
                except Exception:
                    pass

    print(f"  Shared symbols: {count} connections")
    conn.commit()
    return count


def get_symbolic_connections_for_verse(conn, verse_id):
    """Get all symbolic connections for a specific verse.

    Returns a list of symbols found in this verse, with their connections.
    """
    symbols = conn.execute("""
        SELECT s.name, s.category, s.meaning
        FROM symbols s
        JOIN symbol_occurrences so ON so.symbol_id = s.id
        WHERE so.verse_id = ?
    """, (verse_id,)).fetchall()

    result = []
    for s in symbols:
        # Find connected verses sharing this symbol
        connected = conn.execute("""
            SELECT c.target_verse
            FROM connections c
            WHERE c.source_verse = ? AND c.subtype = ? AND c.layer = 'symbolic'
            LIMIT 10
        """, (verse_id, s["name"])).fetchall()
        result.append({
            "symbol": s["name"],
            "category": s["category"],
            "meaning": s["meaning"],
            "connected_verses": [r["target_verse"] for r in connected],
        })

    return result
