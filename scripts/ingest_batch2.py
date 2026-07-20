#!/usr/bin/env python3
"""
Batch 2: Ingest Targum Pseudo-Jonathan, Mishnah, Sibylline Oracles, Exagoge, Nag Hammadi.

Usage:
  python3 scripts/ingest_batch2.py           # Download and ingest all
  python3 scripts/ingest_batch2.py --rebuild-fts  # Also rebuild FTS index
"""

import html.parser
import os
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TEXT_DIR = BASE_DIR / "data" / "texts"
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def add_work(conn, work_id, title, subtitle=""):
    if conn.execute("SELECT id FROM works WHERE id=?", (work_id,)).fetchone():
        return
    mp = conn.execute("SELECT MAX(position) as mp FROM works").fetchone()["mp"] or 0
    conn.execute("INSERT INTO works (id,title,subtitle,position) VALUES (?,?,?,?)",
                 (work_id, title[:100], subtitle[:200], mp + 1))
    conn.commit()


def add_book(conn, work_id, book_id, title, subtitle=""):
    if conn.execute("SELECT id FROM books WHERE id=?", (book_id,)).fetchone():
        return
    mp = conn.execute("SELECT MAX(position) as mp FROM books WHERE work_id=?", (work_id,)).fetchone()["mp"] or 0
    conn.execute("INSERT INTO books (id,work_id,title,subtitle,position) VALUES (?,?,?,?,?)",
                 (book_id, work_id, title[:100], subtitle[:200], mp + 1))
    conn.commit()


def add_verse(conn, book_id, chapter, verse, text):
    vid = f"{book_id}.{chapter}.{verse}"
    text = text[:5000]
    if text.strip():
        conn.execute("INSERT OR IGNORE INTO verses (id,book_id,chapter,verse,text_english) VALUES (?,?,?,?,?)",
                     (vid, book_id, chapter, verse, text))


def download(url, dest_name):
    """Download a file to TEXT_DIR."""
    dest = TEXT_DIR / dest_name
    if dest.exists():
        print(f"  Already have: {dest_name}")
        return str(dest)
    print(f"  Downloading {dest_name}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=60).read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f"    {len(data)} bytes")
    except Exception as e:
        print(f"    FAILED: {e}")
    return str(dest) if dest.exists() else None


# ── 1. Targum Pseudo-Jonathan ──

def ingest_targum(conn):
    """Ingest Targum Pseudo-Jonathan from Etheridge translation."""
    path = download(
        "https://archive.org/stream/cu31924074296975/cu31924074296975_djvu.txt",
        "targum_etheridge.txt"
    )
    if not path:
        return 0
    
    text = open(path, encoding="utf-8", errors="replace").read()
    
    work_id = "targums"
    add_work(conn, work_id, "Targums (Aramaic Bible Translations)")
    
    # The text contains multiple targums. Find Pseudo-Jonathan sections.
    # Pseudo-Jonathan is labeled as "Pseudo-Jonathan" or "Palestinian Targum"
    lines = text.split("\n")
    current_book = "targum_pj_gen"
    current_book_title = "Targum Pseudo-Jonathan - Genesis"
    current_chapter = 1
    current_verse = 1
    verse_text = ""
    added = 0
    in_pj = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) > 2000:
            continue
        
        # Detect book changes
        if "PSEUDO-JONATHAN" in stripped.upper() or "PALESTINIAN TARGUM" in stripped.upper():
            in_pj = True
        
        if not in_pj:
            continue
        
        # Detect chapters
        ch_match = re.match(r'(?:CHAPTER|CHAP\.?|Chapter|Chap\.?)\s+(\d+)', stripped)
        if ch_match:
            if verse_text.strip():
                add_verse(conn, current_book, current_chapter, current_verse, verse_text.strip())
                added += 1
            current_chapter = int(ch_match.group(1))
            current_verse = 1
            verse_text = ""
            continue
        
        # Verse numbers
        vs_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if vs_match:
            if verse_text.strip():
                add_verse(conn, current_book, current_chapter, current_verse, verse_text.strip())
                added += 1
            current_verse = int(vs_match.group(1))
            verse_text = vs_match.group(2)
        else:
            if verse_text:
                verse_text += " " + stripped
            elif stripped:
                verse_text = stripped
    
    if verse_text.strip():
        add_verse(conn, current_book, current_chapter, current_verse, verse_text.strip())
        added += 1
    
    conn.commit()
    return added


# ── 2. Mishnah ──

