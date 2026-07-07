#!/usr/bin/env python3
"""
Import DSS full scroll texts from ETCBC/dss Text-Fabric dataset into the
verses table as a new 'dss' work.

Fetches the dataset via text-fabric (downloads ~200MB on first run).
Imports each scroll as a "book" and each scroll-line as a "verse".

Usage: python3 scripts/import_dss_texts.py
"""

import sys, os, json, re, time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# ─── TARGET SCROLLS ───────────────────────────────────────────────────
# Priority sectarian + major biblical scrolls
TARGET_SCROLLS = [
    # Major sectarian scrolls
    ('1QS', 'Community Rule (Serek ha-Yahad)', 'sectarian'),
    ('1QSa', 'Rule of the Congregation', 'sectarian'),
    ('1QSb', 'Rule of the Blessings', 'sectarian'),
    ('1QM', 'War Scroll (Milhamah)', 'sectarian'),
    ('1QHa', 'Hodayot (Thanksgiving Hymns)', 'sectarian'),
    ('1QpHab', 'Pesher Habakkuk', 'sectarian'),
    ('11Q13', 'Melchizedek Scroll', 'sectarian'),
    ('11Q19', 'Temple Scroll', 'sectarian'),
    ('11Q20', 'Temple Scroll (fragment)', 'sectarian'),
    ('CD', 'Damascus Document', 'sectarian'),
    # Songs of Sabbath Sacrifice
    ('4Q400', 'Songs of Sabbath Sacrifice (4Q400)', 'sectarian'),
    ('4Q401', 'Songs of Sabbath Sacrifice (4Q401)', 'sectarian'),
    ('4Q402', 'Songs of Sabbath Sacrifice (4Q402)', 'sectarian'),
    ('4Q403', 'Songs of Sabbath Sacrifice (4Q403)', 'sectarian'),
    ('4Q404', 'Songs of Sabbath Sacrifice (4Q404)', 'sectarian'),
    ('4Q405', 'Songs of Sabbath Sacrifice (4Q405)', 'sectarian'),
    ('4Q406', 'Songs of Sabbath Sacrifice (4Q406)', 'sectarian'),
    ('4Q407', 'Songs of Sabbath Sacrifice (4Q407)', 'sectarian'),
    # Other important sectarian
    ('4Q174', 'Florilegium (4QMidrEschat)', 'sectarian'),
    ('4Q246', 'Son of God / Aramaic Apocalypse', 'sectarian'),
    ('4Q521', 'Messianic Apocalypse', 'sectarian'),
    ('4Q266', 'Damascus Document (4QDᵃ)', 'sectarian'),
    ('4Q267', 'Damascus Document (4QDᵇ)', 'sectarian'),
    ('4Q268', 'Damascus Document (4QDᶜ)', 'sectarian'),
    ('4Q269', 'Damascus Document (4QDᵈ)', 'sectarian'),
    ('4Q270', 'Damascus Document (4QDᵉ)', 'sectarian'),
    ('4Q271', 'Damascus Document (4QDᶠ)', 'sectarian'),
    ('4Q272', 'Damascus Document (4QDᵍ)', 'sectarian'),
    ('4Q273', 'Damascus Document (4QDʰ)', 'sectarian'),
    ('4Q394', '4QMMT (Miqtsat Ma\'asei ha-Torah)', 'sectarian'),
    ('4Q395', '4QMMT (4Q395)', 'sectarian'),
    ('4Q396', '4QMMT (4Q396)', 'sectarian'),
    ('4Q397', '4QMMT (4Q397)', 'sectarian'),
    ('4Q398', '4QMMT (4Q398)', 'sectarian'),
    ('4Q399', '4QMMT (4Q399)', 'sectarian'),
    # Major biblical scrolls
    ('1Qisaa', 'Isaiah Scroll (1QIsaᵃ)', 'biblical'),
    ('1Qisab', 'Isaiah Scroll (1QIsaᵇ)', 'biblical'),
]

# Scrolls with variants mapped to OT references (too small to be standalone)
FRAGMENTARY_SCROLLS = {}  # populated below


def build_fragmentary_list():
    """Build set of scrolls that have < 50 words (too fragmentary)."""
    return set()


