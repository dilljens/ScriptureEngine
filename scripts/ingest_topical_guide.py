#!/usr/bin/env python3
"""Ingest LDS Topical Guide and Bible Dictionary from Church API.

Extracts 677 TG topics and Bible Dictionary entries from the
churchofjesuschrist.org API, parsing each topic's description,
cross-references, and verse references into structured data.

Usage:
    python3 scripts/ingest_topical_guide.py                  # Fetch all topics
    python3 scripts/ingest_topical_guide.py --test            # Fetch first 3 topics only
    python3 scripts/ingest_topical_guide.py --skip-fetch      # Use existing data only
"""

import sys, os, json, re, time, sqlite3, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_BASE = "https://www.churchofjesuschrist.org/study/api/v3/language-pages/type/content?lang=eng&uri="
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ScriptureExplorer/1.0 (research project)",
}

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


SCHEMA = """
CREATE TABLE IF NOT EXISTS topical_guide (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    url_path TEXT DEFAULT '',
    parent_topic_id TEXT,
    related_topic_ids TEXT DEFAULT '[]',
    related_bd_entries TEXT DEFAULT '[]',
    verse_count INTEGER DEFAULT 0,
    importance REAL DEFAULT 0.5,
    raw_html TEXT DEFAULT '',
    last_fetched TEXT
);

CREATE TABLE IF NOT EXISTS bible_dictionary (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    entry_text TEXT NOT NULL,
    summary TEXT DEFAULT '',
    url_path TEXT DEFAULT '',
    word_origin TEXT DEFAULT '',
    related_verses TEXT DEFAULT '[]',
    related_topics TEXT DEFAULT '[]',
    related_entries TEXT DEFAULT '[]',
    raw_html TEXT DEFAULT '',
    last_fetched TEXT
);

CREATE TABLE IF NOT EXISTS tg_verse_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topical_guide(id),
    verse_id TEXT NOT NULL,
    snippet TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    UNIQUE(topic_id, verse_id)
);
"""


def make_slug(name):
    """Generate URL-safe slug from a TG topic name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def extract_topics_from_footnotes():
    """Extract unique TG topic names from existing footnotes table."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT verse_id, reference_data FROM footnotes WHERE category='tg'"
    ).fetchall()
    conn.close()

    topics = {}  # name -> {verses: set, slug: str}
    for verse_id, ref_json in rows:
        try:
            refs = json.loads(ref_json)
            for ref in refs:
                text = ref.get('text', '')
                name = text.replace('TG\u00a0', '').replace('TG ', '').strip()
                if name and not name.startswith('BD'):
                    if name not in topics:
                        topics[name] = {"verses": set(), "slug": make_slug(name)}
                    topics[name]["verses"].add(verse_id)
        except:
            pass

    # Also check for BD references from footnotes
    bd_topics = {}
    for verse_id, ref_json in rows:
        try:
            refs = json.loads(ref_json)
            for ref in refs:
                text = ref.get('text', '')
                name = text.replace('TG\u00a0', '').replace('TG ', '').strip()
                if name.startswith('BD'):
                    bd_name = name.replace('BD\u00a0', '').replace('BD ', '').strip()
                    if bd_name and bd_name not in bd_topics:
                        bd_topics[bd_name] = {"verses": set(), "slug": make_slug(bd_name)}
                    if bd_name:
                        bd_topics[bd_name]["verses"].add(verse_id)
        except:
            pass

    return topics, bd_topics


def fetch_topic_page(slug):
    """Fetch a TG topic page from the Church API. Returns dict or None."""
    url = f"{API_BASE}/scriptures/tg/{slug}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data
    except urllib.error.HTTPError as e:
        return None
    except Exception as e:
        return None


def fetch_bd_entry(slug):
    """Fetch a Bible Dictionary entry from the Church API."""
    url = f"{API_BASE}/scriptures/bd/{slug}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data
    except:
        return None