def ingest_mishnah(conn):
    """Ingest Mishnah — extract Yoma, Tamid, Middot from Danby translation."""
    path = download(
        "https://archive.org/stream/DanbyMishnah/DanbyMishnah_djvu.txt",
        "mishnah_danby.txt"
    )
    if not path:
        return 0
    
    text = open(path, encoding="utf-8", errors="replace").read()
    
    work_id = "mishnah"
    add_work(conn, work_id, "Mishnah (Danby Translation)")
    
    # Extract specific tractates: Yoma, Tamid, Middot
    tractates = {
        "yoma": "Yoma (Day of Atonement)",
        "tamid": "Tamid (Daily Temple Service)",
        "middot": "Middot (Temple Measurements)",
    }
    
    total = 0
    for tid, ttitle in tractates.items():
        # Find tractate in text
        pattern = re.compile(rf'{tid.upper()}[\s\n]*\n', re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            print(f"  Tractate {tid} not found")
            continue
        
        start = match.start()
        # Find next tractate or end
        end = len(text)
        for other_id in tractates:
            if other_id != tid:
                om = re.search(rf'{other_id.upper()}[\s\n]*\n', text[start + 100:], re.IGNORECASE)
                if om:
                    end = min(end, start + 100 + om.start())
        
        section = text[start:end]
        book_id = f"mishnah_{tid}"
        add_book(conn, work_id, book_id, ttitle)
        
        # Parse chapters and verses
        lines = section.split("\n")
        chapter = 1
        verse = 1
        verse_text = ""
        count = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            ch_match = re.match(r'(?:CHAPTER|Chapter|CHAP\.?|Chap\.?)\s+(\d+)', stripped)
            if ch_match:
                if verse_text.strip():
                    add_verse(conn, book_id, chapter, verse, verse_text.strip())
                    count += 1
                chapter = int(ch_match.group(1))
                verse = 1
                verse_text = ""
                continue
            
            vs_match = re.match(r'^(\d+)\.\s*[A-Z]', stripped)
            if vs_match and len(stripped) < 200:
                if verse_text.strip():
                    add_verse(conn, book_id, chapter, verse, verse_text.strip())
                    count += 1
                verse = int(vs_match.group(1))
                verse_text = re.sub(r'^\d+\.\s*', '', stripped)
            else:
                if verse_text:
                    verse_text += " " + stripped
                elif stripped:
                    verse_text = stripped
        
        if verse_text.strip():
            add_verse(conn, book_id, chapter, verse, verse_text.strip())
            count += 1
        
        conn.commit()
        print(f"  {tid}: {count} verses")
        total += count
    
    return total


# ── 3. Sibylline Oracles ──

def ingest_sibylline(conn):
    """Ingest Sibylline Oracles from Terry translation."""
    path = download(
        "https://archive.org/stream/sibyllineoracle00terrgoog/sibyllineoracle00terrgoog_djvu.txt",
        "sibylline_terry.txt"
    )
    if not path:
        return 0
    
    text = open(path, encoding="utf-8", errors="replace").read()
    
    work_id = "sibylline_oracles"
    book_id = "sibylline_oracles"
    add_work(conn, work_id, "Sibylline Oracles (Terry Translation)")
    add_book(conn, work_id, book_id, "The Sibylline Oracles (Books I-XIV)")
    
    # Terry format: Book I-VIII headings with numbered lines
    lines = text.split("\n")
    current_book = 1
    current_line = 1
    line_text = ""
    added = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) > 1000:
            continue
        
        # Book headers
        bk_match = re.match(r'BOOK\s+([IVXLCDM]+)', stripped, re.IGNORECASE)
        if bk_match:
            if line_text.strip():
                add_verse(conn, book_id, current_book, current_line, line_text.strip())
                added += 1
            current_book = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,
                           'IX':9,'X':10,'XI':11,'XII':12,'XIII':13,'XIV':14}.get(bk_match.group(1).upper(), 1)
            current_line = 1
            line_text = ""
            continue
        
        # Line numbers
        ln_match = re.match(r'^(\d+)\s+(.*)', stripped)
        if ln_match:
            if line_text.strip():
                add_verse(conn, book_id, current_book, current_line, line_text.strip())
                added += 1
            current_line = int(ln_match.group(1))
            line_text = ln_match.group(2)
        else:
            if line_text:
                line_text += " " + stripped
    
    if line_text.strip():
        add_verse(conn, book_id, current_book, current_line, line_text.strip())
        added += 1
    
    conn.commit()
    return added


# ── 4. Exagoge ──

