#!/usr/bin/env python3
"""Align real audio timestamps to verses using Whisper.

Processes a full book at once: transcribes the entire audio with whisper,
then aligns verse boundaries by matching whisper segments to verses.

Usage:
  python3 scripts/align_audio.py --book gen              # align all of Genesis
  python3 scripts/align_audio.py --book gen --chapter 2  # align just one chapter
  python3 scripts/align_audio.py --book gen --force      # re-transcribe even if cached
  python3 scripts/align_audio.py --list                  # show available books
"""

import gc
import json
import os
import re
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

BOOK_MAP = {
    "gen": "01_Genesis.mp3", "exo": "02_Exodus.mp3", "lev": "03_Leviticus.mp3",
    "num": "04_Numbers.mp3", "deu": "05_Deuteronomy.mp3", "josh": "07_Judges.mp3",
    "judg": "07_Judges.mp3", "ruth": "08_Ruth.mp3", "1sam": "09_1Samuel.mp3",
    "2sam": "10_2Samuel.mp3", "1kgs": "11_1Kings.mp3", "2kgs": "12_2Kings.mp3",
    "1chr": "13_1Chronicles.mp3", "2chr": "14_2Chronicles.mp3",
    "ezra": "15_Ezra.mp3", "neh": "16_Nehemiah.mp3", "esth": "17_Esther.mp3",
    "job": "18_Job.mp3", "psa": "19_Psalms.mp3", "prov": "20_Proverbs.mp3",
    "eccl": "21_Ecclesiastes.mp3", "song": "22_SongofSongs.mp3",
    "isa": "23_Isaiah.mp3", "jer": "24_Jeremiah.mp3", "lam": "25_Lamentations.mp3",
    "ezek": "26_Ezekiel.mp3", "dan": "27_Daniel.mp3", "hos": "28_Hosea.mp3",
    "joel": "29_Joel.mp3", "amos": "30_Amos.mp3", "obad": "31_Obadiah.mp3",
    "jonah": "32_Jonah.mp3", "mic": "33_Micah.mp3", "nah": "34_Nahum.mp3",
    "hab": "35_Habakkuk.mp3", "zeph": "36_Zephaniah.mp3", "hag": "37_Haggai.mp3",
    "zech": "38_Zechariah.mp3" if os.path.exists("data/audio/raw/38_Zechariah.mp3") else None,
    "mal": "39_Malachi.mp3",
}


