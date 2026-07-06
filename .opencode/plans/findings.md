# Findings — Memorization Module for ScriptureEngine

## Architecture Decisions

### Why Go Microservice Instead of Python
ScriptureEngine's backend is Python/FastAPI, but memorization is delegated to a Go microservice because:
1. **FSRS algorithm** — Go is excellent for algorithmic math with no GC pauses
2. **ComfyUI proxy** — Go's stdlib HTTP client is production-grade
3. **Single binary** — easy to deploy alongside the Python app
4. **No runtime dependency** — user doesn't need Python venv for the memorization module

### Why FSRS Instead of SM-2
FSRS (Free Spaced Repetition Scheduler) is the modern standard used by Anki 23.10+. It adapts to each user's memory patterns with 4 learned parameters. SM-2 is simpler but less efficient (more reviews for same retention). The user explicitly requested FSRS.

### Why ComfyUI Instead of A1111
ComfyUI has the best API for programmatic use (native REST + WebSocket), best VRAM management (`--lowvram`), and workflows can be version-controlled as JSON. A1111 development has stalled.

### AI Model Recommendation for 6GB VRAM
- **Primary:** SD 3.5 Medium (FP16, fits at 6GB, good text rendering for scripture)
- **Fallback:** SD 1.5 + Realistic Vision V5.1 (guaranteed fit, rich ecosystem for compositing)
- **Optimizations:** `--lowvram --force-fp16` + xformers + tiled VAE decode
- **Two-stage pipeline:** txt2img (concept) → img2img inpainting (composite into palace photo)
- **Expected times:** 4-8 sec per concept image, 2-4 sec per composite

## ScriptureEngine Architecture (as discovered)

### Frontend
- React 19 + Vite 6 + Tailwind CSS 3
- **No React Router** — custom tab system via React Context + `useReducer`
- View hierarchy: `tiles → library → work → book → chapter` (+ `chat`, `graph`, `study`)
- Navigation via up/down/left/right commands
- State persisted to localStorage under `scripture_tabs`
- API client: `frontend/src/api.js` — `fetchJSON` wrapper, all calls to `/api/v1/*`
- Vite proxy in dev: `/api` → `http://localhost:8002`

### Backend
- Python 3 + FastAPI + Uvicorn
- Single monolithic file: `web/server.py` (~4,000 lines)
- RAM cache: loads all verse data at startup (~500MB)
- SQLite database at `data/processed/scripture.db` with FTS5, sqlite-vec, WAL mode
- 42K+ verses, 218K+ connections, gematria, lexicon, assessment engine
- Tool registry pattern: tools registered in `lib/api/__init__.py` auto-exposed as HTTP + MCP + CLI

### Assessment Engine (Pre-existing)
- `lib/assessment/` directory exists but no frontend UI for memorization
- `knowledge_items` table with Bloom's taxonomy levels
- No spaced repetition or flashcard system in the frontend

## Research Sources

### Memorization Techniques
1. **FSRS Algorithm** — Open Spaced Repetition Scheduler (Anki 23.10+)
2. **Active Recall / Testing Effect** — Roediger & Karpicke (2006), Psychological Science
3. **Spaced Repetition** — Cepeda et al. (2006), Dunlosky et al. (2013)
4. **Method of Loci** — Used since ancient Greece, dominant memory athlete technique
5. **First-Letter Method** — Cued recall variant used by ScriptureTyper, Bible Memory App
6. **Production Effect** — Eghbaria-Ghanamah et al. (2021) — saying aloud > silent reading
7. **Quran Hifz traditions** — 3×3 method, 3-10 method, 6-4-4-6 method
8. **Tibetan Buddhist monastic memorization** — chanting with body rocking, aural-only
9. **Medieval Christian monastic** — Lectio Divina, memory palaces, chant

### AI Image Generation for 6GB VRAM
- **ComfyUI** is the recommended backend (best API, best VRAM, fastest updates)
- **SD 3.5 Medium** fits at 6GB FP16 at 512×768
- **SD 1.5 + Realistic Vision** is the safest fallback with best ecosystem
- Two-stage pipeline: txt2img concept → img2img composite into palace photo
- Docker container: `ai-dock/comfyui` with GPU passthrough

## Quality Baseline

No sentrux scan performed — this is a new module being added to an existing project. The project's existing quality will be measured before the first code changes.