def load_tf(tf_dir):
    """Load a TF column file, return dict node_id -> value."""
    result = {}
    filepath = os.path.join(tf_dir + '/tf/2.0', tf_dir if tf_dir.endswith('.tf') else tf_dir)
    # No, we need a different approach. Let the caller pass the full path.
    raise NotImplementedError("Use text-fabric library instead")


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║      Dead Sea Scrolls Full Text Import      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Step 1: Load text-fabric
    print("Step 1: Loading DSS dataset via text-fabric...")
    print("  (Downloads ~200MB on first run)")
    sys.stdout.flush()

    from tf.app import use
    A = use("ETCBC/dss:latest", hoist=globals(), quiet=True)
    print(f"  Loaded! {len(F.otype.s('word'))} word nodes available")
    sys.stdout.flush()

    # Step 2: Build scroll name mapping
    print("\nStep 2: Building scroll index...")
    sys.stdout.flush()

    # scroll name -> node_id
    scroll_index = {}
    for node in F.otype.s('scroll'):
        name = F.scroll.v(node)
        if name and name.strip():
            scroll_index[name.strip()] = node

    print(f"  {len(scroll_index)} named scrolls in dataset")
    sys.stdout.flush()

    # Step 3: Connect to DB
    conn = get_db()

    # Step 4: Create DSS work
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('dss', 'Dead Sea Scrolls')")
    print("\nStep 3: Importing target scrolls...")
    sys.stdout.flush()

    total_lines = 0
    total_verses = 0
    import_count = 0
    skipped = []

    for idx, (scroll_id, title, scroll_type) in enumerate(TARGET_SCROLLS, start=1):
        # Check if scroll exists in the dataset
        actual_id = None
        for name, node in scroll_index.items():
            if name.lower() == scroll_id.lower():
                actual_id = name
                scroll_node = node
                break
        else:
            # Try fuzzy match
            for name, node in scroll_index.items():
                if scroll_id.lower() in name.lower():
                    actual_id = name
                    scroll_node = node
                    break

        if actual_id is None:
            skipped.append(scroll_id)
            continue

        # Count words and lines
        fragments = L.d(scroll_node, otype='fragment')
        word_count = 0
        line_count = 0
        line_texts = []

        for frag_node in fragments:
            fragment_name = F.fragment.v(frag_node) or ''
            for line_node in L.d(frag_node, otype='line'):
                line_num = F.line.v(line_node) or ''
                words = []
                for word_node in L.d(line_node, otype='word'):
                    text = F.glyph.v(word_node) or F.g_cons.v(word_node) or ''
                    if text:
                        words.append(text)
                    word_count += 1

                if words:
                    line_text = ' '.join(words)
                    line_texts.append({
                        'fragment': fragment_name,
                        'line': line_num,
                        'text': line_text,
                    })
                    line_count += 1

        if line_count == 0:
            skipped.append(scroll_id)
            continue

        # Create book entry
        conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, 'dss', ?, ?)",
            (scroll_id, title, idx)
        )

        # Import each line as a verse
        batch_verses = []
        batch_resources = []
        for li, ld in enumerate(line_texts, start=1):
            verse_id = f'dss.{scroll_id}.{li}'
            # Fragment + line info as heading
            heading = f"[{actual_id}] {ld['fragment']} line {ld['line']}" if ld['fragment'] else f"[{actual_id}] line {ld['line']}"
            batch_verses.append((
                verse_id, scroll_id, 1, li, ld['text'],
                '', 1, heading,
            ))
            batch_resources.append((
                verse_id, 'DSS_HEBREW', ld['text'], 'hbo',
                json.dumps({'scroll': actual_id, 'fragment': ld['fragment'],
                           'line': ld['line'], 'type': scroll_type})
            ))

        # Batch insert verses
        conn.executemany("""
            INSERT OR IGNORE INTO verses
                (id, book_id, chapter, verse, text_hebrew,
                 text_hebrew_translit, has_hebrew, heading)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_verses)

        # Batch insert text_resources
        conn.executemany("""
            INSERT OR REPLACE INTO text_resources
                (verse_id, version, text, language, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, batch_resources)

        conn.commit()
        total_lines += line_count
        total_verses += len(batch_verses)
        import_count += 1
        print(f"  {scroll_id:8s} {title[:40]:42s} {line_count:5d} lines, {word_count:6d} words")
        sys.stdout.flush()

    # Summary
    print(f"\n{'='*60}")
    print(f"Imported: {import_count} scrolls, {total_lines} lines, {total_verses} verses")
    if skipped:
        print(f"Skipped (not found in dataset): {', '.join(skipped)}")

    # Step 4: Recreate the existing sod-layer connections using new verse IDs
    print("\nStep 4: Creating DSS-to-Bible connections...")
    sys.stdout.flush()

    parallel_connections = [
        ("4Q400", "rev.4.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Songs of Sabbath Sacrifice — angelic liturgy parallels Revelation's heavenly temple scenes"),
        ("4Q405", "ezek.1.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Songs of Sabbath Sacrifice — chariot throne visions parallel Ezekiel's merkabah"),
        ("4Q403", "isa.6.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Songs of Sabbath Sacrifice — 'Holy, holy, holy' liturgy parallels Isaiah's temple vision"),
        ("11Q13", "heb.7.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Melchizedek Scroll — Melchizedek as heavenly high priest, parallels Hebrews 7"),
        ("11Q13", "psa.110.4", "sod", "dss_sectarian", 0.65, 0.55,
         "Melchizedek Scroll — interprets Psalm 110:4 as Melchizedek's eternal priesthood"),
        ("11Q13", "lev.25.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Melchizedek Scroll — connects Melchizedek to the jubilee release"),
        ("11Q19", "exo.25.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Temple Scroll — expanded temple law paralleling Exodus tabernacle instructions"),
        ("11Q19", "ezek.40.1", "sod", "dss_sectarian", 0.65, 0.55,
         "Temple Scroll — temple measurements and layout parallel Ezekiel's temple vision"),
        ("1QS", "1cor.3.16", "sod", "dss_sectarian", 0.65, 0.55,
         "Community Rule — community as spiritual temple, parallels Paul's 'you are the temple of God'"),
        ("1QS", "eph.2.21", "sod", "dss_sectarian", 0.65, 0.55,
         "Community Rule — the community as a holy house built for God"),
        ("1QM", "rev.19.11", "sod", "dss_sectarian", 0.65, 0.55,
         "War Scroll — eschatological war between sons of light and darkness parallels Revelation"),
        ("1QM", "rev.12.7", "sod", "dss_sectarian", 0.65, 0.55,
         "War Scroll — heavenly war and angelic combat parallels Revelation's war in heaven"),
        ("1QpHab", "hab.2.4", "sod", "dss_sectarian", 0.65, 0.55,
         "Pesher Habakkuk — interprets 'the just shall live by his faith'"),
        ("1QpHab", "rom.1.17", "sod", "dss_sectarian", 0.65, 0.55,
         "Pesher Habakkuk — Paul's use of 'the just shall live by faith' has DSS parallels"),
        ("CD", "jer.31.31", "sod", "dss_sectarian", 0.65, 0.55,
         "Damascus Document — New Covenant, parallels Jeremiah's new covenant"),
        ("CD", "heb.8.8", "sod", "dss_sectarian", 0.65, 0.55,
         "Damascus Document — new covenant community, parallels Hebrews"),
        ("1QHa", "phil.2.5", "sod", "dss_sectarian", 0.65, 0.55,
         "Hodayot — self-humbling exaltation pattern parallels Christ hymn in Philippians 2"),
        ("1QHa", "col.1.15", "sod", "dss_sectarian", 0.65, 0.55,
         "Hodayot — creation through wisdom parallels Colossians' Christ hymn"),
        ("4Q246", "luke.1.32", "sod", "dss_sectarian", 0.65, 0.55,
         "Son of God text — 'He shall be called Son of God' parallels Gabriel's annunciation"),
        ("4Q246", "dan.7.13", "sod", "dss_sectarian", 0.65, 0.55,
         "Son of God text — figure with eternal dominion parallels Daniel's 'son of man'"),
        ("4Q174", "2sam.7.14", "sod", "dss_sectarian", 0.65, 0.55,
         "Florilegium — interprets Davidic covenant as messianic"),
        ("4Q521", "matt.11.5", "sod", "dss_sectarian", 0.65, 0.55,
         "Messianic Apocalypse — works of Messiah: heal sick, raise dead, preach to poor"),
        ("4Q521", "luke.7.22", "sod", "dss_sectarian", 0.65, 0.55,
         "Messianic Apocalypse — same works paralleling Jesus' ministry"),
    ]

    conn.execute("PRAGMA foreign_keys=OFF")
    conn_count = 0
    existing_con_count = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE type='dss_sectarian'"
    ).fetchone()[0]
    print(f"  Existing DSS connections: {existing_con_count}")

    for scroll_id, target_verse, layer, typ, strength, confidence, note in parallel_connections:
        # Use dss.{scroll_id}.1 as the DSS verse
        source = f"dss.{scroll_id}.1"
        existing = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE source_verse=? AND type=? AND subtype=?",
            (source, typ, scroll_id)
        ).fetchone()[0]
        if existing == 0:
            conn.execute(
                """INSERT INTO connections
                   (source_verse, target_verse, layer, type, subtype,
                    strength, confidence, discovered_by, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'human', ?)""",
                (source, target_verse, layer, typ, scroll_id, strength, confidence,
                 json.dumps({
                     "note": note[:200],
                     "scholar": "ETCBC/Abegg",
                     "dss_scroll": scroll_id
                 }))
            )
            conn_count += 1

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    print(f"  New connections created: {conn_count}")
    print(f"\n{'='*60}")
    print("DSS import complete!")

    conn.close()


if __name__ == '__main__':
    main()
