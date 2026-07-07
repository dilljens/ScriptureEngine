# Task Plan: Fix ScriptureEngine Online

## Overview

ScriptureEngine.org isn't working. Root cause: several generated frontend files are listed in `.gitignore` and only exist on the other development laptop. Additionally, there are import/runtime bugs in `App.jsx` and stale IP addresses in deployment docs.

## Tracks

### Track A — Restore Missing Generated Files
Create the 6 files that are gitignored and missing on this machine:

| File | Purpose |
|------|---------|
| `frontend/index.html` | Vite entry point (HTML shell) |
| `frontend/src/main.jsx` | React mount point |
| `frontend/src/index.css` | Tailwind imports |
| `frontend/src/settings.jsx` | SettingsProvider, useSettings, useHistory |
| `frontend/src/progress.jsx` | ProgressProvider, navigation history |
| `frontend/src/useAgentControl.js` | Agent control hook (`?agent=true`) |

**⏱ Timebox:** 20 min  
**✅ Checkpoint:** `ls frontend/index.html frontend/src/main.jsx frontend/src/index.css frontend/src/settings.jsx frontend/src/progress.jsx frontend/src/useAgentControl.js 2>&1 | grep -v "No such" | wc -l` returns 6  
**⚙ Fallback:** Ask user to copy files from the other laptop via USB/network

---

### Track B — Fix App.jsx Bugs
Two bugs preventing clean build:

1. **`MemorizeIcon`** — used in JSX (line 1003) but missing from the import block (lines 12-19)
2. **`openMemorizeTab`** — called in onClick (line 1002) but never defined

**⏱ Timebox:** 5 min  
**✅ Checkpoint:** `grep -c 'MemorizeIcon' frontend/src/App.jsx` = 2 (import + usage) AND `grep -c 'openMemorizeTab' frontend/src/App.jsx` = 2 (definition + usage)  
**⚙ Fallback:** Comment out the Memorize button

---

### Track C — Update Deployment Docs
Replace old Hetzner IP `46.224.171.239` with new VPS IP `40.160.241.74`:

| File | Occurrences |
|------|-------------|
| `docs/deployment.md` | 6 (lines 3, 30, 40, 75, 77, 86) |
| `MEMORY.md` | 1 (line 109) |
| `scripts/deploy.sh` | 1 (comment line 6) |

Also update the "Hetzner CX23" platform reference to the new provider if different.

**⏱ Timebox:** 5 min  
**✅ Checkpoint:** `grep -c '46.224.171.239' docs/deployment.md MEMORY.md scripts/deploy.sh` returns 0  
**⚙ Fallback:** Leave stale — deploy still works with current HOST variable

---

### Track D — Build, Ingest & Deploy

1. `cd frontend && npm install`
2. `npm run build` → produces `frontend/dist/`
3. Ensure `.env` exists with `DEEPSEEK_API_KEY="sk-..."`
4. Ingest database: `./run.sh ingest` (or copy scripture.db from other machine)
5. Run `./scripts/deploy.sh`
6. Verify: `curl -s https://scriptureengine.org/api/v1/health`

**⏱ Timebox:** 15 min  
**✅ Checkpoint:** `curl -s -o /dev/null -w "%{http_code}" https://scriptureengine.org/api/v1/health` returns 200  
**⚙ Fallback:** Test locally first (`python3 -m uvicorn web.server:app --port 8000`), then diagnose SSH/deploy

---

## Execution Order

Tracks A → B → C can run in any order (independent). D depends on A+B being done first.
