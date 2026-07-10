#!/usr/bin/env python3
"""Ingest Joseph Smith's public-domain teachings from Wikisource.

Seeds the js_sources table with discourses, letters, and writings
available on Wikisource under public domain.

After ingestion, connections to scripture can be added via
tools/js_sources.py or the existing prophetic_quote mechanism.
"""

import sys, os, re, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db

# ── Public domain JS sources on Wikisource ──
# Each entry: (ref_id, title, date, source_type, location, source_url, source_manuscript)

JST_TEACHINGS = [
    # ── Sermons ──
    {
        "ref_id": "js.1839.06.02",
        "title": "The Priesthood—The Second Advent—The Gathering—Spiritual Ministrations and Manifestations",
        "date": "1839-06-02",
        "source_type": "sermon",
        "location": "Commerce, Illinois",
        "source": "Journal of Discourses 6:8-11",
        "url": "https://en.wikisource.org/wiki/Journal_of_Discourses/Volume_6/The_Priesthood,_etc.",
    },
    {
        "ref_id": "js.1843.06.30",
        "title": "The Constitutions of the United States and Illinois",
        "date": "1843-06-30",
        "source_type": "sermon",
        "location": "Nauvoo, Illinois",
        "source": "Journal of Discourses 2:19-23",
        "url": "https://en.wikisource.org/wiki/Journal_of_Discourses/Volume_2/The_Constitutions_of_the_United_States_and_Illinois,_etc.",
    },
    {
        "ref_id": "js.1844.04.06",
        "title": "Character and Being of God—Creation—Salvation of the Dead—The Unpardonable Sin—Resurrection—Baptism of the Spirit",
        "date": "1844-04-06",
        "source_type": "sermon",
        "location": "Nauvoo, Illinois",
        "source": "Journal of Discourses 6:1-7",
        "url": "https://en.wikisource.org/wiki/Journal_of_Discourses/Volume_6/Character_and_Being_of_God,_etc.",
    },
    {
        "ref_id": "js.1844.04.07",
        "title": "King Follett Discourse",
        "date": "1844-04-07",
        "source_type": "sermon",
        "location": "Nauvoo, Illinois (Grove east of Temple)",
        "source": "Multiple scribes: Wilford Woodruff, Thomas Bullock, etc.",
        "url": "https://en.wikisource.org/wiki/King_Follett_Discourse",
    },
    # ── Letters ──
    {
        "ref_id": "js.1842.03.01",
        "title": "The Wentworth Letter",
        "date": "1842-03-01",
        "source_type": "letter",
        "location": "Nauvoo, Illinois",
        "source": "Times and Seasons 3:9 (March 1, 1842)",
        "url": "https://en.wikisource.org/wiki/The_Wentworth_Letter",
    },
    {
        "ref_id": "js.1844.06.14",
        "title": "Letter from Joseph Smith to Thomas Ford",
        "date": "1844-06-14",
        "source_type": "letter",
        "location": "Nauvoo, Illinois",
        "source": "Published in History of the Church 6:500-504",
        "url": "https://en.wikisource.org/wiki/Letter_from_Joseph_Smith_to_Thomas_Ford_(14_June_1844)",
    },
    {
        "ref_id": "js.1843.03.27",
        "title": "Letter from Joseph Smith to Sidney Rigdon",
        "date": "1843-03-27",
        "source_type": "letter",
        "location": "Nauvoo, Illinois",
        "source": "Published in History of the Church",
        "url": "https://en.wikisource.org/wiki/Letter_from_Joseph_Smith_to_Sidney_Rigdon_(27_March_1843)",
    },
    # ── Rupp Letter ──
    {
        "ref_id": "js.1844.01.01",
        "title": "Letter to I. Daniel Rupp (The Rupp Letter)",
        "date": "1844",
        "source_type": "letter",
        "location": "Nauvoo, Illinois",
        "source": "Published in History of the Church",
        "url": "https://en.wikisource.org/wiki/The_Rupp_Letter",
    },
]


