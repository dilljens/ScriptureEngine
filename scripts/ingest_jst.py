#!/usr/bin/env python3
"""Ingest Joseph Smith Translation (JST) into the textual connection layer."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import add_connection, get_db

JST_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "joseph-smith-translation", "bible-jst.txt")
KJV_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "joseph-smith-translation", "bible-kjv.txt")

BOOK_MAP = {
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num",
    "Deuteronomy": "deu", "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "1 Samuel": "1sam", "2 Samuel": "2sam", "1 Kings": "1kgs", "2 Kings": "2kgs",
    "1 Chronicles": "1chr", "2 Chronicles": "2chr", "Ezra": "ezra", "Nehemiah": "neh",
    "Esther": "esth", "Job": "job", "Psalms": "psa", "Proverbs": "prov",
    "Ecclesiastes": "eccl", "Solomon's Song": "song",
    "Isaiah": "isa", "Jeremiah": "jer", "Lamentations": "lam", "Ezekiel": "ezek",
    "Daniel": "dan", "Hosea": "hos", "Joel": "joel", "Amos": "amos",
    "Obadiah": "obad", "Jonah": "jonah", "Micah": "mic", "Nahum": "nah",
    "Habakkuk": "hab", "Zephaniah": "zeph", "Haggai": "hag", "Zechariah": "zech", "Malachi": "mal",
    "Matthew": "matt", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Romans": "rom", "1 Corinthians": "1cor", "2 Corinthians": "2cor",
    "Galatians": "gal", "Ephesians": "eph", "Philippians": "phil", "Colossians": "col",
    "1 Thessalonians": "1thes", "2 Thessalonians": "2thes",
    "1 Timothy": "1tim", "2 Timothy": "2tim", "Titus": "titus",
    "Philemon": "philem", "Hebrews": "heb", "James": "james",
    "1 Peter": "1pet", "2 Peter": "2pet", "1 John": "1john",
    "2 John": "2john", "3 John": "3john", "Jude": "jude", "Revelation": "rev",
}

def normalize(text):
    return re.sub(r'\s+', ' ', text.strip().lower().replace("'", "'"))

def is_real_change(k, j):
    kn = normalize(k); jn = normalize(j)
    if kn == jn: return False
    kc = re.sub(r'[^\w\s]', '', kn); jc = re.sub(r'[^\w\s]', '', jn)
    return kc != jc

def main():
    conn = get_db()
    print("Loading JST/KJV...", flush=True)
    raw = {"kjv": {}, "jst": {}}
    for name in ("kjv", "jst"):
        fpath = JST_FILE if name == "jst" else KJV_FILE
        with open(fpath) as f:
            for line in f:
                parts = line.strip().split('\t', 1)
                if len(parts) != 2: continue
                m = re.match(r'^([\w\s]+?)\s+(\d+):(\d+)$', parts[0].strip())
                if not m: continue
                bid = BOOK_MAP.get(m.group(1).strip())
                if not bid: continue
                raw[name][f"{bid}.{int(m.group(2))}.{int(m.group(3))}"] = parts[1].strip()
    print(f"  KJV: {len(raw['kjv'])} JST: {len(raw['jst'])}", flush=True)

    count = 0; same = 0
    for vid in sorted(set(raw['kjv']) & set(raw['jst'])):
        k = raw['kjv'][vid]; j = raw['jst'][vid]
        if not is_real_change(k, j): same += 1; continue
        j_len = len(normalize(j))
        k_len = len(normalize(k))
        ctype = "jst_addition" if j_len > k_len * 1.3 else "jst_change"
        try:
            add_connection(conn, vid, vid, layer="textual", type_name=ctype,
                subtype="joseph_smith", strength=0.8, confidence=0.9,
                discovered_by="algorithm",
                metadata={"jst": j[:300], "kjv": k[:300]})
            count += 1
        except Exception:
            pass
        if count % 300 == 0:
            conn.commit(); print(f"  {count}...", flush=True)

    conn.commit()
    t = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='textual'").fetchone()["c"]
    print(f"\n  JST changes: {count}, Identical/punct: {same}, Textual layer total: {t}")
    conn.close()

if __name__ == "__main__":
    main()
