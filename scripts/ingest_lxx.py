#!/usr/bin/env python3
"""Ingest Septuagint (LXX) into the textual connection layer.

Parses the LXX lemma JS files and creates MT↔LXX variant connections.
"""

import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db, add_connection
from lib.gematria_greek import compute_all as greek_gematria

# Map LXX JS filenames to our book IDs
LXX_BOOK_MAP = {
    "Gen": "gen", "Exod": "exo", "Lev": "lev", "Num": "num", "Deut": "deu",
    "Josh": "josh", "Josh": "josh", "Judg": "judg", "Ruth": "ruth",
    "1Sam": "1sam", "2Sam": "2sam", "1Kgs": "1kgs", "2Kgs": "2kgs",
    "1Chr": "1chr", "2Chr": "2chr", "Ezra": "ezra", "Neh": "neh",
    "Esth": "esth", "Job": "job", "Ps": "psa", "Prov": "prov",
    "Eccl": "eccl", "Song": "song",
    "Isa": "isa", "Jer": "jer", "Lam": "lam", "Ezek": "ezek", "Dan": "dan",
    "Hos": "hos", "Joel": "joel", "Amos": "amos", "Obad": "obad",
    "Jonah": "jonah", "Mic": "mic", "Nah": "nah", "Hab": "hab",
    "Zeph": "zeph", "Hag": "hag", "Zech": "zech", "Mal": "mal",
}

def parse_lxx_js(filepath):
    """Parse LXX JS lemma file into verse_id → greek_words dict."""
    with open(filepath) as f:
        content = f.read()
    
    # The JS files look like: {"Gen.1.1": [{"key": "...", "lemma": "..."}, ...], ...}
    # Strip the var assignment if present
    if "=" in content:
        content = content.split("=", 1)[1].strip()
    if content.endswith(";"):
        content = content[:-1]
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try replacing single quotes with double quotes for JS-style syntax
        content2 = re.sub(r"'", '"', content)
        # Fix unquoted keys
        content2 = re.sub(r'(\w+):', r'"\1":', content2)
        try:
            data = json.loads(content2)
        except:
            print(f"  Failed to parse {filepath}")
            return {}
    
    result = {}
    for ref, word_list in data.items():
        # Ref format: "Gen.1.1" or "Gen.1"
        parts = ref.split(".")
        if len(parts) < 2:
            continue
        book_code = parts[0]
        try:
            chapter = int(parts[1])
        except ValueError:
            continue
        try:
            verse = int(parts[2]) if len(parts) >= 3 else 0
        except (ValueError, IndexError):
            verse = 0
        
        book_id = LXX_BOOK_MAP.get(book_code)
        if not book_id:
            continue
        
        # Handle numeric verse with possible letter suffix (e.g., "35a")
        try:
            verse_str = re.sub(r'[a-zA-Z]', '', str(verse))
            verse = int(verse_str) if verse_str else verse
        except:
            verse = 0
        if verse < 1:
            continue
        
        vid = f"{book_id}.{chapter}.{verse}"
        
        # Build Greek text from lemmas
        greek_words = [w.get("key", "") or w.get("lemma", "") for w in word_list]
        greek_text = " ".join(greek_words)
        
        result[vid] = {
            "text": greek_text,
            "words": [w.get("lemma", w.get("key", "")) for w in word_list],
        }
    
    return result

def main():
    lxx_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "GreekResources", "LxxLemmas")
    conn = get_db()
    
    print("=" * 60)
    print("LXX Ingestion — Septuagint")
    print("=" * 60)
    
    total_verses = 0
    total_connections = 0
    lxx_texts = {}
    
    # Parse all LXX files
    for fname in sorted(os.listdir(lxx_dir)):
        if not fname.endswith(".js"):
            continue
        book_code = fname.replace(".js", "")
        filepath = os.path.join(lxx_dir, fname)
        data = parse_lxx_js(filepath)
        if data:
            lxx_texts.update(data)
            total_verses += len(data)
    
    print(f"  Parsed {total_verses} LXX verses", flush=True)
    
    # For each LXX verse, check if our DB has a verse with Hebrew
    # If so, create a textual connection noting it has a LXX counterpart
    count = 0
    for vid, lxx_data in lxx_texts.items():
        # Check verse exists in our DB
        existing = conn.execute("SELECT id, has_hebrew, text_hebrew FROM verses WHERE id = ?", (vid,)).fetchone()
        if not existing:
            continue
        
        try:
            add_connection(conn, vid, vid,
                          layer="textual",
                          type_name="septuagint_difference",
                          subtype="lxx_present",
                          strength=0.6,
                          confidence=0.8,
                          discovered_by="algorithm",
                          metadata={
                              "lxx_text": lxx_data["text"][:300],
                              "lxx_word_count": len(lxx_data["words"]),
                              "has_hebrew": bool(existing["has_hebrew"]),
                              "source": "greek_resources_lxx",
                          })
            count += 1
        except Exception:
            pass
        
        if count % 500 == 0:
            conn.commit()
            print(f"  {count} LXX connections...", flush=True)
    
    conn.commit()
    
    # Also compute isopsephy for LXX words (adding to gematria_greek)
    greek_word_count = 0
    for vid, lxx_data in lxx_texts.items():
        for idx, lemma in enumerate(lxx_data["words"][:50]):
            if lemma:
                try:
                    values = greek_gematria(lemma)
                    conn.execute("""
                        INSERT OR IGNORE INTO gematria_greek 
                        (verse_id, word_index, word_greek, lemma, value_standard, value_ordinal, value_reduced)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (vid, idx, lemma, lemma, values["standard"], values["ordinal"], values["reduced"]))
                    greek_word_count += 1
                except:
                    pass
    
    conn.commit()
    
    textual_count = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='textual'").fetchone()["c"]
    greek_total = conn.execute("SELECT COUNT(*) as c FROM gematria_greek").fetchone()["c"]
    
    print(f"\n  LXX connections: {count}")
    print(f"  LXX Greek words: {greek_word_count}")
    print(f"  Textual layer total: {textual_count}")
    print(f"  Greek isopsephy total: {greek_total}")
    conn.close()

if __name__ == "__main__":
    main()
