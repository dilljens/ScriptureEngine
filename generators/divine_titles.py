"""Divine Titles generator — connects verses that share the same title/epithet for God.

Finds significant divine titles and epithets across the canon and creates
connections between verses that use the same title. These are meaningful
theological links that word-level generators miss.

Hebrew titles searched in text_hebrew (OT + DSS), English fallback for NT, BoM, D&C.
"""

from collections import defaultdict, Counter
from lib.db import add_connection

# Divine titles: (english_name, hebrew_key, [english_keywords])
# hebrew_key = substring to search in text_hebrew
# english_keywords = list of words to match in text_english (for NT/BoM/D&C)
TITLES = [
    # ── Compound Divine Names ──
    ("YHWH Elohim / Lord God", "יהוה אלהים", ["Lord God", "LORD God"]),
    ("YHWH of Hosts / Lord of Hosts", "יהוה צבאות", ["Lord of hosts", "LORD of hosts"]),
    ("YHWH Sabaoth / God of Hosts", "יהוה צבאות", ["Lord God of hosts", "God of hosts"]),
    ("El Elyon / God Most High", "אל עליון", ["Most High God", "God Most High"]),
    ("El Shaddai / God Almighty", "אל שדי", ["God Almighty", "Almighty God"]),
    ("El Olam / Everlasting God", "אל עולם", ["Everlasting God", "the everlasting God"]),
    ("El Roi / God Who Sees", "אל ראי", ["God who sees", "God of seeing"]),
    ("El Berit / God of the Covenant", "אל ברית", ["God of the covenant"]),

    # ── Epithets ──
    ("Holy One of Israel", "קדוש ישראל", ["Holy One of Israel"]),
    ("Holy One of Jacob", "קדוש יעקב", ["Holy One of Jacob"]),
    ("Mighty One of Israel", "אביר ישראל", ["Mighty One of Israel"]),
    ("Mighty One of Jacob", "אביר יעקב", ["Mighty One of Jacob"]),
    ("Rock of Israel", "צור ישראל", ["Rock of Israel"]),
    ("Shepherd of Israel", "רעה ישראל", ["Shepherd of Israel"]),
    ("King of Israel", "מלך ישראל", ["King of Israel"]),
    ("King of Glory", "מלך הכבוד", ["King of glory", "King of Glory"]),
    ("King of Kings", "מלך המלכים", ["King of kings", "King of Kings", "Lord of lords"]),
    ("Lord of Lords", "אדון האדנים", ["Lord of lords"]),
    ("God of Gods", "אל האלהים", ["God of gods"]),
    ("Prince of Peace", "שר שלום", ["Prince of Peace", "Prince of peace"]),
    ("Father of Lights", "", ["Father of lights"]),
    ("Ancient of Days", "עתיק יומין", ["Ancient of Days", "Ancient of days"]),
    ("Living God", "אל חי", ["living God", "God who lives"]),
    ("God of Heaven", "אל השמים", ["God of heaven"]),
    ("God of Israel", "אלהי ישראל", ["God of Israel"]),
    ("God of Abraham, Isaac, Jacob", "אלהי אברהם", ["God of Abraham"]),
    ("God of Truth", "אל אמת", ["God of truth"]),
    ("Jealous God", "אל קנא", ["jealous God", "jealous god"]),
    ("God of Salvation", "אל ישועה", ["God of salvation"]),
    ("God of My Righteousness", "אלהי צדקי", ["God of my righteousness"]),
    ("God of Vengeance", "אל נקמות", ["God of vengeance", "God that executeth vengeance"]),

    # ── Descriptive Titles ──
    ("Burning Bush God", "", ["God of the burning bush"]),
    ("God Who Heals", "יהוה רפא", ["God that healeth", "Lord who heals", "the LORD that healeth"]),
    ("God My Provider", "יהוה יראה", ["God will provide", "the LORD will provide"]),
    ("God Our Peace", "יהוה שלום", ["God of peace", "Lord of peace", "the LORD of peace"]),
    ("God Our Righteousness", "יהוה צדקנו", ["God our righteousness", "the LORD our righteousness"]),
    ("God Is There", "יהוה שמה", ["God is there", "the LORD is there"]),
    ("God Who Sanctifies", "יהוה מקדשכם", ["God that doth sanctify", "the LORD which hallow"]),
]


def run(conn, book_ids=None):
    count = 0
    total_title = 0
    batch = []
    
    for title_name, heb_key, eng_keys in TITLES:
        # Search Hebrew text (OT)
        heb_verses = set()
        if heb_key:
            rows = conn.execute(
                "SELECT id FROM verses WHERE text_hebrew LIKE ? AND has_hebrew = 1",
                (f'%{heb_key}%',)
            ).fetchall()
            for r in rows:
                heb_verses.add(r["id"])
        
        # Search English text (NT, BoM, D&C, Apocrypha, Pseudepigrapha)
        eng_verses = set()
        for ek in eng_keys:
            rows = conn.execute(
                "SELECT id FROM verses WHERE text_english LIKE ?",
                (f'%{ek}%',)
            ).fetchall()
            for r in rows:
                eng_verses.add(r["id"])
        
        all_verses = list(heb_verses | eng_verses)
        if len(all_verses) < 2:
            continue
        
        total_title += 1
        
        # Connect hub-style: first verse connects to all others
        # (avoids O(n²) explosion for common titles like "God of Israel")
        hub = all_verses[0]
        for v in all_verses[1:]:
            # Limit to 50 connections per title to avoid noise
            if len(batch) >= 50:
                count += len(batch)
                _flush_batch(conn, batch)
                batch = []
            batch.append((
                hub, v, "symbolic", "name_symbolic", "divine_title",
                0.5, 0.45, "algorithm",
                f'{{"title": "{title_name}", "hebrew": "{heb_key}", "verse_count": {len(all_verses)}}}'
            ))
        
        if len(batch) >= 200:
            count += len(batch)
            _flush_batch(conn, batch)
            batch = []
    
    if batch:
        count += len(batch)
        _flush_batch(conn, batch)
    
    print(f"  Divine Titles: {total_title} titles, {count} connections")
    return count


def _flush_batch(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    batch.clear()