def fetch_wikisource_text(url):
    """Fetch raw wikitext from a Wikisource page via action=raw."""
    import urllib.request
    
    # Extract page title from URL
    page_match = re.search(r'wiki/(.+)$', url)
    if not page_match:
        return None
    
    page_title = page_match.group(1)
    raw_url = f"https://en.wikisource.org/w/index.php?title={page_title}&action=raw"
    
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "scriptureengine/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        return raw
    except Exception as e:
        print(f"    Error fetching {raw_url}: {e}")
        return None


def extract_text_from_wikitext(raw):
    """Extract readable text from wikitext markup."""
    if not raw:
        return ""
    
    text = raw
    
    # Remove templates {{...}} (recursive)
    while re.search(r'\{\{[^}]*\}\}', text):
        text = re.sub(r'\{\{[^}]*\}\}', '', text)
    
    # Remove references <ref>...</ref>
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^>]*/>', '', text)
    
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Remove wiki markup
    text = re.sub(r"'''", '', text)     # bold
    text = re.sub(r"''", '', text)      # italic
    text = re.sub(r'\[\[([^\]|]*)\]\]', r'\1', text)  # [[links]]
    text = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', text)  # [[target|text]]
    text = re.sub(r'\[https?://[^\]]+\]', '', text)  # [http links]
    text = re.sub(r'\[https?://[^\]]+\s([^\]]*)\]', r'\1', text)  # [http text]
    
    # Remove headers/section markers
    text = re.sub(r'^=+\s*.*?\s*=+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove {{pagenum|N}} markers
    text = re.sub(r'\{\{pagenum\|[^}]*\}\}', '', text)
    
    # Remove ---- horizontal rules
    text = re.sub(r'^-{4,}\s*$', '', text, flags=re.MULTILINE)
    
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


def main():
    conn = get_db()
    count_ingested = 0
    count_failed = 0
    
    for source in JST_TEACHINGS:
        ref_id = source["ref_id"]
        print(f"\n[{ref_id}] {source['title'][:60]}...")
        
        # Check if already ingested
        existing = conn.execute("SELECT 1 FROM js_sources WHERE ref_id=?", (ref_id,)).fetchone()
        if existing:
            print(f"  Already exists, skipping.")
            count_ingested += 1
            continue
        
        # Fetch text
        url = source.get("url", "")
        if not url:
            print(f"  No URL, skipping.")
            count_failed += 1
            continue
        
        print(f"  Fetching from Wikisource...")
        raw = fetch_wikisource_text(url)
        if not raw:
            print(f"  Failed to fetch, skipping.")
            count_failed += 1
            continue
        
        # Extract clean text
        text = extract_text_from_wikitext(raw)
        if len(text) < 50:
            print(f"  Extracted text too short ({len(text)} chars), trying direct fetch...")
            # Try direct page text
            text = raw[:5000]  # fallback to raw
        
        print(f"  Extracted {len(text)} characters")
        
        # Store in database
        try:
            conn.execute("""
                INSERT OR REPLACE INTO js_sources (ref_id, title, date, source_type, location, source, text, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ref_id, source["title"], source["date"],
                source["source_type"], source.get("location", ""),
                source.get("source", ""), text,
                json.dumps({"url": source.get("url", ""), "source_type": source["source_type"]})
            ))
            count_ingested += 1
        except Exception as e:
            print(f"  DB error: {e}")
            count_failed += 1
            continue
        
        conn.commit()
        print(f"  ✅ Ingested ({len(text)} chars)")
    
    print(f"\n{'='*50}")
    print(f"Ingested: {count_ingested}")
    print(f"Failed: {count_failed}")
    print(f"Connections: {count_connections}")
    
    # Stats
    total = conn.execute("SELECT COUNT(*) FROM js_sources").fetchone()[0]
    print(f"\nTotal JS sources: {total}")
    
    conn.close()


if __name__ == "__main__":
    main()