def parse_tg_page(data, name, slug):
    """Parse a TG topic page into structured data.
    
    Returns: {name, slug, description, summary, related_topics, related_bd, verses: [{id, snippet}]}
    """
    if not data:
        return None
    
    content = data.get("content", {})
    body = content.get("body", "")
    
    result = {
        "name": name,
        "slug": slug,
        "description": "",
        "summary": "",
        "related_topics": [],
        "related_bd": [],
        "verses": [],
        "raw_html": body,
    }
    
    # Extract description: first <p> after <h1> (the header)
    desc_match = re.search(r'<h1[^>]*>.*?</h1>\s*(.*?)</header>', body, re.DOTALL)
    if desc_match:
        desc_text = re.sub(r'<[^>]+>', ' ', desc_match.group(1)).strip()
        desc_text = re.sub(r'\s+', ' ', desc_text)
        result["description"] = desc_text
        result["summary"] = desc_text[:200] if len(desc_text) > 200 else desc_text
    
    # Extract "See also" cross-references
    see_also_section = re.search(r'<em>See also</em>(.*?)</ul>', body, re.DOTALL)
    if see_also_section:
        see_also_html = see_also_section.group(1)
        # Extract TG links
        for m in re.finditer(r'href="/study/scriptures/tg/([^"]+)"[^>]*>([^<]+)</a>', see_also_html):
            result["related_topics"].append({
                "slug": m.group(1).replace('?lang=eng', ''),
                "name": m.group(2).strip()
            })
        # Extract BD links
        for m in re.finditer(r'href="/study/scriptures/bd/([^"]+)"[^>]*>([^<]+)</a>', see_also_html):
            result["related_bd"].append({
                "slug": m.group(1).replace('?lang=eng', ''),
                "name": m.group(2).strip()
            })
    
    # Extract verse references: <p class="entry">...snippet..., <a class="scripture-ref">verse</a>
    verse_entries = re.findall(
        r'<p[^>]*class="entry"[^>]*>(.*?)</p>', body, re.DOTALL
    )
    verse_ref_pattern = re.compile(
        r'/study/scriptures/([^/]+)/([^/]+?)/(\d+)[^"]*id=p(\d+)'
    )
    SUB_BOOK_MAP = {
        'gen': 'gen', 'ex': 'exo', 'lev': 'lev', 'num': 'num', 'deu': 'deu',
        'josh': 'josh', 'judg': 'judg', 'ruth': 'ruth',
        '1-sam': '1sam', '2-sam': '2sam', '1-kgs': '1kgs', '2-kgs': '2kgs',
        '1-chr': '1chr', '2-chr': '2chr', 'ezra': 'ezra', 'neh': 'neh', 'esth': 'esth',
        'job': 'job', 'ps': 'psa', 'prov': 'prov', 'eccl': 'eccl', 'song': 'song',
        'isa': 'isa', 'jer': 'jer', 'lam': 'lam', 'ezek': 'ezek', 'dan': 'dan',
        'hos': 'hos', 'joel': 'joel', 'amos': 'amos', 'obad': 'obad', 'jonah': 'jonah',
        'mic': 'mic', 'nah': 'nah', 'hab': 'hab', 'zeph': 'zeph', 'hag': 'hag',
        'zech': 'zech', 'mal': 'mal',
        'matt': 'matt', 'mark': 'mark', 'luke': 'luke', 'john': 'john',
        'acts': 'acts', 'rom': 'rom',
        '1-cor': '1cor', '2-cor': '2cor', 'gal': 'gal', 'eph': 'eph',
        'phil': 'phil', 'col': 'col',
        '1-thes': '1thes', '2-thes': '2thes', '1-tim': '1tim', '2-tim': '2tim',
        'titus': 'titus', 'philem': 'philem', 'heb': 'heb',
        'james': 'james', '1-pet': '1pet', '2-pet': '2pet',
        '1-jn': '1john', '2-jn': '2john', '3-jn': '3john', 'jude': 'jude',
        'rev': 'rev',
        '1-ne': '1ne', '2-ne': '2ne', 'jacob': 'jacob', 'enos': 'enos',
        'jarom': 'jarom', 'omni': 'omni', 'w-of-m': 'wom',
        'mosiah': 'mosiah', 'alma': 'alma', 'hel': 'hel',
        '3-ne': '3ne', '4-ne': '4ne', 'morm': 'morm', 'ether': 'ether', 'moro': 'moro',
        'moses': 'moses', 'abr': 'abraham', 'js-m': 'jsm', 'js-h': 'jsh', 'a-of-f': 'aoff',
    }
    
    for entry_html in verse_entries:
        # Clean snippet: remove HTML tags, get text before the link
        snippet = re.sub(r'<[^>]+>', ' ', entry_html).strip()
        snippet = re.sub(r'\s+', ' ', snippet)
        # Truncate at the verse reference
        snippet = snippet[:200]
        
        # Find verse reference
        ref_match = verse_ref_pattern.search(entry_html)
        if ref_match:
            vol, book_path, chapter, verse = ref_match.groups()
            book_id = SUB_BOOK_MAP.get(book_path)
            if book_id:
                if vol == 'dc-testament':
                    verse_id = f"dc{chapter}.{verse}"
                else:
                    verse_id = f"{book_id}.{chapter}.{verse}"
                result["verses"].append({
                    "id": verse_id,
                    "snippet": snippet,
                })
    
    return result


