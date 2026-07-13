"""Audio playback + read-along routes."""
import io
import json
import os as audio_os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

router = APIRouter()

# Audio sources available (also referenced from server.py)
AUDIO_SOURCES = ["schmueloff", "tts"]

BASE_DIR = Path(__file__).parent.parent.parent
RAW_AUDIO_DIR = BASE_DIR / "data" / "audio" / "raw"
AUDIO_DIR = BASE_DIR / "data" / "audio" / "verses"
ALIGN_DIR = BASE_DIR / "data" / "audio" / "alignments"


def get_db():
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()


@router.get("/api/v1/read-along/{verse_id:path}")
def get_read_along_data(verse_id: str):
    import re as _re
    vid = verse_id.strip("/").replace(":", ".").replace(" ", ".").lower()
    m = _re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', vid)
    if m:
        vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}"

    conn = get_db()
    verse = conn.execute(
        "SELECT text_hebrew, text_english, text_greek, book_id, chapter, verse FROM verses WHERE id=?",
        (vid,)).fetchone()

    if not verse:
        conn.close()
        raise HTTPException(404, f"Verse not found: {vid}")

    ts_row = conn.execute(
        "SELECT start_sec, end_sec, word_timestamps, source_file FROM audio_timestamps WHERE verse_id=?",
        (vid,)).fetchone()

    audio_source = "schmueloff" if ts_row else "tts"
    audio_url = f"/api/v1/audio/play/{vid}"

    word_ts = []
    if ts_row:
        try:
            word_ts = json.loads(ts_row["word_timestamps"])
        except (json.JSONDecodeError, TypeError):
            word_ts = []

    word_count = len(word_ts)
    duration = 0.0
    if word_ts:
        duration = round(word_ts[-1]["end"] - word_ts[0]["start"], 3)

    raw_audio_url = None
    if ts_row and ts_row["source_file"]:
        raw_audio_url = f"/api/v1/audio/play-raw/{ts_row['source_file']}?start={ts_row['start_sec']}&end={ts_row['end_sec']}"

    result = {
        "verse": vid, "text_hebrew": verse["text_hebrew"],
        "text_english": verse["text_english"], "text_greek": verse["text_greek"],
        "audio_url": audio_url, "word_timestamps": word_ts,
        "word_count": word_count, "duration": duration, "audio_source": audio_source,
    }
    if ts_row:
        result["segment_start"] = ts_row["start_sec"]
        result["segment_end"] = ts_row["end_sec"]
        result["raw_audio_url"] = raw_audio_url

    conn.close()
    return {"ok": True, "data": result}


@router.get("/api/v1/audio/play-raw/{filename:path}")
def play_raw_audio_segment(filename: str, start: float = 0.0, end: float = 30.0):
    safe_name = audio_os.path.basename(filename)
    audio_file = RAW_AUDIO_DIR / safe_name
    if not audio_file.exists():
        raise HTTPException(404, f"Raw audio not found: {safe_name}")

    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
        "-i", str(audio_file), "-f", "wav",
        "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", "pipe:1"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        return StreamingResponse(
            io.BytesIO(proc.stdout),
            media_type="audio/wav",
            headers={"Content-Disposition": f'inline; filename="{safe_name}_{start:.0f}_{end:.0f}.waw"'}
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Audio extraction timed out") from e


@router.get("/api/v1/audio/play/{verse_id:path}")
def play_verse_audio(verse_id: str):
    vid = verse_id.strip("/")
    for suffix in ['_schmueloff', '_cloned', '']:
        audio_file = AUDIO_DIR / f"{vid}{suffix}.wav"
        if audio_file.exists():
            return FileResponse(str(audio_file), media_type="audio/wav", filename=f"{vid}.wav")
    raise HTTPException(404, f"Audio not found: {vid}")


@router.get("/api/v1/audio/align/{verse_id:path}")
def get_verse_alignment(verse_id: str):
    vid = verse_id.strip("/")
    for suffix in ['_schmueloff', '_cloned', '']:
        align_file = ALIGN_DIR / f"{vid}{suffix}.json"
        if align_file.exists():
            with open(align_file) as f:
                data = json.load(f)
            return {"ok": True, "data": data}
    raise HTTPException(404, f"Alignment not found: {vid}")
