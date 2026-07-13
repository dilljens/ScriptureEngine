#!/usr/bin/env python3
"""Ingest official LDS footnotes from the churchofjesuschrist.org API.

Fetches each chapter's verse text with word-level footnote markers,
parses the structured footnote data, and stores it in the database.

Usage:
  python3 scripts/ingest_footnotes.py              # Ingest all chapters
  python3 scripts/ingest_footnotes.py --books isa  # Ingest specific book(s)
  python3 scripts/ingest_footnotes.py --chapters isa.55,isa.6  # Specific chapters

Uses concurrent requests for speed.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import contextlib

from lib.db import get_db

API_BASE = "https://www.churchofjesuschrist.org/study/api/v3/language-pages/type/content?lang=eng&uri=/scriptures"

# Map book IDs to API volume paths
VOLUME_MAP = {
    # OT
    'gen': 'ot', 'exo': 'ot', 'lev': 'ot', 'num': 'ot', 'deu': 'ot',
    'josh': 'ot', 'judg': 'ot', 'ruth': 'ot',
    '1sam': 'ot', '2sam': 'ot', '1kgs': 'ot', '2kgs': 'ot',
    '1chr': 'ot', '2chr': 'ot',
    'ezra': 'ot', 'neh': 'ot', 'esth': 'ot',
    'job': 'ot', 'psa': 'ot', 'prov': 'ot', 'eccl': 'ot', 'song': 'ot',
    'isa': 'ot', 'jer': 'ot', 'lam': 'ot', 'ezek': 'ot', 'dan': 'ot',
    'hos': 'ot', 'joel': 'ot', 'amos': 'ot', 'obad': 'ot', 'jonah': 'ot',
    'mic': 'ot', 'nah': 'ot', 'hab': 'ot', 'zeph': 'ot', 'hag': 'ot',
    'zech': 'ot', 'mal': 'ot',
    # NT
    'matt': 'nt', 'mark': 'nt', 'luke': 'nt', 'john': 'nt',
    'acts': 'nt', 'rom': 'nt',
    '1cor': 'nt', '2cor': 'nt', 'gal': 'nt', 'eph': 'nt',
    'phil': 'nt', 'col': 'nt',
    '1thes': 'nt', '2thes': 'nt', '1tim': 'nt', '2tim': 'nt',
    'titus': 'nt', 'philem': 'nt', 'heb': 'nt',
    'james': 'nt', '1pet': 'nt', '2pet': 'nt',
    '1john': 'nt', '2john': 'nt', '3john': 'nt', 'jude': 'nt',
    'rev': 'nt',
    # BoM
    '1ne': 'bofm', '2ne': 'bofm', 'jacob': 'bofm', 'enos': 'bofm',
    'jarom': 'bofm', 'omni': 'bofm', 'wom': 'bofm',
    'mosiah': 'bofm', 'alma': 'bofm', 'hel': 'bofm',
    '3ne': 'bofm', '4ne': 'bofm', 'morm': 'bofm', 'ether': 'bofm', 'moro': 'bofm',
    # PGP
    'moses': 'pgp', 'abraham': 'pgp', 'jsm': 'pgp', 'jsh': 'pgp', 'aoff': 'pgp',
}

# D&C has sections, not chapters — handled separately
CHAPTER_COUNTS = {
    'gen':50, 'exo':40, 'lev':27, 'num':36, 'deu':34, 'josh':24, 'judg':21, 'ruth':4,
    '1sam':31, '2sam':24, '1kgs':22, '2kgs':25, '1chr':29, '2chr':36,
    'ezra':10, 'neh':13, 'esth':10, 'job':42, 'psa':150, 'prov':31, 'eccl':12, 'song':8,
    'isa':66, 'jer':52, 'lam':5, 'ezek':48, 'dan':12, 'hos':14, 'joel':3, 'amos':9,
    'obad':1, 'jonah':4, 'mic':7, 'nah':3, 'hab':3, 'zeph':3, 'hag':2, 'zech':14, 'mal':4,
    'matt':28, 'mark':16, 'luke':24, 'john':21, 'acts':28, 'rom':16, '1cor':16,
    '2cor':13, 'gal':6, 'eph':6, 'phil':4, 'col':4, '1thes':5, '2thes':3,
    '1tim':6, '2tim':4, 'titus':3, 'philem':1, 'heb':13, 'james':5, '1pet':5,
    '2pet':3, '1john':5, '2john':1, '3john':1, 'jude':1, 'rev':22,
    '1ne':22, '2ne':33, 'jacob':7, 'enos':1, 'jarom':1, 'omni':1, 'wom':1,
    'mosiah':29, 'alma':63, 'hel':16, '3ne':30, '4ne':1, 'morm':9, 'ether':15, 'moro':10,
    'moses':8, 'abraham':5, 'jsm':1, 'jsh':1, 'aoff':1,
}
# Add D&C sections (dc1 through dc138)
for _i in range(1, 139):
    CHAPTER_COUNTS[f"dc{_i}"] = 1


def _api_book_id(book_id):
    """Convert internal book ID to API book path segment."""
    # D&C: dc76 -> dc-testament/dc/76
    if book_id.startswith('dc'):
        section = book_id[2:]  # "76" from "dc76"
        return f"dc-testament/dc/{section}"
    return f"{VOLUME_MAP.get(book_id, 'ot')}/{book_id}"


def _parse_body_verses(body_html):
    """Parse the HTML body into verse-level text with inline footnote markers.

    Returns:
        list of dicts: [{"verse": int, "html": str, "footnotes": [(word, note_id), ...]}, ...]
    """
    # The body contains <p class="verse" data-aid="..." id="p1">...</p> blocks
    # Find all verse paragraphs
    verse_pattern = re.compile(
        r'<p\s+class="verse"[^>]*id="p(\d+)"[^>]*>(.*?)</p>',
        re.DOTALL
    )
    # Footnote marker pattern: <a class="study-note-ref" href="#noteX_Y"><sup class="marker" data-value="Z"></sup>word</a>
    note_ref_pattern = re.compile(
        r'<a\s+class="study-note-ref"[^>]*href="#(note\d+_[a-z])"[^>]*>'
        r'<sup[^>]*></sup>([^<]+)</a>',
        re.DOTALL
    )

    # For chapter-level text (sometimes the whole body is one block), detect verses differently
    # Some bodies use <p class="verse-number">1</p> followed by the text
    # Let's try the id-based pattern first
    verses = []
    for m in verse_pattern.finditer(body_html):
        verse_num = int(m.group(1))
        verse_html = m.group(2).strip()
        # Find footnote markers within this verse
        footnotes = []
        for fm in note_ref_pattern.finditer(verse_html):
            note_id = fm.group(1)
            word = fm.group(2).strip()
            footnotes.append((word, note_id))
        # Clean HTML for text
        text = re.sub(r'<[^>]+>', ' ', verse_html).strip()
        text = re.sub(r'\s+', ' ', text)
        verses.append({
            "verse": verse_num,
            "html": verse_html,
            "text": text,
            "footnotes": footnotes,
        })

    if not verses:
        # Fallback: try to parse from the full body
        # Split by <p class="verse-number">
        parts = re.split(r'<p\s+class="verse-number"[^>]*>\s*(\d+)\s*</p>', body_html)
        if len(parts) >= 3:
            for i in range(1, len(parts), 2):
                verse_num = int(parts[i])
                verse_text = parts[i + 1] if i + 1 < len(parts) else ""
                # Clean tags
                footnotes = []
                for fm in note_ref_pattern.finditer(verse_text):
                    note_id = fm.group(1)
                    word = fm.group(2).strip()
                    footnotes.append((word, note_id))
                text = re.sub(r'<[^>]+>', ' ', verse_text).strip()
                text = re.sub(r'\s+', ' ', text)
                verses.append({
                    "verse": verse_num,
                    "html": verse_text,
                    "text": text,
                    "footnotes": footnotes,
                })

    return verses


def _parse_footnotes(footnotes_dict):
    """Parse the footnotes dictionary from the API response.

    Returns:
        dict: note_id -> {category, body_html, references}
    """
    result = {}
    for note_id, fn in footnotes_dict.items():
        body = fn.get("text", "")
        category = None
        references = []

        # Extract category from data-note-category attribute
        cat_m = re.search(r'data-note-category="([^"]+)"', body)
        if cat_m:
            category = cat_m.group(1)

        # Extract scripture references
        for ref in fn.get("referenceUris", []):
            ref_type = ref.get("type", "")
            ref_href = ref.get("href", "")
            ref_text = ref.get("text", "")
            if ref_type == "scripture-ref":
                references.append({"type": "scripture", "href": ref_href, "text": ref_text})
            else:
                references.append({"type": ref_type, "href": ref_href, "text": ref_text})

        # Also try to parse scripture refs from inline links
        for a_m in re.finditer(r'<a\s+class="scripture-ref"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', body):
            href = a_m.group(1)
            text = a_m.group(2).strip()
            if not any(r["href"] == href for r in references):
                references.append({"type": "scripture", "href": href, "text": text})

        result[note_id] = {
            "category": category or "unknown",
            "body_html": body,
            "context": fn.get("context", ""),
            "references": references,
        }

    return result


def fetch_chapter(book_id, chapter):
    """Fetch a chapter's footnote data from the Church API.

    Returns:
        dict with 'verses' and 'footnotes' keys, or None on error.
    """
    api_book = _api_book_id(book_id)
    # D&C: section is in the book ID, no need to append chapter
    if book_id.startswith('dc'):
        url = f"{API_BASE}/{api_book}"
    else:
        url = f"{API_BASE}/{api_book}/{chapter}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "ScriptureExplorer/1.0 (research project)",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print(f"  [ERROR] {book_id} {chapter}: {e}")
        return None

    content = data.get("content", {})
    body = content.get("body", "")
    raw_footnotes = content.get("footnotes", {})
    meta = data.get("meta", {})

    if not body and not raw_footnotes:
        print(f"  [WARN] {book_id} {chapter}: empty response")
        return None

    verses = _parse_body_verses(body)
    footnotes = _parse_footnotes(raw_footnotes)

    return {
        "verses": verses,
        "footnotes": footnotes,
        "title": meta.get("title", ""),
        "chapter": chapter,
    }


def store_footnotes(conn, book_id, chapter, result):
    """Store parsed footnote data in the database."""
    if not result:
        return 0

    count = 0
    # For D&C, the chapter is the section number (from book_id), not the parameter
    if book_id.startswith('dc'):
        dc_section = book_id[2:]
        verse_id_prefix = f"{book_id}.{dc_section}."
    else:
        verse_id_prefix = f"{book_id}.{chapter}."

    for v in result["verses"]:
        verse_ref = f"{verse_id_prefix}{v['verse']}"

        # Build word index for the verse
        words = v["text"].split()
        word_index_map = {}
        for i, w in enumerate(words):
            # Clean word for matching
            clean = w.strip(".,;:!?()\"'-").lower()
            word_index_map[clean] = i

        for context_word, note_id in v["footnotes"]:
            fn_data = result["footnotes"].get(note_id, {})
            category = fn_data.get("category", "unknown")
            body_html = fn_data.get("body_html", "")
            references = fn_data.get("references", [])

            # Find word index
            clean_word = context_word.strip(".,;:!?()\"'-").lower()
            word_idx = word_index_map.get(clean_word)

            # Insert footnote
            fn_id = f"{verse_ref}_{note_id.split('_')[1]}"
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO footnotes
                        (id, verse_id, marker, word_index, context_word, category, body_html, reference_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fn_id, verse_ref, note_id, word_idx, context_word,
                    category, body_html, json.dumps(references),
                ))
                count += 1
            except Exception as e:
                print(f"  [DB] Error inserting footnote {fn_id}: {e}")

            # Resolve scripture cross-references
            for ref in references:
                if ref.get("type") == "scripture":
                    target = _resolve_scripture_ref(ref.get("href", ""))
                    if target:
                        with contextlib.suppress(Exception):
                            conn.execute("""
                                INSERT OR IGNORE INTO cross_references
                                    (source_verse, target_verse, footnote_id, confidence)
                                VALUES (?, ?, ?, ?)
                            """, (verse_ref, target, fn_id, 1.0))

    return count


REF_PATTERN = re.compile(
    r'/study/scriptures/([^/]+)/([^/]+?)/([^/?#]+)'
)
SUB_BOOK_MAP = {
    'gen': 'gen', 'ex': 'exo', 'lev': 'lev', 'num': 'num', 'deu': 'deu',
    'josh': 'josh', 'judg': 'judg', 'ruth': 'ruth',
    '1-sam': '1sam', '2-sam': '2sam', '1-kgs': '1kgs', '2-kgs': '2kgs',
    '1-chr': '1chr', '2-chr': '2chr',
    'ezra': 'ezra', 'neh': 'neh', 'esth': 'esth',
    'job': 'job', 'ps': 'psa', 'prov': 'prov', 'eccl': 'eccl', 'song': 'song',
    'isa': 'isa', 'jer': 'jer', 'lam': 'lam', 'ezek': 'ezek', 'dan': 'dan',
    'hos': 'hos', 'joel': 'joel', 'amos': 'amos', 'obad': 'obad', 'jonah': 'jonah',
    'mic': 'mic', 'nah': 'nah', 'hab': 'hab', 'zeph': 'zeph', 'hag': 'hag',
    'zech': 'zech', 'mal': 'mal',
    'matt': 'matt', 'mark': 'mark', 'luke': 'luke', 'john': 'john',
    'acts': 'acts', 'rom': 'rom',
    '1-cor': '1cor', '2-cor': '2cor', 'gal': 'gal', 'eph': 'eph',
    'phil': 'phil', 'col': 'col',
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
    'moses': 'moses', 'abr': 'abraham', 'js-m': 'jsm', 'js-h': 'jsh', 'a-of-f': 'aoff',
}

def _resolve_scripture_ref(href):
    """Parse a scripture reference URL into a verse ID like 'isa.55.1'.

    Handles formats like:
      /study/scriptures/ot/isa/55?lang=eng&id=p6#p6
      /study/scriptures/bofm/1-ne/1?lang=eng
      /study/scriptures/tg/faith
    """
    if not href or '/tg/' in href or '/guide/' in href or '/bd/' in href:
        return None  # Topical Guide / Guide to Scriptures / Bible Dictionary — not a verse ref

    # Try pattern: /scriptures/{volume}/{book}/{chapter}
    m = REF_PATTERN.search(href)
    if m:
        volume_path = m.group(1)
        book_path = m.group(2)
        chapter_str = m.group(3)

        # Get verse from fragment: id=p6
        frag_match = re.search(r'id=p(\d+)', href)
        verse_num = frag_match.group(1) if frag_match else "1"

        # Map book path to internal ID
        book_id = SUB_BOOK_MAP.get(book_path)
        if not book_id:
            # D&C: dc-testament/dc/76
            if volume_path == 'dc-testament':
                book_id = f"dc{chapter_str}"
            if not book_id:
                return None

        return f"{book_id}.{chapter_str}.{verse_num}"

    return None


def chapter_num_from_href(href):
    """Extract chapter number from a scripture reference URL."""
    # Already have it in REF_PATTERN, but this handles edge cases
    m = re.search(r'/(\d+)(?:\?|$)', href)
    if m:
        return m.group(1)
    return "1"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest LDS footnotes from Church API")
    parser.add_argument("--books", type=str, help="Comma-separated book IDs (e.g., 'isa,gen')")
    parser.add_argument("--chapters", type=str, help="Comma-separated chapter refs (e.g., 'isa.55,isa.6')")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent API workers (default 5)")
    args = parser.parse_args()

    conn = get_db()
    total_footnotes = 0
    total_xrefs = 0
    chapter_count = 0

    # Build chapter list
    chapters_to_fetch = []

    if args.chapters:
        for ref in args.chapters.split(","):
            parts = ref.strip().split(".")
            if len(parts) >= 2:
                book_id = parts[0]
                chapter = int(parts[1])
                chapters_to_fetch.append((book_id, chapter))
    elif args.books:
        for book_id in args.books.split(","):
            book_id = book_id.strip()
            if book_id == 'dc':
                # All D&C sections
                for sec in range(1, 139):
                    chapters_to_fetch.append((f"dc{sec}", 1))
            elif book_id.startswith('dc'):
                chapters_to_fetch.append((book_id, 1))
            else:
                count = CHAPTER_COUNTS.get(book_id, 10)
                for ch in range(1, count + 1):
                    chapters_to_fetch.append((book_id, ch))
    else:
        # All books (including D&C)
        for book_id, count in CHAPTER_COUNTS.items():
            if book_id.startswith('dc'):
                chapters_to_fetch.append((book_id, 1))
            else:
                for ch in range(1, count + 1):
                    chapters_to_fetch.append((book_id, ch))

    print(f"Fetching {len(chapters_to_fetch)} chapters with {args.workers} concurrent workers...")

    # Check what's already ingested
    existing = set()
    for row in conn.execute("SELECT DISTINCT verse_id FROM footnotes").fetchall():
        parts = row["verse_id"].rsplit(".", 1)
        if len(parts) == 2:
            existing.add(parts[0])  # book.chapter

    to_fetch = [(b, c) for (b, c) in chapters_to_fetch if f"{b}.{c}" not in existing]
    print(f"  {len(to_fetch)} new chapters (skipping {len(chapters_to_fetch) - len(to_fetch)} already ingested)")

    batch_size = 20
    for batch_start in range(0, len(to_fetch), batch_size):
        batch = to_fetch[batch_start:batch_start + batch_size]

        # Fetch concurrently
        results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_map = {pool.submit(fetch_chapter, b, c): (b, c) for (b, c) in batch}
            for future in as_completed(future_map):
                b, c = future_map[future]
                try:
                    result = future.result()
                    if result:
                        results[(b, c)] = result
                except Exception as e:
                    print(f"\n  [ERROR] {b} {c}: {e}")

        # Store results
        for (b, c), result in results.items():
            chapter_count += 1
            fn_count = store_footnotes(conn, b, c, result)
            total_footnotes += fn_count
            xref_count = conn.execute(
                "SELECT COUNT(*) as c FROM cross_references cr "
                "JOIN footnotes f ON cr.footnote_id = f.id "
                "WHERE f.verse_id LIKE ?",
                (f"{b}.{c}.%",)
            ).fetchone()["c"]
            total_xrefs += xref_count
            print(f"  [{chapter_count}/{len(to_fetch)}] {b} {c}: {fn_count} fn, {xref_count} xref")

        if results:
            conn.commit()

    conn.close()
    print(f"\nDone: {total_footnotes} footnotes, {total_xrefs} cross-references across {chapter_count} chapters")


if __name__ == "__main__":
    main()