def clean_heb(txt):
    if not txt:
        return ""
    txt = re.sub(r'[\u0591-\u05C7]', '', txt)
    txt = re.sub(r'[\u05F3\u05F4]', '', txt)
    txt = re.sub(r'[,\\.;:!?()\-\'"\[\]/\u05BE]', '', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def align_book(audio_path, source_file, book_id, chapter_filter=None, force_transcribe=False):
    """Align a full book's audio to its verses."""
    os.makedirs("data/audio/raw/transcriptions", exist_ok=True)

    book_label = source_file.replace(".mp3", "")
    whisper_file = f"data/audio/raw/transcriptions/{book_label}.json"

    # Transcribe or load cached
    if force_transcribe or not os.path.exists(whisper_file):
        print(f"Transcribing {source_file} with whisper small...")
        import whisper
        gc.collect()
        torch.cuda.empty_cache()

        model = whisper.load_model("small")
        result = model.transcribe(audio_path, language="he", word_timestamps=True)

        with open(whisper_file, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Saved transcription ({len(result['segments'])} segments)")
        del model
        gc.collect()
        torch.cuda.empty_cache()
    else:
        with open(whisper_file) as f:
            result = json.load(f)
        print(f"Loaded transcription ({len(result['segments'])} segments)")

    # Get all verses for this book
    conn = get_db()
    if chapter_filter:
        verses = conn.execute("""
            SELECT id, book_id, chapter, verse, text_hebrew FROM verses
            WHERE book_id = ? AND chapter = ?
            ORDER BY chapter, verse
        """, (book_id, chapter_filter)).fetchall()
    else:
        verses = conn.execute("""
            SELECT id, book_id, chapter, verse, text_hebrew FROM verses
            WHERE book_id = ? AND text_hebrew IS NOT NULL
            ORDER BY chapter, verse
        """, (book_id,)).fetchall()
    conn.close()

    if not verses:
        print(f"  No verses found for {book_id}")
        return

    print(f"  Aligning {len(verses)} verses...")

    # Build verse data
    vdata = []
    for v in verses:
        clean = clean_heb(v["text_hebrew"])
        vdata.append({
            "id": v["id"],
            "book": v["book_id"],
            "chapter": v["chapter"],
            "clean": clean,
            "words": [w for w in clean.split() if len(w) > 1 and not w.startswith('/') and not w.endswith('/')],
            "start_sec": -1.0,
            "end_sec": -1.0,
        })

    # Build word timeline
    all_words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            wt = w.get("word", "").strip(" ,.!?;:'\"[]-")
            if wt:
                all_words.append({
                    "text": wt,
                    "clean": wt.lower().strip(",.!?;:'\"[]-/\u05be"),
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                })

    # Match each whisper segment to verses by text overlap
    segments = result.get("segments", [])
    verse_timeline = []

    for seg in segments:
        seg_clean = clean_heb(seg.get("text", ""))
        seg_words_set = set(seg_clean.split())

        seg_verse_ids = []
        for vd in vdata:
            if vd["clean"]:
                vw_set = set(vd["clean"].split())
                overlap = len(seg_words_set & vw_set)
                if overlap >= 2:
                    seg_verse_ids.append(vd["id"])

        verse_timeline.append((seg["start"], seg["end"], seg_verse_ids, seg_clean[:60]))

    # Distribute each segment's time across its verses
    for seg_start, seg_end, seg_vids, _ in verse_timeline:
        if not seg_vids:
            continue
        seg_duration = seg_end - seg_start
        vc = len(seg_vids)

        for vi, vid in enumerate(seg_vids):
            vd = next(v for v in vdata if v["id"] == vid)
            vd["start_sec"] = seg_start + (seg_duration * vi / vc)
            vd["end_sec"] = seg_start + (seg_duration * (vi + 1) / vc)

    # Fill unassigned verses by interpolation
    for i, vd in enumerate(vdata):
        if vd["start_sec"] < 0:
            prev_v = next((v for v in reversed(vdata[:i]) if v["start_sec"] >= 0), None)
            next_v = next((v for v in vdata[i+1:] if v["start_sec"] >= 0), None)

            if prev_v and next_v:
                pi = vdata.index(prev_v)
                ni = vdata.index(next_v)
                gap = next_v["start_sec"] - prev_v["end_sec"]
                num_gap = sum(1 for v in vdata[pi:ni] if v["start_sec"] < 0)
                pos_gap = sum(1 for v in vdata[pi:i] if v["start_sec"] < 0)
                vd["start_sec"] = prev_v["end_sec"] + (gap * pos_gap / (num_gap + 1))
                vd["end_sec"] = prev_v["end_sec"] + (gap * (pos_gap + 1) / (num_gap + 1))
            elif prev_v:
                vd["start_sec"] = prev_v["end_sec"]
                vd["end_sec"] = vd["start_sec"] + 3.0
            elif next_v:
                vd["end_sec"] = next_v["start_sec"]
                vd["start_sec"] = vd["end_sec"] - 3.0
            else:
                vd["start_sec"] = 0.0
                vd["end_sec"] = 3.0

    # Build word-level timestamps per verse
    v_ts = {vd["id"]: [] for vd in vdata}
    for w in all_words:
        for vd in vdata:
            if vd["start_sec"] <= w["start"] <= vd["end_sec"]:
                v_ts[vd["id"]].append({"word": w["text"], "start": w["start"], "end": w["end"]})

    # Save to DB
    conn = get_db()
    count = 0
    for vd in vdata:
        if vd["start_sec"] >= vd["end_sec"]:
            vd["end_sec"] = vd["start_sec"] + 3.0

        conn.execute("""
            INSERT OR REPLACE INTO audio_timestamps
                (verse_id, book_id, chapter, start_sec, end_sec, word_timestamps, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vd["id"], vd["book"], vd["chapter"],
            round(vd["start_sec"], 2), round(vd["end_sec"], 2),
            json.dumps(v_ts[vd["id"]], ensure_ascii=False),
            source_file
        ))
        count += 1

    conn.commit()
    conn.close()

    # Print summary by chapter
    chapters = {}
    for vd in vdata:
        ch = vd["chapter"]
        if ch not in chapters:
            chapters[ch] = {"aligned": 0, "with_words": 0, "total": 0}
        chapters[ch]["total"] += 1
        if vd["start_sec"] >= 0:
            chapters[ch]["aligned"] += 1
        if len(v_ts[vd["id"]]) > 0:
            chapters[ch]["with_words"] += 1

    for ch in sorted(chapters.keys()):
        c = chapters[ch]
        print(f"  Chapter {ch:3d}: {c['aligned']}/{c['total']} aligned, {c['with_words']} with word ts")

    print(f"  Total: {count} verses aligned from {source_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Align audio timestamps to verses")
    parser.add_argument("--book", default="", help="Book ID (gen, exo, isa, etc.)")
    parser.add_argument("--chapter", type=int, default=0, help="Specific chapter (optional)")
    parser.add_argument("--force", action="store_true", help="Force re-transcribe")
    parser.add_argument("--list", action="store_true", help="List available audio files")
    args = parser.parse_args()

    if args.list:
        print("Available audio files:")
        for book, fname in sorted(BOOK_MAP.items()):
            if fname:
                path = f"data/audio/raw/{fname}"
                exists = os.path.exists(path)
                size = os.path.getsize(path) / 1e6 if exists else 0
                print(f"  {book:5s} → {fname:30s} {'⬢' if exists else '○'} {size:.0f} MB" if exists else f"  {book:5s} → {fname:30s} ○ pending")
        return

    if not args.book:
        print("Specify --book (e.g., --book gen) or use --list to see available")
        return

    audio_file = BOOK_MAP.get(args.book)
    if not audio_file:
        print(f"Unknown book: {args.book}")
        return

    audio_path = f"data/audio/raw/{audio_file}"
    if not os.path.exists(audio_path):
        print(f"Audio not found: {audio_path}")
        return

    align_book(audio_path, audio_file, args.book,
               chapter_filter=args.chapter if args.chapter > 0 else None,
               force_transcribe=args.force)


if __name__ == "__main__":
    main()
