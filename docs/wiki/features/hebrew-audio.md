# Hebrew Audio System

PassageReader, DailyVerse, AudioReview — Hebrew audio playback with synchronized text.

## Overview

The Hebrew Audio system integrates **Schmueloff recordings** (Hebrew Genesis 1 audio) into three learning experiences:

1. **PassageReader** — Read-along mode: verse text highlights in sync with audio playback
2. **DailyVerse** — Daily Hebrew verse widget with one-tap audio
3. **AudioReview** — Listen-and-type: user hears Hebrew audio, types what they hear

## Architecture

```
Audio files (Schmueloff .mp3)
        │
        ▼
web/routes/audio.py
        │
        ├── GET /api/v1/audio/play         → Stream Hebrew audio segment
        └── GET /api/v1/hebrew/dailyverse   → Daily verse + audio URL
                │
                ▼
frontend (React)
        ├── PassageReader component  → Verse text + audio sync
        ├── DailyVerse widget        → Today's verse + play button
        └── AudioReview tab          → Listen → type → verify
```

## Key Files

| File | Purpose |
|------|---------|
| `web/routes/audio.py` | Audio streaming endpoint (124 lines) |
| `frontend/src/components/PassageReader.jsx` | Read-along synchronized text |
| `frontend/src/components/DailyVerse.jsx` | Daily verse widget |
| `frontend/src/components/AudioReview.jsx` | Listen-and-type review |

## Audio Sources

- **Schmueloff recordings**: Hebrew audio for Genesis 1, sourced from Schmueloff.com
- Format: MP3, served via streaming endpoint
- Verse-level segmentation aligned to MT verse divisions

## Testing

- Audio endpoint tested via curl/HTTP
- Frontend audio sync tested in Playwright E2E

## Path Scope

- `web/routes/audio.py` — API route
- `frontend/src/components/*Audio*.*` — UI components
- `frontend/src/components/PassageReader.*` — Read-along