def parse_bd_page(data, name, slug):
    """Parse a Bible Dictionary entry page."""
    if not data:
        return None
    
    content = data.get("content", {})
    body = content.get("body", "")
    
    result = {
        "name": name,
        "slug": slug,
        "entry_text": "",
        "summary": "",
        "related_verses": [],
        "related_topics": [],
        "related_entries": [],
        "raw_html": body,
    }
    
    # Extract entry text from body
    entry_text = re.sub(r'<[^>]+>', ' ', body)
    entry_text = re.sub(r'\s+', ' ', entry_text).strip()
    result["entry_text"] = entry_text
    result["summary"] = entry_text[:300] if len(entry_text) > 300 else entry_text
    
    # Extract related verses from scripture-ref links
    # Simpler two-step regex: extract URL path first, then verse fragment
    verse_ref_pattern = re.compile(
        r'/study/scriptures/([^/]+)/([^/]+)/(\d+)'
    )
    verse_frag_pattern = re.compile(r'[?&]id=p(\d+)')
    
    SUB_BOOK_MAP_BD = {
        'gen': 'gen', 'ex': 'exo', 'lev': 'lev', 'num': 'num', 'deu': 'deu',
        'josh': 'josh', 'judg': 'judg', 'ruth': 'ruth',
        '1-sam': '1sam', '2-sam': '2sam',
        'ps': 'psa', 'isa': 'isa', 'jer': 'jer',
        'matt': 'matt', 'luke': 'luke', 'john': 'john',
        'acts': 'acts', 'rom': 'rom',
        '1-cor': '1cor', '2-cor': '2cor',
        'gal': 'gal', 'eph': 'eph', 'phil': 'phil', 'col': 'col',
        '1-thes': '1thes', '2-thes': '2thes',
        '1-tim': '1tim', '2-tim': '2tim', 'titus': 'titus', 'philem': 'philem',
        'heb': 'heb', 'james': 'james',
        '1-pet': '1pet', '2-pet': '2pet',
        '1-jn': '1john', '2-jn': '2john', '3-jn': '3john', 'jude': 'jude',
        'rev': 'rev',
        '1-ne': '1ne', '2-ne': '2ne', 'jacob': 'jacob', 'enos': 'enos',
        'jarom': 'jarom', 'omni': 'omni', 'w-of-m': 'wom',
        'mosiah': 'mosiah', 'alma': 'alma', 'hel': 'hel',
        '3-ne': '3ne', '4-ne': '4ne', 'morm': 'morm', 'ether': 'ether', 'moro': 'moro',
        'moses': 'moses', 'abr': 'abraham',
    }
    
    for m in verse_ref_pattern.finditer(body):
        vol, book_path, chapter = m.groups()
        # Find verse number in the fragment after this match
        rest = body[m.end():m.end()+80]
        verse_m = verse_frag_pattern.search(rest)
        verse = verse_m.group(1) if verse_m else '1'
        book_id = SUB_BOOK_MAP_BD.get(book_path)
        if book_id:
            if vol == 'dc-testament':
                result["related_verses"].append(f"dc{chapter}.{verse}")
            else:
                result["related_verses"].append(f"{book_id}.{chapter}.{verse}")
    
    # Extract related TG topics
    for m in re.finditer(
        r'href="/study/scriptures/tg/([^"]+)"[^>]*>([^<]+)</a>', body
    ):
        result["related_topics"].append({
            "slug": m.group(1).replace('?lang=eng', ''),
            "name": m.group(2).strip()
        })
    
    return result


