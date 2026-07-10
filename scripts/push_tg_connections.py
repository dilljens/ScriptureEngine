#!/usr/bin/env python3
"""Push Topical Guide and Bible Dictionary data into the connection graph.

Creates:
1. Verse → TG topic connections (from footnotes + API data)
2. TG topic → TG topic connections (from API "See also" + shared verse overlap)
3. BD entry → verse connections
4. BD entry → TG topic connections

Run after ingest_topical_guide.py.

Usage:
    python3 scripts/push_tg_connections.py
    python3 scripts/push_tg_connections.py --dry-run
    python3 scripts/push_tg_connections.py --min-jaccard 0.15
"""

import sys, os, json, sqlite3, time, math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def get_all_db():
    # Also access the main lib.db for consistent connection handling
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()


def count_existing_tg_connections(conn):
    """Count existing TG connections already in the graph."""
    return conn.execute(
        "SELECT COUNT(*) FROM connections WHERE layer='interpretive' AND type='topical_guide'"
    ).fetchone()[0]


def push_verse_topic_connections(conn, dry_run=False):
    """Push verse → TG topic connections from footnotes + tg_verse_references."""
    import re as _re  # needed for footnote slug generation
    count = 0
    now = time.strftime('%Y-%m-%d')
    
    # Get all TG topics with their slugs
    topics = conn.execute(
        "SELECT slug, name FROM topical_guide"
    ).fetchall()
    topic_slugs = {slug: name for slug, name in topics}
    
    # Track what's already inserted to avoid duplicates
    existing_set = set()
    for row in conn.execute(
        "SELECT source_verse, REPLACE(target_verse, 'tg:', '') FROM connections WHERE layer='interpretive' AND type='topical_guide'"
    ).fetchall():
        existing_set.add((row[0], row[1]))
    
    # Collect all inserts:
    # Method 1: From tg_verse_references table (API-extracted data)
    inserts = []
    refs = conn.execute(
        "SELECT topic_id, verse_id FROM tg_verse_references"
    ).fetchall()
    for topic_slug, verse_id in refs:
        if topic_slug not in topic_slugs:
            continue
        if (verse_id, topic_slug) in existing_set:
            continue
        if not dry_run:
            inserts.append((verse_id, topic_slug, topic_slugs[topic_slug], "api_extract"))
        else:
            count += 1
    
    # Method 2: From footnotes (original source — catches any missed by API)
    footnotes = conn.execute(
        "SELECT verse_id, reference_data FROM footnotes WHERE category='tg'"
    ).fetchall()
    for verse_id, ref_json in footnotes:
        try:
            ref_data = json.loads(ref_json)
        except:
            continue
        for ref in ref_data:
            text = ref.get('text', '')
            name = text.replace('TG\u00a0', '').replace('TG ', '').strip()
            if not name or name.startswith('BD'):
                continue
            slug = name.lower()
            slug = _re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
            if not slug:
                continue
            if (verse_id, slug) in existing_set:
                continue
            existing_set.add((verse_id, slug))
            if not dry_run:
                inserts.append((verse_id, slug, name, "footnote"))
            else:
                count += 1
    
    if not dry_run and inserts:
        for verse_id, slug, name, source in inserts:
            target = f"tg:{slug}"
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO connections 
                        (source_verse, target_verse, layer, type, subtype, 
                         strength, confidence, discovered_by, metadata,
                         quality_level, created_at)
                    VALUES (?, ?, 'interpretive', 'topical_guide', '',
                            0.7, 0.95, 'lds_topical_guide', ?,
                            'strong', ?)
                """, (verse_id, target,
                      json.dumps({"topic_name": name, "source": source}),
                      now))
                count += 1
            except Exception as e:
                pass
        conn.commit()
        print(f"  Inserted {count} verse→TG connections")
    elif dry_run:
        print(f"  Would insert {count} verse→TG connections")
    else:
        print(f"  No new verse→TG connections to insert")
    
    return count


def push_tg_cross_references(conn, dry_run=False, min_jaccard=0.1):
    """Push TG topic → TG topic connections (See also + shared verses)."""
    count = 0
    now = time.strftime('%Y-%m-%d')
    
    # Method A: From API "See also" references
    topics = conn.execute(
        "SELECT slug, related_topic_ids FROM topical_guide"
    ).fetchall()
    
    api_count = 0
    for slug, rel_json in topics:
        if not rel_json:
            continue
        try:
            rel_topics = json.loads(rel_json)
        except:
            continue
        for rel_slug in rel_topics:
            if not rel_slug:
                continue
            api_count += 1  # count first, regardless of dry-run
            if not dry_run:
                source = f"tg:{slug}"
                target = f"tg:{rel_slug}"
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype,
                             strength, confidence, discovered_by, metadata,
                             quality_level, created_at)
                        VALUES (?, ?, 'interpretive', 'topical_see_also', '',
                                0.6, 0.9, 'lds_topical_guide', ?,
                                'strong', ?)
                    """, (source, target,
                          json.dumps({"source": "api_cross_ref"}),
                          now))
                except:
                    api_count -= 1  # failed insert
    
    if dry_run:
        print(f"  Would insert {api_count} TG→TG API cross-refs")
    else:
        conn.commit()
        print(f"  Inserted {api_count} TG→TG API cross-refs")
    
    count += api_count
    
    # Method B: Auto-generate from shared verse overlap (Jaccard similarity)
    # Get verse sets per topic
    topic_verses = {}
    for row in conn.execute(
        "SELECT target_verse, source_verse FROM connections WHERE layer='interpretive' AND type='topical_guide'"
    ).fetchall():
        topic = row[0]  # tg:slug
        verse = row[1]
        if topic not in topic_verses:
            topic_verses[topic] = set()
        topic_verses[topic].add(verse)
    
    # Only compare topics that share at least 3 verses
    topic_list = list(topic_verses.keys())
    shared_count = 0
    
    # Build an index: verse → list of topics
    verse_topics = {}
    for topic, verses in topic_verses.items():
        for v in verses:
            if v not in verse_topics:
                verse_topics[v] = []
            verse_topics[v].append(topic)
    
    # For each pair of topics that appear together in at least 3 verses
    topic_pair_shared = {}
    for verse, tops in verse_topics.items():
        for i in range(len(tops)):
            for j in range(i + 1, len(tops)):
                a, b = tops[i], tops[j]
                if a > b:
                    a, b = b, a
                key = (a, b)
                topic_pair_shared[key] = topic_pair_shared.get(key, 0) + 1
    
    # Compute Jaccard for pairs with ≥3 shared verses
    for (topic_a, topic_b), shared in topic_pair_shared.items():
        if shared < 3:
            continue
        set_a = topic_verses.get(topic_a, set())
        set_b = topic_verses.get(topic_b, set())
        union = len(set_a | set_b)
        jaccard = shared / max(union, 1)
        
        if jaccard >= min_jaccard:
            # Check if direct connection already exists
            existing = conn.execute(
                "SELECT 1 FROM connections WHERE source_verse=? AND target_verse=? AND type='topical_see_also'",
                (topic_a, topic_b)
            ).fetchone()
            if existing:
                continue
            
            shared_count += 1  # count first
            if not dry_run:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype,
                             strength, confidence, discovered_by, metadata,
                             quality_level, created_at)
                        VALUES (?, ?, 'interpretive', 'topical_shared_verses', '',
                                ?, 0.8, 'shared_verse_overlap', ?,
                                'suggested', ?)
                    """, (topic_a, topic_b,
                          round(min(1.0, jaccard * 2), 2),
                          json.dumps({"jaccard": round(jaccard, 3), "shared_verses": shared,
                                      "union_verses": union}),
                          now))
                except:
                    shared_count -= 1  # failed insert
    
    if dry_run:
        print(f"  Would insert {shared_count} shared-verse TG→TG connections")
    else:
        conn.commit()
        print(f"  Inserted {shared_count} shared-verse TG→TG connections (Jaccard ≥ {min_jaccard})")
    
    count += shared_count
    return count


def push_bd_connections(conn, dry_run=False):
    """Push Bible Dictionary entry connections."""
    count = 0
    now = time.strftime('%Y-%m-%d')
    
    # Get BD entries with their related verses and topics
    bd_entries = conn.execute(
        "SELECT slug, name, related_verses, related_topics FROM bible_dictionary"
    ).fetchall()
    
    for slug, name, vers_json, topics_json in bd_entries:
        bd_id = f"bd:{slug}"
        
        # BD → verses
        try:
            verses = json.loads(vers_json) if vers_json else []
        except:
            verses = []
        for verse_id in verses:
            if not dry_run:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype,
                             strength, confidence, discovered_by, metadata,
                             quality_level, created_at)
                        VALUES (?, ?, 'interpretive', 'bible_dictionary', '',
                                0.8, 0.95, 'bible_dictionary', ?,
                                'strong', ?)
                    """, (bd_id, verse_id,
                          json.dumps({"entry_name": name, "source": "bible_dictionary_api"}),
                          now))
                    count += 1
                except:
                    pass
        
        # BD → TG topics
        try:
            bd_topics = json.loads(topics_json) if topics_json else []
        except:
            bd_topics = []
        for t in bd_topics:
            t_slug = t if isinstance(t, str) else t.get("slug", "")
            if not t_slug:
                continue
            target = f"tg:{t_slug}"
            if not dry_run:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype,
                             strength, confidence, discovered_by, metadata,
                             quality_level, created_at)
                        VALUES (?, ?, 'interpretive', 'bible_dictionary_tg', '',
                                0.7, 0.85, 'bible_dictionary', ?,
                                'strong', ?)
                    """, (bd_id, target,
                          json.dumps({"entry_name": name, "source": "bible_dictionary_api"}),
                          now))
                    count += 1
                except:
                    pass
    
    if dry_run:
        print(f"  Would insert {count} BD connections")
    else:
        conn.commit()
        print(f"  Inserted {count} BD connections")
    
    return count


def update_topic_importance(conn):
    """Update TG topic importance scores based on verse count and centrality."""
    max_verse_count = conn.execute(
        "SELECT MAX(verse_count) FROM topical_guide"
    ).fetchone()[0] or 1
    
    topics = conn.execute(
        "SELECT slug, verse_count FROM topical_guide"
    ).fetchall()
    
    for slug, vc in topics:
        # Get connection count from graph
        conn_count = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE source_verse=? OR target_verse=?",
            (f"tg:{slug}", f"tg:{slug}")
        ).fetchone()[0]
        
        # Importance = normalized verse count + normalized connection count
        importance = (vc / max_verse_count) * 0.5 + min(conn_count / 100, 1) * 0.5
        importance = round(importance, 3)
        
        conn.execute(
            "UPDATE topical_guide SET importance=? WHERE slug=?",
            (importance, slug)
        )
    
    conn.commit()
    print(f"  Updated importance for {len(topics)} topics")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Push TG/BD data into connection graph")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no inserts")
    parser.add_argument("--min-jaccard", type=float, default=0.1, help="Min Jaccard for shared-verse links")
    args = parser.parse_args()
    
    import re  # needed by footnote parsing
    
    print("=" * 60)
    print("Pushing TG/BD Data into Connection Graph")
    print("=" * 60)
    
    conn = get_conn()
    
    # Check existing
    existing = count_existing_tg_connections(conn)
    print(f"\nExisting TG connections in graph: {existing}")
    
    # Phase 1: Verse → TG
    print(f"\n[1/4] Verse → TG topic connections...")
    v1 = push_verse_topic_connections(conn, dry_run=args.dry_run)
    
    # Phase 2: TG → TG cross-references
    print(f"\n[2/4] TG → TG cross-references...")
    v2 = push_tg_cross_references(conn, dry_run=args.dry_run, min_jaccard=args.min_jaccard)
    
    # Phase 3: BD connections
    print(f"\n[3/4] Bible Dictionary connections...")
    v3 = push_bd_connections(conn, dry_run=args.dry_run)
    
    # Phase 4: Update importance
    print(f"\n[4/4] Updating topic importance scores...")
    if not args.dry_run:
        update_topic_importance(conn)
    
    total = v1 + v2 + v3
    summary = (f"\n{'=' * 60}\n"
               f"Summary:\n"
               f"  Verse→TG: {v1}\n"
               f"  TG→TG:   {v2}\n"
               f"  BD:      {v3}\n"
               f"  Total:   {total}\n"
               f"{'=' * 60}\n")
    print(summary)
    
    conn.close()


if __name__ == "__main__":
    main()
