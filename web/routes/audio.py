"""Audio playback + read-along routes."""
import io
import json
import os as audio_os
import subprocess
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

router = APIRouter()

# Audio sources available (also referenced from server.py)
AUDIO_SOURCES = ["shmuelof", "tts"]

BASE_DIR = Path(__file__).parent.parent.parent
RAW_AUDIO_DIR = BASE_DIR / "data" / "audio" / "raw"
AUDIO_DIR = BASE_DIR / "data" / "audio" / "verses"
ALIGN_DIR = BASE_DIR / "data" / "audio" / "alignments"


def get_db():
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()


def _inline_disposition(name: str, fallback: str = "audio") -> str:
    """Content-Disposition header safe for non-ASCII filenames.

    Headers are latin-1, so Hebrew/Arabic names must be carried via RFC 5987
    ``filename*`` (UTF-8 percent-encoded) with an ASCII ``filename`` fallback.
    """
    ascii_name = name.encode("ascii", "replace").decode("ascii") or fallback
    return f'inline; filename="{ascii_name}.wav"; filename*=UTF-8\'\'{quote(name)}.wav'


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

    audio_source = "shmuelof" if ts_row else "tts"
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


def _normalize_hebrew_word(w: str) -> str:
    """Normalize an OSHB word for matching: strip the '/' morph separator and
    niqqud/cantillation marks, and map final forms to their regular letters."""
    import re as _re
    w = _re.sub(r"[\u0591-\u05C7]", "", w or "")   # niqqud + cantillation
    w = w.replace("/", "").strip()
    w = w.replace("ך", "כ").replace("ם", "מ").replace("ן", "נ") \
         .replace("ף", "פ").replace("ץ", "צ")
    return w


@router.get("/api/v1/hebrew/word-audio/{verse_id:path}")
def get_word_audio(verse_id: str, word: str = ""):
    """Play the audio slice for one word in an aligned verse.

    Finds the word's [start, end] in audio_timestamps.word_timestamps (matching
    by normalized Hebrew form), then streams that slice from the source file.
    This is verse-level playback of the licensed recording (in-browser slice),
    not a redistributed clip — the ND-safe use.
    """
    import re as _re
    vid = verse_id.strip("/").replace(":", ".").replace(" ", ".").lower()
    m = _re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', vid)
    vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}" if m else vid

    target = _normalize_hebrew_word(word)
    if not target:
        raise HTTPException(400, "word required")

    conn = get_db()
    ts_row = conn.execute(
        "SELECT source_file, word_timestamps FROM audio_timestamps WHERE verse_id=?",
        (vid,)).fetchone()
    conn.close()
    if not ts_row or not ts_row["source_file"]:
        raise HTTPException(404, f"No alignment for verse: {vid}")

    try:
        words = json.loads(ts_row["word_timestamps"] or "[]")
    except (json.JSONDecodeError, TypeError):
        words = []

    match = None
    for w in words:
        if _normalize_hebrew_word(w.get("word", "")) == target:
            match = w
            break
    if not match:
        raise HTTPException(404, f"Word '{word}' not found in aligned {vid}")

    start, end = float(match["start"]), float(match["end"])
    src = RAW_AUDIO_DIR / ts_row["source_file"]
    if not src.exists():
        alt = AUDIO_DIR / ts_row["source_file"]
        if not alt.exists():
            raise HTTPException(404, f"Source audio not found: {ts_row['source_file']}")
        src = alt

    # small padding so the word isn't clipped at the boundary
    pad = 0.03
    cmd = [
        "ffmpeg", "-y", "-ss", str(max(0, start - pad)), "-to", str(end + pad),
        "-i", str(src), "-f", "wav", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1", "pipe:1",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Audio extraction timed out") from e
    if proc.returncode != 0 or not proc.stdout:
        raise HTTPException(500, f"ffmpeg slice failed for {vid}")
    return StreamingResponse(
        io.BytesIO(proc.stdout),
        media_type="audio/wav",
        headers={"Content-Disposition": f'inline; filename="{vid}.wav"'},
    )


@router.get("/api/v1/audio/letter/{letter_id}")
def play_letter_audio(letter_id: str):
    """Serve pre-generated Hebrew letter audio."""
    safe_name = audio_os.path.basename(letter_id)
    letter_file = BASE_DIR / "data" / "audio" / "letters" / f"{safe_name}.wav"
    if not letter_file.exists():
        raise HTTPException(404, f"Letter audio not found: {letter_id}")
    return FileResponse(str(letter_file), media_type="audio/wav",
                        headers={"Content-Disposition": _inline_disposition(safe_name)})


@router.get("/api/v1/audio/word/{node_id}")
def play_word_audio(node_id: str):
    """Serve pre-generated Hebrew word/phrase/root audio (kokoro TTS).

    The /hebrew/audio/{word} lookup resolves a Hebrew word to a node and returns
    this URL; the file lives in data/audio/words/{node_id}.wav.
    """
    safe_name = audio_os.path.basename(node_id)
    word_file = BASE_DIR / "data" / "audio" / "words" / f"{safe_name}.wav"
    if not word_file.exists():
        raise HTTPException(404, f"Word audio not found: {node_id}")
    return FileResponse(str(word_file), media_type="audio/wav",
                        headers={"Content-Disposition": _inline_disposition(safe_name)})


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
    for suffix in ['_shmuelof', '_cloned', '']:
        audio_file = AUDIO_DIR / f"{vid}{suffix}.wav"
        if audio_file.exists():
            return FileResponse(str(audio_file), media_type="audio/wav", filename=f"{vid}.wav")
    raise HTTPException(404, f"Audio not found: {vid}")


@router.get("/api/v1/audio/align/{verse_id:path}")
def get_verse_alignment(verse_id: str):
    vid = verse_id.strip("/")
    for suffix in ['_shmuelof', '_cloned', '']:
        align_file = ALIGN_DIR / f"{vid}{suffix}.json"
        if align_file.exists():
            with open(align_file) as f:
                data = json.load(f)
            return {"ok": True, "data": data}
    raise HTTPException(404, f"Alignment not found: {vid}")
