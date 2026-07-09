#!/usr/bin/env python3
"""
Wiki Article Generator — creates comprehensive wiki articles from the DB.

Generates Markdown files for every entity, book, work, and connection layer
in the knowledge graph. Optionally enriches with online sources.

Usage:
    python3 generators/generate_wiki_articles.py                    # All entities
    python3 generators/generate_wiki_articles.py --entity jesus     # Single entity
    python3 generators/generate_wiki_articles.py --book gen         # Single book
    python3 generators/generate_wiki_articles.py --all              # Everything
    python3 generators/generate_wiki_articles.py --enrich           # + Wikipedia/Wikidata
"""

import sqlite3
import json
import os
import sys
import re
import urllib.request
import urllib.parse
import time
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "scripture.db"
WIKI_DIR = PROJECT_ROOT / "knowledge" / "wiki"
ENTITIES_DIR = WIKI_DIR / "entities"
BOOKS_DIR = WIKI_DIR / "books"
WORKS_DIR = WIKI_DIR / "works"
LAYERS_DIR = WIKI_DIR / "layers"

# Wikidata SPARQL endpoint
WD_SPARQL = "https://query.wikidata.org/sparql"
# Wikipedia REST API
WP_API = "https://en.wikipedia.org/api/rest_v1/page/summary"

# Cache for online lookups
_cache = {}

# Entity type to emoji/icon mapping for visual distinction
ENTITY_ICONS = {
    "person": "👤",
    "place": "📍",
    "concept": "💡",
    "title": "👑",
    "being": "✨",
    "event": "📅",
    "object": "📜",
}

LAYER_DESCRIPTIONS = {
    "linguistic": "Word-level language connections — same Hebrew/Greek lemma, root, morphology, wordplay, or cognate across passages",
    "numerical": "Gematria and isopsephy connections — verses linked by matching numerical values of their words",
    "structural": "Literary structures — chiasms, parallelisms, inclusios, refrains, acrostics, and formula markers",
    "intertextual": "How texts quote, allude to, or echo other texts — direct quotations, allusions, type-antitype patterns",
    "textual": "Textual variants and manuscript traditions — differences between the MT, LXX, DSS, Vulgate, JST, and other versions",
    "geographic": "Geographical and spatial connections — same location, journey paths, wilderness, temple mountain, exile routes",
    "chronological": "Temporal connections — same time period, genealogical links, prophetic timelines, feast cycles, dispensations",
    "interpretive": "How the text has been interpreted across traditions — rabbinic, patristic, reformation, restoration, critical scholarship",
    "frequency": "Word occurrence patterns — distribution counts, hapax legomenon, repeated formulaic numbers (7, 10, 12, 40)",
    "symbolic": "Shared symbols, apocalyptic vocabulary, and typology — conceptual connections across the canon",
    "sod": "Sod (Hidden/Temple) — deep mystical, temple-theology, ascent, and hidden connections known as 'the inner meaning'",
}

LAYER_EXAMPLES = {
    "linguistic": "Genesis 1:1 and John 1:1 share 'beginning' (בראשית / ἀρχῇ) — same semantic domain",
    "numerical": "The gematria of 'Elohim' (אלהים = 86) connects to other verses where 86 appears",
    "structural": "Alma 36 forms a perfect chiastic structure: A-B-C-D-C'-B'-A'",
    "intertextual": "Matthew 2:15 quotes Hosea 11:1 — 'Out of Egypt I called my son'",
    "textual": "Isaiah 53 in the Great Isaiah Scroll (1QIsaᵃ) differs from the Masoretic Text in several places",
    "geographic": "The wilderness of Judea connects John the Baptist, Jesus' temptation, and the Qumran community",
    "chronological": "The 70-weeks prophecy of Daniel 9 connects to the time of Jesus' ministry",
    "interpretive": "The Suffering Servant in Isaiah 53 — Jewish tradition reads it as Israel, Christian tradition reads it as Jesus",
    "frequency": "The word 'covenant' (ברית) appears 13 times in Genesis, 25 times in Deuteronomy",
    "symbolic": "The Lamb of God symbol connects Genesis 22, Exodus 12, Isaiah 53, and Revelation 5",
    "sod": "The temple veil being rent at Jesus' death (Matthew 27:51) connects to the Holy of Holies symbolism in Exodus 26",
}


