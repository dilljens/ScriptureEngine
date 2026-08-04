#!/usr/bin/env bash
# Sync Hebrew audio data (alignment + TTS wavs + raw MP3s) to production VPS.
#
# The 2.2GB scripture.db ships via GitHub Releases (docs/deployment.md), but
# re-releasing it for every alignment run is heavy. This script does a SURGICAL
# sync of just the audio-related data:
#   1. audio_timestamps + verse_boundaries_stage tables (the alignment) — SQL dump
#   2. data/audio/raw/*.mp3  — real Shmuelof verse audio
#   3. data/audio/words/ + letters/ — Kokoro TTS word audio
#   4. data/audio/alignments/ — alignment sidecars
#
# Usage:
#   bash scripts/sync_audio_data.sh            # sync to production VPS
#   bash scripts/sync_audio_data.sh --dry-run  # show what would transfer
#
# Prereqs: SSH key for ubuntu@40.160.241.74; sqlite3 on both ends.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST="ubuntu@40.160.241.74"
REMOTE_DIR="/var/www/scripture"
LOCAL_DB="data/processed/scripture.db"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

DRY=""
[ "${1:-}" = "--dry-run" ] && DRY="--dry-run"

echo "=== Sync Hebrew audio data to $HOST ==="

# ── 1. DB tables: export audio_timestamps + verse_boundaries_stage ──
echo "[1/4] Exporting alignment tables..."
sqlite3 "$LOCAL_DB" ".dump audio_timestamps" > "$TMP/audio_timestamps.sql"
sqlite3 "$LOCAL_DB" ".dump verse_boundaries_stage" > "$TMP/verse_boundaries_stage.sql"
echo "  audio_timestamps:    $(du -h "$TMP/audio_timestamps.sql" | cut -f1)"
echo "  verse_boundaries_stage: $(du -h "$TMP/verse_boundaries_stage.sql" | cut -f1)"

if [ -n "$DRY" ]; then
  echo "  (dry-run) would transfer + apply SQL dumps"
else
  scp "$TMP/audio_timestamps.sql" "$TMP/verse_boundaries_stage.sql" "$HOST:/tmp/"
  ssh "$HOST" bash -s <<'EOF'
set -e
DB=/var/www/scripture/data/processed/scripture.db
# Backup the current DB first (timestamped, kept alongside)
BK="$DB.bak-$(date +%Y%m%d-%H%M%S)"
cp "$DB" "$BK"
echo "  backed up DB -> $(basename "$BK")"
# Replace the two tables (drop + recreate from our dump)
sqlite3 "$DB" "DROP TABLE IF EXISTS audio_timestamps; DROP TABLE IF EXISTS verse_boundaries_stage;"
sqlite3 "$DB" < /tmp/audio_timestamps.sql
sqlite3 "$DB" < /tmp/verse_boundaries_stage.sql
rm -f /tmp/audio_timestamps.sql /tmp/verse_boundaries_stage.sql
# Verify
GEN=$(sqlite3 "$DB" "SELECT COUNT(*) FROM audio_timestamps WHERE book_id='gen' AND json_array_length(word_timestamps)>3;")
echo "  gen verses with word timestamps: $GEN"
EOF
fi

# ── 2. Raw Shmuelof MP3s (real verse audio) ──
echo "[2/4] Syncing raw audio MP3s (~200MB)..."
if [ -d data/audio/raw ]; then
  ssh "$HOST" "mkdir -p $REMOTE_DIR/data/audio/raw"
  rsync -avz $DRY --exclude 'genesis_chapters' data/audio/raw/ "$HOST:$REMOTE_DIR/data/audio/raw/"
else
  echo "  (no data/audio/raw locally)"
fi

# ── 3. Kokoro TTS word audio ──
echo "[3/4] Syncing Kokoro word/letter audio..."
for d in words letters; do
  if [ -d "data/audio/$d" ]; then
    ssh "$HOST" "mkdir -p $REMOTE_DIR/data/audio/$d"
    rsync -avz $DRY "data/audio/$d/" "$HOST:$REMOTE_DIR/data/audio/$d/"
  else
    echo "  (no data/audio/$d locally)"
  fi
done

# ── 4. Alignment sidecars ──
echo "[4/4] Syncing alignment sidecars..."
if [ -d data/audio/alignments ]; then
  ssh "$HOST" "mkdir -p $REMOTE_DIR/data/audio/alignments"
  rsync -avz $DRY data/audio/alignments/ "$HOST:$REMOTE_DIR/data/audio/alignments/"
else
  echo "  (no data/audio/alignments locally)"
fi

# ── restart ──
if [ -z "$DRY" ]; then
  echo "Restarting scripture-api..."
  ssh "$HOST" "sudo systemctl restart scripture-api"
fi

echo "=== Done ==="
echo "Verify: ssh $HOST 'systemctl is-active scripture-api'"
