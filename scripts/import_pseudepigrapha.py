#!/usr/bin/env python3
"""
Import expanded canon texts (pseudepigrapha, deuterocanon, etc.) from
the scrollmapper/bible_databases_deuterocanonical dataset.

Creates a new 'pseu' work in the database.

Usage: python3 scripts/import_pseudepigrapha.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

SCROLLMAPPER = "/tmp/bible_databases_deuterocanonical/sources/en"

# Texts to skip — already imported in apocrypha work
SKIP_APOCRYPHA = {
    '1-esdras', '2-esdras', '1-maccabees', '2-maccabees',
    'book-of-tobit', 'book-of-judith', 'book-of-sirach',
    'wisdom-of-solomon', 'susanna', 'bel-and-the-dragon',
    'prayer-of-manasseh', '1-baruch',
}

# Texts that should go into DSS work instead
DSS_TEXTS = {
    'songs-of-the-sabbath-sacrifice', 'genesis-apocryphon',
    'book-of-giants', 'visions-of-amram', 'testament-of-kohath',
}

# Map dir names to book IDs and titles
TEXT_MAP = [
    # Pseudepigrapha — new pseu work
    ('1-enoch', '1en', '1 Enoch (Ethiopic)'),
    ('2-enoch', '2en', '2 Enoch (Slavonic)'),
    ('3-baruch', '3bar', '3 Baruch (Greek Apocalypse)'),
    ('4-baruch', '4bar', '4 Baruch (Rest of Words of Baruch)'),
    ('1-hermas', '1her', 'Shepherd of Hermas — Visions'),
    ('2-hermas', '2her', 'Shepherd of Hermas — Mandates'),
    ('3-hermas', '3her', 'Shepherd of Hermas — Similitudes'),
    ('1-adam-and-eve', '1adae', 'Life of Adam and Eve (Vita)'),
    ('2-adam-and-eve', '2adae', 'Life of Adam and Eve (Apocalypse)'),
    ('apocalypse-of-abraham', 'apabr', 'Apocalypse of Abraham'),
    ('apocalypse-of-elijah', 'apelj', 'Apocalypse of Elijah'),
    ('apocalypse-of-peter', 'apet', 'Apocalypse of Peter'),
    ('apocalypse-of-sedrach', 'apsed', 'Apocalypse of Sedrach'),
    ('apocryphon-of-joshua', 'apjosh', 'Apocryphon of Joshua'),
    ('ascension-of-isaiah', 'ascis', 'Ascension of Isaiah'),
    ('assumption-of-moses', 'asmos', 'Assumption of Moses'),
    ('azar', 'azar', 'Prayer of Azariah'),
    ('balaam-inscription', 'balin', 'Balaam Inscription'),
    ('book-of-jasher', 'jasher', 'Book of Jasher'),
    ('book-of-jubilees', 'jub', 'Book of Jubilees'),
    ('book-of-nathan-the-prophet', 'nathan', 'Book of Nathan the Prophet'),
    ('epistle-of-barnabas', 'barn', 'Epistle of Barnabas'),
    ('five-psalms-of-david', '5psdav', 'Five Psalms of David'),
    ('gad-the-seer', 'gad', 'Gad the Seer'),
    ('gospel-of-nicodemus', 'gnic', 'Gospel of Nicodemus (Acta Pilati)'),
    ('greek-esther', 'grkest', 'Greek Esther (LXX additions)'),
    ('history-of-the-rechabites', 'rechab', 'History of the Rechabites'),
    ('jannes-and-jambres', 'janjam', 'Jannes and Jambres'),
    ('joseph-and-asenath', 'josasen', 'Joseph and Asenath'),
    ('ladder-of-jacob', 'ladjac', 'Ladder of Jacob'),
    ('lives-of-the-prophets', 'livprop', 'Lives of the Prophets'),
    ('odes-of-solomon', 'odessol', 'Odes of Solomon'),
    ('psalms-of-solomon', 'psssol', 'Psalms of Solomon'),
    ('testament-of-abraham', 'tabr', 'Testament of Abraham'),
    ('testament-of-isaac', 'tisaac', 'Testament of Isaac'),
    ('testament-of-jacob', 'tjacob', 'Testament of Jacob'),
    ('testament-of-job', 'tjob', 'Testament of Job'),
    ('testament-of-solomon', 'tsol', 'Testament of Solomon'),
    ('wisdom-of-ahikar', 'ahikar', 'Wisdom of Ahikar'),
    # Individual Testaments of the 12 Patriarchs
    ('testament-of-reuben', 'treub', 'Testament of Reuben'),
    ('testament-of-simeon', 'tsimeon', 'Testament of Simeon'),
    ('testament-of-levi', 'tlevi', 'Testament of Levi'),
    ('testament-of-judah', 'tjudah', 'Testament of Judah'),
    ('testament-of-dan', 'tdan', 'Testament of Dan'),
    ('testament-of-naphtali', 'tnaph', 'Testament of Naphtali'),
    ('testament-of-gad', 'tgad', 'Testament of Gad'),
    ('testament-of-asher', 'tasher', 'Testament of Asher'),
    ('testament-of-issachar', 'tiss', 'Testament of Issachar'),
    ('testament-of-zebulun', 'tzeb', 'Testament of Zebulun'),
    ('testament-of-joseph', 'tjos', 'Testament of Joseph'),
    ('testament-of-benjamin', 'tbenj', 'Testament of Benjamin'),
    # DSS texts that should go into the dss work
    ('songs-of-the-sabbath-sacrifice', '4Q400', 'Songs of the Sabbath Sacrifice'),
    ('genesis-apocryphon', '1Q20', 'Genesis Apocryphon (1Q20)'),
    ('book-of-giants', 'bookgiants', 'Book of Giants (4Q530-533)'),
    ('visions-of-amram', 'visamram', 'Visions of Amram (4Q543-548)'),
    ('testament-of-kohath', 'tkohath', 'Testament of Kohath (4Q542)'),
]


def main():
    conn = get_db()
    
    # Create the pseu work
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('pseu', 'Pseudepigrapha & Expanded Canon')")
    
    total_books = 0
    total_verses = 0
    
    for dirname, book_id, title in TEXT_MAP:
        json_path = os.path.join(SCROLLMAPPER, dirname, f"{dirname}.json")
        if not os.path.exists(json_path):
            print(f"  SKIP {dirname}: not found")
            continue
        
        with open(json_path) as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"  SKIP {dirname}: JSON error — {e}")
                continue
        
        books_data = data.get('books', [])
        if not books_data:
            print(f"  SKIP {dirname}: no books in JSON")
            continue
        
        # Determine which work this belongs to
        if dirname in DSS_TEXTS:
            work_id = 'dss'
        else:
            work_id = 'pseu'
        
        # Create book entry
        conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, ?, ?, 99)",
            (book_id, work_id, title)
        )
        
        chapter_count = 0
        verse_count = 0
        
        for book_data in books_data:
            for ch_data in book_data.get('chapters', []):
                ch_num = ch_data.get('chapter', chapter_count + 1)
                
                for v_data in ch_data.get('verses', []):
                    v_num = v_data.get('verse', verse_count + 1)
                    text = v_data.get('text', '').strip()
                    
                    if not text:
                        continue
                    
                    verse_id = f"{book_id}.{ch_num}.{v_num}"
                    
                    if work_id == 'dss':
                        # For DSS texts: store in text_hebrew too for consistency
                        conn.execute(
                            "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                            (verse_id, book_id, ch_num, v_num, text)
                        )
                    else:
                        conn.execute(
                            "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                            (verse_id, book_id, ch_num, v_num, text)
                        )
                    
                    # Also store as text resource
                    conn.execute(
                        "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'SCROLLMAPPER', ?, 'eng')",
                        (verse_id, text)
                    )
                    
                    verse_count += 1
                
                chapter_count += 1
        
        conn.commit()
        total_verses += verse_count
        total_books += 1
        print(f"  {book_id:8s} {title[:45]:45s} {verse_count:5d} verses [{work_id}]")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"Imported: {total_books} texts, {total_verses} total verses")
    print(f"Work: 'pseu' = Pseudepigrapha & Expanded Canon")
    print(f"Also added 5 texts to 'dss' work (Songs Sabbath, Genesis Apocryphon, etc.)")


if __name__ == '__main__':
    main()