def get_conn():
    """Get a database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def make_slug(text):
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().replace(" ", "_").replace("(", "").replace(")", "")
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug


def query_wikidata(entity_name, entity_type, entity_id=None):
    """Query Wikidata for entity information."""
    # Build SPARQL based on entity type
    # Known Wikidata QIDs for specific biblical entities
    KNOWN_QIDS = {
        "jesus": "Q302",      # Jesus Christ
        "christ": "Q302",     # Jesus Christ
        "moses": "Q9077",     # Moses
        "abraham": "Q9181",   # Abraham (biblical figure)
        "david": "Q41330",    # David (biblical figure)
        "adam": "Q70899",     # Adam (biblical figure)
        "noah": "Q81482",     # Noah (biblical figure)
        "isaiah": "Q188229",  # Isaiah (biblical prophet)
        "jeremiah": "Q201909",# Jeremiah (biblical figure)
        "ezekiel": "Q180329", # Ezekiel (biblical figure)
        "daniel": "Q216635",  # Daniel (biblical figure)
        "paul": "Q9260",      # Paul the Apostle
        "peter": "Q33903",    # Peter (biblical figure)
        "john_baptist": "Q40662", # John the Baptist
        "mary": "Q3958763",   # Mary, mother of Jesus
        "joseph": "Q40822",   # Joseph (biblical figure, son of Jacob)
        "jacob": "Q40822",    # Jacob (biblical figure)
        "isaac": "Q194184",   # Isaac (biblical figure)
        "solomon": "Q37045",  # Solomon (biblical figure)
        "jerusalem": "Q491955",# Jerusalem (the ancient city)
        "zion": "Q232185",    # Zion (the biblical hill/concept)
        "egypt": "Q79",       # Egypt (the country)
        "babylon": "Q320209", # Babylon (the ancient city)
        "sinai": "Q38797",    # Mount Sinai
    }

    if entity_id in KNOWN_QIDS:
        qid = KNOWN_QIDS[entity_id]
        query = f"""
        SELECT ?item ?itemLabel ?description ?birthDate ?deathDate ?fatherLabel ?motherLabel ?spouseLabel ?image ?coords
        WHERE {{
            BIND(wd:{qid} AS ?item)
            ?item rdfs:label ?itemLabel . FILTER(LANG(?itemLabel) = "en")
            OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?item wdt:P569 ?birthDate . }}
            OPTIONAL {{ ?item wdt:P570 ?deathDate . }}
            OPTIONAL {{ ?item wdt:P22 ?father . }}
            OPTIONAL {{ ?item wdt:P25 ?mother . }}
            OPTIONAL {{ ?item wdt:P26 ?spouse . }}
            OPTIONAL {{ ?item wdt:P18 ?image . }}
            OPTIONAL {{ ?item wdt:P625 ?coords . }}
        }}
        """
    elif entity_type in ("person", "title", "being"):
        query = f"""
        SELECT ?item ?itemLabel ?description ?birthDate ?deathDate ?fatherLabel ?motherLabel ?spouseLabel ?image
        WHERE {{
            ?item rdfs:label "{entity_name}"@en .
            ?item wdt:P31 wd:Q5 .
            OPTIONAL {{ ?item wdt:P140 wd:Q5043 . }}
            OPTIONAL {{ ?item wdt:P140 wd:Q9263 . }}
            OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?item wdt:P569 ?birthDate . }}
            OPTIONAL {{ ?item wdt:P570 ?deathDate . }}
            OPTIONAL {{ ?item wdt:P22 ?father . }}
            OPTIONAL {{ ?item wdt:P25 ?mother . }}
            OPTIONAL {{ ?item wdt:P26 ?spouse . }}
            OPTIONAL {{ ?item wdt:P18 ?image . }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        ORDER BY DESC(?item)
        LIMIT 3
        """
    elif entity_type == "place":
        query = f"""
        SELECT ?item ?itemLabel ?description ?coords ?image
        WHERE {{
            ?item rdfs:label "{entity_name}"@en .
            ?item wdt:P31 wd:Q27096213 .
            OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?item wdt:P625 ?coords . }}
            OPTIONAL {{ ?item wdt:P18 ?image . }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 1
        """
    else:
        query = f"""
        SELECT ?item ?itemLabel ?description ?image
        WHERE {{
            ?item rdfs:label "{entity_name}"@en .
            OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?item wdt:P18 ?image . }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 1
        """

    url = f"{WD_SPARQL}?format=json&query={urllib.parse.quote(query)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ScriptureEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("results", {}).get("bindings", [])
            if results:
                bindings = results[0]
                info = {}
                if "description" in bindings:
                    info["summary"] = bindings["description"]["value"]
                if "birthDate" in bindings:
                    info["birth_date"] = bindings["birthDate"]["value"]
                if "deathDate" in bindings:
                    info["death_date"] = bindings["deathDate"]["value"]
                if "fatherLabel" in bindings:
                    info["father"] = bindings["fatherLabel"]["value"]
                if "motherLabel" in bindings:
                    info["mother"] = bindings["motherLabel"]["value"]
                if "spouseLabel" in bindings:
                    info["spouse"] = bindings["spouseLabel"]["value"]
                if "image" in bindings:
                    info["image"] = bindings["image"]["value"]
                if "coords" in bindings:
                    info["coordinates"] = bindings["coords"]["value"]
                return info
    except Exception:
        pass
    return None


def fetch_wikipedia_summary(entity_name):
    """Fetch a clean summary from Wikipedia REST API."""
    cache_key = f"wp:{entity_name}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        url = f"{WP_API}/{urllib.parse.quote(entity_name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "ScriptureEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            summary = data.get("extract", "")
            _cache[cache_key] = summary[:500] if summary else None
            return _cache[cache_key]
    except Exception:
        _cache[cache_key] = None
        return None


def generate_entity_article(conn, entity_id, enrich=False):
    """Generate a wiki article for a single entity."""
    # Get entity info
    row = conn.execute(
        "SELECT * FROM entity_links WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    if not row:
        print(f"  Entity not found: {entity_id}")
        return None

    entity = dict(row)
    name = entity["english_name"] or entity_id
    slug = make_slug(name)
    ent_type = entity["entity_type"]

    # Get all verses mentioning this entity
    verses = conn.execute(
        """
        SELECT ve.verse_id, ve.relationship_type, ve.confidence,
               v.text_english, b.title as book_title, v.chapter, v.verse
        FROM verse_entities ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE ve.entity_id = ?
        ORDER BY b.position, v.chapter, v.verse
        LIMIT 200
    """,
        (entity_id,),
    ).fetchall()

    if not verses:
        print(f"  No verses for {entity_id}, skipping")
        return None

    verse_list = [dict(v) for v in verses]

    # Get connections involving these verses (cross-connections)
    verse_ids = [v["verse_id"] for v in verse_list[:50]]  # cap for performance
    placeholders = ",".join("?" for _ in verse_ids)

    intra_connections = []
    if verse_ids:
        conns = conn.execute(
            f"""
            SELECT c.source_verse, c.target_verse, c.layer, c.type, c.strength
            FROM connections c
            WHERE (c.source_verse IN ({placeholders}) AND c.target_verse IN ({placeholders}))
            AND c.source_verse != c.target_verse
            ORDER BY c.strength DESC
            LIMIT 30
        """,
            verse_ids + verse_ids,
        ).fetchall()
        intra_connections = [dict(c) for c in conns]

    # Get related entities (co-occurring in same verses)
    related = conn.execute(
        f"""
        SELECT el.entity_id, el.english_name, el.entity_type, COUNT(*) as co_count
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        WHERE ve.verse_id IN ({placeholders})
        AND ve.entity_id != ?
        AND ve.confidence >= 0.3
        GROUP BY el.entity_id
        ORDER BY co_count DESC
        LIMIT 20
    """,
        verse_ids + [entity_id],
    ).fetchall()
    related_list = [dict(r) for r in related]

    # Get works distribution
    works_dist = conn.execute(
        f"""
        SELECT w.title, COUNT(*) as c
        FROM verse_entities ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        JOIN works w ON w.id = b.work_id
        WHERE ve.entity_id = ?
        GROUP BY w.id
        ORDER BY c DESC
    """,
        (entity_id,),
    ).fetchall()

    # ——— Build Article ———
    lines = []
    icon = ENTITY_ICONS.get(ent_type, "📖")

    # Title
    lines.append(f"# {icon} {name}\n")

    # Metadata line
    meta_parts = []
    if entity.get("hebrew_name"):
        meta_parts.append(f"**Hebrew**: {entity['hebrew_name']}")
    if entity.get("hebrew_strongs"):
        meta_parts.append(f"**Strong's**: {entity['hebrew_strongs']}")
    if entity.get("greek_name"):
        meta_parts.append(f"**Greek**: {entity['greek_name']}")
    if entity.get("greek_strongs"):
        meta_parts.append(f"**Strong's**: {entity['greek_strongs']}")
    if meta_parts:
        lines.append(" | ".join(meta_parts))
        lines.append("")

    # Online enrichment
    if enrich:
        wikidata = query_wikidata(name, ent_type, entity_id=entity_id)
        if wikidata:
            if wikidata.get("summary"):
                lines.append(f"_{wikidata['summary']}_\n")
            # Dates
            dates = []
            if wikidata.get("birth_date"):
                dates.append(f"**Born**: {wikidata['birth_date'][:4]}")
            if wikidata.get("death_date"):
                dates.append(f"**Died**: {wikidata['death_date'][:4]}")
            if dates:
                lines.append(" | ".join(dates))
                lines.append("")
            # Family
            family = []
            for rel, label in [("father", "Father"), ("mother", "Mother"), ("spouse", "Spouse")]:
                if wikidata.get(rel):
                    family.append(f"**{label}**: {wikidata[rel]}")
            if family:
                lines.append(" | ".join(family))
                lines.append("")
            # Image
            if wikidata.get("image"):
                img_url = wikidata["image"]
                lines.append(f"![{name}]({img_url})\n")

        # Try Wikipedia summary as fallback
        if not wikidata or not wikidata.get("summary"):
            wp_summary = fetch_wikipedia_summary(name)
            if wp_summary:
                lines.append(f"> {wp_summary}\n")

    # Work distribution
    if works_dist:
        lines.append("## Appears In\n")
        for w in works_dist:
            lines.append(f"- **{w['title']}**: {w['c']} verses")
        lines.append("")

    # Key verses (top 10 by confidence)
    top_verses = sorted(verse_list, key=lambda v: -v["confidence"])[:10]
    lines.append(f"## Key Verses ({len(verse_list)} total)\n")
    for v in top_verses[:10]:
        ref = f"{v['book_title']} {v['chapter']}:{v['verse']}"
        text = (v["text_english"] or "")[:150]
        rel = f" ({v['relationship_type']})" if v["relationship_type"] else ""
        lines.append(f"- **{ref}**{rel}: _{text}_")
    if len(verse_list) > 10:
        lines.append(f"\n*... and {len(verse_list) - 10} more verses*\n")

    # Connections between these verses
    if intra_connections:
        by_layer = defaultdict(list)
        for c in intra_connections:
            by_layer[c["layer"]].append(c)

        lines.append("## Connections\n")
        for layer, conns in by_layer.items():
            desc = LAYER_DESCRIPTIONS.get(layer, layer)
            lines.append(f"### {layer.title()}")
            lines.append(f"_{desc}_\n")
            for c in conns[:8]:
                src_ref = c["source_verse"]
                tgt_ref = c["target_verse"]
                lines.append(f"- **{c['type']}**: [{src_ref}](verse://{src_ref}) → [{tgt_ref}](verse://{tgt_ref})")
            if len(conns) > 8:
                lines.append(f"  *... and {len(conns) - 8} more*\n")
        lines.append("")

    # Related entities
    if related_list:
        lines.append("## Related Entities\n")
        for r in related_list[:10]:
            icon_r = ENTITY_ICONS.get(r["entity_type"], "•")
            lines.append(f"- {icon_r} **{r['english_name']}** ({r['entity_type']}) — co-occurs in {r['co_count']} verses")
        lines.append("")

    # Type tag
    lines.append(f"---\n*Article type: **{ent_type.capitalize()}** | Generated from the Scripture Knowledge Engine*")

    return {
        "entity_id": entity_id,
        "title": name,
        "slug": slug,
        "type": ent_type,
        "content": "\n".join(lines),
        "verse_count": len(verse_list),
    }


def generate_book_article(conn, book_id):
    """Generate a wiki article for a book of scripture."""
    book = conn.execute(
        "SELECT b.*, w.title as work_title FROM books b JOIN works w ON w.id=b.work_id WHERE b.id=?",
        (book_id,),
    ).fetchone()
    if not book:
        return None
    book = dict(book)

    # Count verses
    verse_count = conn.execute(
        "SELECT COUNT(*) as c FROM verses WHERE book_id=?", (book_id,)
    ).fetchone()["c"]

    # Count chapters
    ch_count = conn.execute(
        "SELECT COUNT(DISTINCT chapter) as c FROM verses WHERE book_id=?", (book_id,)
    ).fetchone()["c"]

    # Get connection stats
    conn_stats = conn.execute(
        """
        SELECT c.layer, COUNT(*) as c
        FROM connections c
        WHERE c.source_verse LIKE ?
        GROUP BY c.layer
        ORDER BY c DESC
    """,
        (f"{book_id}.%",),
    ).fetchall()

    # Top entities in this book
    top_entities = conn.execute(
        """
        SELECT el.english_name, el.entity_type, COUNT(*) as c
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        JOIN verses v ON v.id = ve.verse_id
        WHERE v.book_id = ?
        GROUP BY el.entity_id
        ORDER BY c DESC
        LIMIT 15
    """,
        (book_id,),
    ).fetchall()

    # Top connected verses (hubs within this book)
    top_hubs = conn.execute(
        """
        SELECT source_verse, COUNT(*) as c
        FROM connections
        WHERE source_verse LIKE ?
        GROUP BY source_verse
        ORDER BY c DESC
        LIMIT 10
    """,
        (f"{book_id}.%",),
    ).fetchall()

    # Build article
    lines = []
    lines.append(f"# {book['title']}\n")
    lines.append(f"**Work**: {book['work_title']} | **Chapters**: {ch_count} | **Verses**: {verse_count:,}\n")

    if book.get("subtitle"):
        lines.append(f"*{book['subtitle']}*\n")

    # Connection summary
    if conn_stats:
        total_c = sum(r["c"] for r in conn_stats)
        lines.append(f"## Connections ({total_c:,} total)\n")
        lines.append("| Layer | Count |")
        lines.append("|-------|-------|")
        for r in conn_stats:
            lines.append(f"| {r['layer']} | {r['c']:,} |")
        lines.append("")

    # Top entities
    if top_entities:
        lines.append("## Key Entities\n")
        for r in top_entities:
            icon_e = ENTITY_ICONS.get(r["entity_type"], "•")
            lines.append(f"- {icon_e} **{r['english_name']}** ({r['entity_type']}) — mentioned {r['c']} times")
        lines.append("")

    # Most connected verses
    if top_hubs:
        lines.append("## Most Connected Verses\n")
        for r in top_hubs:
            parts = r["source_verse"].split(".")
            ref = f"{book['title']} {parts[-2]}:{parts[-1]}" if len(parts) >= 3 else r["source_verse"]
            lines.append(f"- **{ref}** — {r['c']} connections")
        lines.append("")

    lines.append(f"---\n*Generated from the Scripture Knowledge Engine — {verse_count:,} verses indexed*")

    return {
        "id": book_id,
        "title": book["title"],
        "content": "\n".join(lines),
    }


def generate_work_article(conn, work_id):
    """Generate a wiki article for a work of scripture."""
    work = conn.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
    if not work:
        return None
    work = dict(work)

    # Get books
    books = conn.execute(
        "SELECT * FROM books WHERE work_id=? ORDER BY position", (work_id,)
    ).fetchall()

    # Total verses
    total_v = conn.execute(
        "SELECT COUNT(*) as c FROM verses v JOIN books b ON b.id=v.book_id WHERE b.work_id=?",
        (work_id,),
    ).fetchone()["c"]

    # Total connections
    book_patterns = [f"{b['id']}.%" for b in books]
    total_c = 0
    if book_patterns:
        clauses = " OR ".join(f"source_verse LIKE ?" for _ in books)
        total_c = conn.execute(
            f"SELECT COUNT(*) as c FROM connections WHERE {clauses}",
            book_patterns,
        ).fetchone()["c"]

    # Build article
    lines = []
    lines.append(f"# {work['title']}\n")
    lines.append(f"**Books**: {len(books)} | **Verses**: {total_v:,} | **Connections**: {total_c:,}\n")

    if work.get("subtitle"):
        lines.append(f"*{work['subtitle']}*\n")

    # Book list
    lines.append("## Books\n")
    lines.append("| Book | Chapters | Verses |")
    lines.append("|------|----------|--------|")
    for b in books:
        ch = conn.execute("SELECT COUNT(DISTINCT chapter) FROM verses WHERE book_id=?", (b["id"],)).fetchone()[0]
        vs = conn.execute("SELECT COUNT(*) FROM verses WHERE book_id=?", (b["id"],)).fetchone()[0]
        lines.append(f"| {b['title']} | {ch} | {vs:,} |")
    lines.append("")

    # Top entities
    top_ents = conn.execute(
        f"""
        SELECT el.english_name, el.entity_type, COUNT(*) as c
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE b.work_id = ?
        GROUP BY el.entity_id
        ORDER BY c DESC
        LIMIT 20
    """,
        (work_id,),
    ).fetchall()
    if top_ents:
        lines.append("## Key Entities\n")
        for r in top_ents:
            icon_e = ENTITY_ICONS.get(r["entity_type"], "•")
            lines.append(f"- {icon_e} **{r['english_name']}** — {r['c']} mentions")
        lines.append("")

    lines.append(f"---\n*Generated from the Scripture Knowledge Engine*")
    return {
        "id": work_id,
        "title": work["title"],
        "content": "\n".join(lines),
    }


def generate_layer_article(layer_name):
    """Generate a wiki article for a connection layer."""
    desc = LAYER_DESCRIPTIONS.get(layer_name, "")
    example = LAYER_EXAMPLES.get(layer_name, "")

    lines = []
    lines.append(f"# {layer_name.title()} Layer\n")
    lines.append(f"_{desc}_\n")
    lines.append(f"> **Example**: {example}\n")

    lines.append("## Purpose\n")
    purpose = {
        "linguistic": "The Linguistic layer tracks word-level connections between passages — same Hebrew roots, Greek lemmas, wordplay, cognates, and semantic domains. This is the most granular layer, operating at the word level rather than the concept level.",
        "numerical": "The Numerical layer connects verses through gematria (Hebrew) and isopsephy (Greek) — when words or phrases share numerical values, suggesting intentional numerical design.",
        "structural": "The Structural layer identifies literary patterns within and between passages — chiasms, parallelisms, inclusios, refrains, acrostics, and formula markers like 'And it came to pass'.",
        "intertextual": "The Intertextual layer tracks how later texts quote, allude to, or echo earlier texts — from verbatim quotations to subtle linguistic echoes spanning centuries.",
        "textual": "The Textual layer documents differences between manuscript traditions — where the Masoretic Text, Septuagint, Dead Sea Scrolls, Vulgate, and other versions diverge.",
        "geographic": "The Geographic layer connects passages by location — same places, journey routes, wilderness experiences, mountain-of-God encounters, and exile paths.",
        "chronological": "The Chronological layer links events by time — same periods, genealogical connections, prophetic timeline fulfillments, sabbatical and jubilee cycles.",
        "interpretive": "The Interpretive layer tracks how different traditions have read the same texts — from rabbinic midrash and patristic exegesis to Gileadi's structural observations and Latter-day Saint readings.",
        "frequency": "The Frequency layer analyzes word occurrence patterns — how often words appear, where they cluster, hapax legomena (words appearing once), and numerical patterns in word counts.",
        "symbolic": "The Symbolic layer connects passages through shared symbols and typology — the Lamb, the Throne, the Temple, apocalyptic imagery, and person/event/object types.",
        "sod": "The Sod layer (from PaRDeS, meaning 'hidden' or 'secret') contains deep temple-theology, mystical ascent, and hidden connections — the inner meaning accessible through prayerful study.",
    }
    lines.append(purpose.get(layer_name, "") + "\n")

    # Get types from the types module
    try:
        from lib.connections.types import LAYERS
        if layer_name in LAYERS:
            types = LAYERS[layer_name]["types"]
            lines.append(f"## Types ({len(types)})\n")
            for t in types:
                lines.append(f"- `{t}`")
            lines.append("")
    except ImportError:
        pass

    lines.append("---\n*One of 11 connection layers in the Scripture Knowledge Engine*")
    return {
        "id": layer_name,
        "title": layer_name.title(),
        "content": "\n".join(lines),
    }


def write_article(article, subdir):
    """Write an article Markdown file."""
    if not article:
        return False
    path = subdir / f"{article['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(article["content"])
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate wiki articles from the Scripture Knowledge Engine")
    parser.add_argument("--entity", type=str, help="Generate article for a specific entity ID")
    parser.add_argument("--book", type=str, help="Generate article for a specific book ID")
    parser.add_argument("--all-entities", action="store_true", help="Generate articles for all entities")
    parser.add_argument("--all-books", action="store_true", help="Generate articles for all books")
    parser.add_argument("--all-works", action="store_true", help="Generate articles for all works")
    parser.add_argument("--all-layers", action="store_true", help="Generate articles for all connection layers")
    parser.add_argument("--all", action="store_true", help="Generate everything")
    parser.add_argument("--enrich", action="store_true", help="Enrich with Wikipedia/Wikidata")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of articles generated")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Run scripts/setup.sh or download from GitHub Releases")
        sys.exit(1)

    conn = get_conn()
    count = 0
    limit = args.limit or 999999

    # Create directories
    for d in [ENTITIES_DIR, BOOKS_DIR, WORKS_DIR, LAYERS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # ─── Single Entity ───
    if args.entity:
        article = generate_entity_article(conn, args.entity, enrich=args.enrich)
        if article:
            write_article({"id": article["slug"], **article}, ENTITIES_DIR)
            print(f"  ✓ {article['title']} ({article['verse_count']} verses)")
            count += 1

    # ─── All Entities ───
    if args.all_entities or args.all:
        entities = conn.execute(
            "SELECT entity_id, english_name, entity_type FROM entity_links ORDER BY entity_type, english_name"
        ).fetchall()
        print(f"\nGenerating {len(entities)} entity articles...\n")
        for row in entities:
            if count >= limit:
                break
            eid = row["entity_id"]
            article = generate_entity_article(conn, eid, enrich=args.enrich)
            if article:
                write_article({"id": article["slug"], **article}, ENTITIES_DIR)
                print(f"  ✓ {article['title']} ({article['verse_count']} verses)")
                count += 1
            time.sleep(0.1)  # Rate limit for online queries
        print(f"\nEntity articles generated: {count}")

    # ─── Single Book ───
    if args.book:
        article = generate_book_article(conn, args.book)
        if article:
            write_article({"id": args.book, **article}, BOOKS_DIR)
            print(f"  ✓ Book: {article['title']}")
            count += 1

    # ─── All Books ───
    if args.all_books or args.all:
        books = conn.execute("SELECT id, title FROM books ORDER BY position").fetchall()
        print(f"\nGenerating {len(books)} book articles...\n")
        for row in books:
            if count >= limit + 9999:  # separate counter for books
                break
            article = generate_book_article(conn, row["id"])
            if article:
                write_article({"id": row["id"], **article}, BOOKS_DIR)
                print(f"  ✓ Book: {article['title']}")
        print()

    # ─── All Works ───
    if args.all_works or args.all:
        works = conn.execute("SELECT id, title FROM works ORDER BY id").fetchall()
        print(f"Generating {len(works)} work overview pages...\n")
        for row in works:
            article = generate_work_article(conn, row["id"])
            if article:
                write_article({"id": row["id"], **article}, WORKS_DIR)
                print(f"  ✓ Work: {article['title']}")
        print()

    # ─── All Layers ───
    if args.all_layers or args.all:
        print(f"Generating {len(LAYER_DESCRIPTIONS)} layer explainer pages...\n")
        for layer_name in sorted(LAYER_DESCRIPTIONS.keys()):
            article = generate_layer_article(layer_name)
            if article:
                write_article({"id": layer_name, **article}, LAYERS_DIR)
                print(f"  ✓ Layer: {layer_name}")
        print()

    conn.close()
    print(f"Done. Generated {count} wiki articles in {WIKI_DIR}")


if __name__ == "__main__":
    main()