def ingest_exagoge(conn):
    """Extract Ezekiel the Tragedian's Exagoge from Eusebius."""
    path = download(
        "https://archive.org/stream/eusebius-preparation-for-the-gospel-full-work-gifford-1903-trans/"
        "Eusebius%2C%20Preparation%20for%20the%20Gospel%20-%20English%20Translation%20"
        "%282%20vols%20in%201%20-%20Gifford%201903%20trans%29_djvu.txt",
        "eusebius_gifford.txt"
    )
    if not path:
        return 0
    
    text = open(path, encoding="utf-8", errors="replace").read()
    
    work_id = "hellenistic_jewish"
    book_id = "exagoge"
    add_work(conn, work_id, "Hellenistic Jewish Literature")
    add_book(conn, work_id, book_id, "Ezekiel the Tragedian - Exagoge")
    
    # Find Book IX
    book9_start = None
    for pat in [r'BOOK\s+IX', r'Book\s+IX']:
        m = re.search(pat, text)
        if m:
            book9_start = m.start()
            break
    
    if not book9_start:
        print("  Book IX not found")
        return 0
    
    book9 = text[book9_start:]
    
    # Find Exagoge sections (Ezekiel references)
    lines = book9.split("\n")
    in_exagoge = False
    verse = 1
    verse_text = ""
    added = 0
    in_poetry = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        if "Ezekiel" in stripped and ("traged" in stripped.lower() or "Exagoge" in stripped or "drama" in stripped.lower()):
            in_exagoge = True
            continue
        
        if in_exagoge:
            # Detect poetic lines (indented, quoted)
            if stripped.startswith('"') or stripped.startswith('  ') or stripped.startswith('\t'):
                in_poetry = True
                clean = stripped.strip('" ')
                if clean:
                    if verse_text:
                        verse_text += " " + clean
                    else:
                        verse_text = clean
            elif in_poetry and stripped and not stripped.startswith('"') and len(stripped) > 20:
                # Still in poetic section
                if verse_text:
                    verse_text += " " + stripped
            else:
                # End of poetic section - save verse
                if verse_text.strip():
                    add_verse(conn, book_id, 1, verse, verse_text.strip())
                    added += 1
                    verse += 1
                    verse_text = ""
                in_poetry = False
            
            # Check for end of Exagoge
            if "BOOK X" in stripped or "BOOK X" in stripped:
                break
    
    if verse_text.strip():
        add_verse(conn, book_id, 1, verse, verse_text.strip())
        added += 1
    
    conn.commit()
    return added


# ── 5. Nag Hammadi ──

class HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip = True
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = False
        if tag in ('p', 'br', 'div', 'h1', 'h2', 'h3', 'h4'):
            self.text.append('\n')
    def handle_data(self, data):
        if not self._skip and data.strip():
            self.text.append(data.strip() + ' ')