def store_topics(conn, topics_data, topic_verse_map):
    """Store parsed TG topics in the database."""
    count = 0
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    for name, data in topics_data.items():
        slug = topic_verse_map.get(name, {}).get("slug", make_slug(name))
        verses = topic_verse_map.get(name, {}).get("verses", set())
        
        related_topics = json.dumps([t["slug"] for t in data.get("related_topics", [])])
        related_bd = json.dumps([t["slug"] for t in data.get("related_bd", [])])
        
        description = data.get("description", "")
        summary = data.get("summary", description[:200])
        raw_html = data.get("raw_html", "")
        
        conn.execute("""
            INSERT OR REPLACE INTO topical_guide
                (id, name, slug, description, summary, url_path, related_topic_ids, related_bd_entries, verse_count, raw_html, last_fetched)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slug, name, slug, description, summary,
            f"/study/scriptures/tg/{slug}",
            related_topics, related_bd,
            len(verses), raw_html, now
        ))
        
        # Store verse references
        for v_data in data.get("verses", []):
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO tg_verse_references (topic_id, verse_id, snippet)
                    VALUES (?, ?, ?)
                """, (slug, v_data["id"], v_data["snippet"][:500]))
            except:
                pass
        
        count += 1
    
    conn.commit()
    return count


def store_bd_entries(conn, bd_data):
    """Store parsed BD entries in the database."""
    count = 0
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    for name, data in bd_data.items():
        slug = make_slug(name)
        related_verses = json.dumps(data.get("related_verses", []))
        related_topics = json.dumps([t["slug"] for t in data.get("related_topics", [])])
        
        conn.execute("""
            INSERT OR REPLACE INTO bible_dictionary
                (id, name, slug, entry_text, summary, url_path, related_verses, related_topics, raw_html, last_fetched)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slug, name, slug,
            data.get("entry_text", ""),
            data.get("summary", ""),
            f"/study/scriptures/bd/{slug}",
            related_verses, related_topics,
            data.get("raw_html", ""),
            now
        ))
        count += 1
    
    conn.commit()
    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest LDS Topical Guide and Bible Dictionary")
    parser.add_argument("--test", action="store_true", help="Fetch first 3 topics only")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip API fetch, use existing data only")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent API workers")
    args = parser.parse_args()
    
    global urllib
    import urllib.request, urllib.error
    
    print("=" * 60)
    print("LDS Topical Guide & Bible Dictionary Ingest")
    print("=" * 60)
    
    # Initialize DB
    conn = get_conn()
    for stmt in SCHEMA.split(";"):
        if stmt.strip():
            conn.execute(stmt)
    conn.commit()
    
    # Extract topics from footnotes
    print("\n[1/4] Extracting TG topics from footnotes...")
    topics, bd_topics = extract_topics_from_footnotes()
    print(f"  Found {len(topics)} unique TG topics")
    print(f"  Found {len(bd_topics)} BD references in TG footnotes")
    
    if args.test:
        topics = dict(list(topics.items())[:3])
        print(f"  TEST MODE: limiting to {len(topics)} topics")
    
    if args.skip_fetch:
        print("  SKIP-FETCH: using existing data only")
    else:
        # Fetch TG topic pages
        print(f"\n[2/4] Fetching {len(topics)} TG topic pages ({args.workers} workers)...")
        topics_data = {}
        fetched = 0
        failed = 0
        
        # Process in batches
        topic_items = list(topics.items())
        batch_size = args.workers * 2
        
        for batch_start in range(0, len(topic_items), batch_size):
            batch = topic_items[batch_start:batch_start + batch_size]
            batch_results = {}
            
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                future_map = {
                    pool.submit(fetch_topic_page, info["slug"]): (name, info)
                    for name, info in batch
                }
                for future in as_completed(future_map):
                    name, info = future_map[future]
                    try:
                        data = future.result(timeout=45)
                        if data:
                            parsed = parse_tg_page(data, name, info["slug"])
                            if parsed:
                                batch_results[name] = parsed
                                fetched += 1
                            else:
                                failed += 1
                        else:
                            failed += 1
                    except TimeoutError:
                        failed += 1
                    except Exception:
                        failed += 1
            
            topics_data.update(batch_results)
            
            # Progress
            done = min(batch_start + batch_size, len(topic_items))
            pct = done / len(topic_items) * 100
            print(f"    [{done}/{len(topic_items)}] {pct:.0f}% — {fetched} fetched, {failed} failed")
            
            # Small delay between batches to be nice to the API
            time.sleep(0.3)
        
        print(f"\n  Results: {fetched} fetched, {failed} failed")
        
        # Store topics
        print(f"\n[3/4] Storing {len(topics_data)} TG topics in database...")
        stored = store_topics(conn, topics_data, topics)
        print(f"  Stored {stored} topics")
        
        # Fetch and store BD entries
        print(f"\n[4/4] Fetching Bible Dictionary entries...")
        # Start with known entries from footnotes + commonly cited ones
        bd_slugs_to_fetch = [
            "faith", "melchizedek", "urim-and-thummim", "heaven", "idumea", "priests",
            "apocrypha", "elias", "lots", "money",
            # Additional important entries
            "jesus-christ", "atonement", "repentance", "baptism", "holy-ghost",
            "prayer", "resurrection", "revelation", "temple", "priesthood",
            "israel", "jerusalem", "sabbath", "passover", "tabernacle",
            "covenant", "grace", "faith", "hope", "charity",
        ]
        bd_data = {}
        bd_fetched = 0
        bd_failed = 0
        
        for entry_slug in bd_slugs_to_fetch:
            data = fetch_bd_entry(entry_slug)
            if data:
                parsed = parse_bd_page(data, entry_slug.replace("-", " ").title(), entry_slug)
                if parsed:
                    bd_data[parsed["name"]] = parsed
                    bd_fetched += 1
            else:
                bd_failed += 1
            time.sleep(0.1)
        
        print(f"  {bd_fetched} BD entries fetched, {bd_failed} failed")
        if bd_data:
            stored_bd = store_bd_entries(conn, bd_data)
            print(f"  Stored {stored_bd} BD entries")
    
    # Summary
    tg_count = conn.execute("SELECT COUNT(*) FROM topical_guide").fetchone()[0]
    bd_count = conn.execute("SELECT COUNT(*) FROM bible_dictionary").fetchone()[0]
    ref_count = conn.execute("SELECT COUNT(*) FROM tg_verse_references").fetchone()[0]
    
    print(f"\n{'=' * 60}")
    print(f"Database Summary:")
    print(f"  Topical Guide topics: {tg_count}")
    print(f"  Bible Dictionary entries: {bd_count}")
    print(f"  Verse references: {ref_count}")
    print(f"{'=' * 60}")
    
    conn.close()


if __name__ == "__main__":
    main()