def ingest_nag_hammadi(conn):
    """Ingest Nag Hammadi texts from gnosis.org."""
    texts = {
        "gospel_philip": {
            "url": "http://www.gnosis.org/naghamm/gop.html",
            "title": "Gospel of Philip",
            "pd": False,
        },
        "apocryphon_john": {
            "url": "http://www.gnosis.org/naghamm/apocjn.html",
            "title": "Apocryphon of John",
            "pd": False,
        },
        "hypostasis_archons": {
            "url": "http://www.gnosis.org/naghamm/hypostas.html",
            "title": "Hypostasis of the Archons",
            "pd": False,
        },
        "trimorphic_protennoia": {
            "url": "http://www.gnosis.org/naghamm/trimorph.html",
            "title": "Trimorphic Protennoia",
            "pd": False,
        },
        "thunder_perfect_mind": {
            "url": "http://www.gnosis.org/naghamm/thunder.html",
            "title": "Thunder, Perfect Mind",
            "pd": False,
        },
    }
    
    work_id = "nag_hammadi"
    add_work(conn, work_id, "Nag Hammadi Library")
    
    total = 0
    for bid, info in texts.items():
        print(f"  Fetching {info['title']}...")
        try:
            req = urllib.request.Request(info["url"], headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
            
            extractor = HTMLTextExtractor()
            extractor.feed(html)
            clean_text = '\n'.join(extractor.text)
            
            # Save raw text
            with open(TEXT_DIR / f"nag_{bid}.txt", "w") as f:
                f.write(clean_text)
            
            add_book(conn, work_id, bid, info["title"])
            
            # Parse into sections/verses
            lines = clean_text.split("\n")
            section = 1
            section_text = ""
            count = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped or len(stripped) > 2000:
                    continue
                
                # Check for page markers and skip
                if stripped.startswith("[") and stripped.endswith("]") and len(stripped) < 20:
                    continue
                
                if section_text:
                    section_text += " " + stripped
                else:
                    section_text = stripped
                
                if len(section_text) > 300:
                    add_verse(conn, bid, 1, section, section_text[:5000])
                    count += 1
                    section += 1
                    section_text = ""
            
            if section_text.strip():
                add_verse(conn, bid, 1, section, section_text[:5000])
                count += 1
            
            conn.commit()
            print(f"    {count} sections")
            total += count
            
        except Exception as e:
            print(f"    FAILED: {e}")
    
    return total


# ── 6. Ugaritic Baal Cycle via Ginsberg (Marquette PDF) ──

def ingest_baal_cycle(conn):
    """Ingest Ugaritic Baal Cycle from Ginsberg ANET translation."""
    path = download(
        "https://www.marquette.edu/maqom/baalyamm.pdf",
        "baal_cycle.pdf"
    )
    if not path:
        # Try alternative source
        path = download(
            "https://archive.org/stream/CanaaniteMythsAndLegends/Canaanite%20Myths%20and%20Legends_djvu.txt",
            "canaanite_myths.txt"
        )
        if path:
            # Driver translation — parse it
            text = open(path, encoding="utf-8", errors="replace").read()
            work_id = "ugaritic_texts"
            book_id = "baal_cycle"
            add_work(conn, work_id, "Ugaritic Texts")
            add_book(conn, work_id, book_id, "Baal Cycle (Driver Translation)")
            
            # Parse sections with line numbers
            lines = text.split("\n")
            current_tablet = 1
            current_line = 1
            line_text = ""
            added = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                
                tab_match = re.match(r'(?:TABLET|Tablet)\s+([IVXLCDM]+)', stripped)
                if tab_match:
                    if line_text.strip():
                        add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
                        added += 1
                    current_tablet = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6}.get(tab_match.group(1).upper(), 1)
                    current_line = 1
                    line_text = ""
                    continue
                
                ln_match = re.match(r'^(\d+)\s+(.*)', stripped)
                if ln_match:
                    if line_text.strip():
                        add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
                        added += 1
                    current_line = int(ln_match.group(1))
                    line_text = ln_match.group(2)
                else:
                    if line_text:
                        line_text += " " + stripped
            
            if line_text.strip():
                add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
                added += 1
            
            conn.commit()
            return added
    
    return 0


def rebuild_fts(conn):
    """Rebuild the FTS5 trigram index."""
    print("\n=== Rebuilding FTS Index ===")
    conn.execute("DELETE FROM verses_fts_trigram")
    
    verses = conn.execute("SELECT id, text_english FROM verses ORDER BY id").fetchall()
    total = 0
    for v in verses:
        text = (v["text_english"] or "")[:5000]
        if text.strip():
            conn.execute(
                "INSERT INTO verses_fts_trigram (verse_id, book_id, search_text) VALUES (?, '?', ?)",
                (v["id"], text)
            )
            total += 1
            if total % 10000 == 0:
                conn.commit()
    
    conn.commit()
    
    check = conn.execute("SELECT COUNT(*) as c FROM verses_fts_trigram").fetchone()["c"]
    total_v = conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()["c"]
    print(f"  FTS entries: {check} / {total_v} verses")
    return check


def main():
    conn = get_conn()
    
    print("=== Batch 2: Ingest Missing Texts ===\n")
    
    print("1. Targum Pseudo-Jonathan...")
    count = ingest_targum(conn)
    print(f"   Result: {count} verses\n")
    
    print("2. Mishnah (Yoma, Tamid, Middot)...")
    count = ingest_mishnah(conn)
    print(f"   Result: {count} verses\n")
    
    print("3. Sibylline Oracles...")
    count = ingest_sibylline(conn)
    print(f"   Result: {count} verses\n")
    
    print("4. Exagoge (Ezekiel the Tragedian)...")
    count = ingest_exagoge(conn)
    print(f"   Result: {count} verses\n")
    
    print("5. Nag Hammadi core texts...")
    count = ingest_nag_hammadi(conn)
    print(f"   Result: {count} sections\n")
    
    print("6. Ugaritic Baal Cycle...")
    try:
        count = ingest_baal_cycle(conn)
        print(f"   Result: {count} verses\n")
    except Exception as e:
        print(f"   SKIPPED: {e}\n")
    
    if "--rebuild-fts" in sys.argv:
        rebuild_fts(conn)
    
    # Summary
    print("\n=== Final Database ===")
    works = conn.execute("SELECT id, title FROM works ORDER BY position").fetchall()
    for w in works:
        vc = conn.execute("""
            SELECT COUNT(*) as c FROM verses v 
            JOIN books b ON b.id=v.book_id WHERE b.work_id=?
        """, (w["id"],)).fetchone()["c"]
        print(f"  {w['id']:25s}: {vc:>6} verses")
    
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
