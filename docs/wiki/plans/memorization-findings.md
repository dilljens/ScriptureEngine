# Findings — ScriptureEngine Online Not Working

## Quality Baseline
<!-- Run sentrux_scan before/after for quality tracking -->

## Summary

The ScriptureEngine frontend cannot build or run because several "generated" source files are listed in `.gitignore` and only exist on the other development laptop. Additionally, `App.jsx` has two bugs (missing import, undefined function) and deployment docs point to a stale IP.

## Issues Found

### P0 — Build-Breaking

1. **Missing `frontend/index.html`** — Vite requires this as entry point. Without it, `npm run dev` and `npm run build` both fail immediately.

2. **Missing `frontend/src/main.jsx`** — React DOM mount point. Imports `<App />` and renders to `#root`.

3. **Missing `frontend/src/index.css`** — Tailwind CSS directives (`@tailwind base/components/utilities`). Without it, all Tailwind classes are undefined.

4. **Missing `frontend/src/settings.jsx`** — Imports in `App.jsx` line 4:
   ```jsx
   import { SettingsProvider, useSettings, useHistory } from './settings.jsx'
   ```
   None of these exports exist. `SettingsProvider` wraps the entire app, so nothing renders.

5. **Missing `frontend/src/progress.jsx`** — Imports in `App.jsx` line 5:
   ```jsx
   import { ProgressProvider, useProgress } from './progress.jsx'
   ```

6. **Missing `frontend/src/useAgentControl.js`** — Imports in `App.jsx` line 35:
   ```jsx
   import useAgentControl from './useAgentControl'
   ```
   Called on line 383: `useAgentControl({...})` — would throw at runtime.

7. **`MemorizeIcon` used but not imported** — Line 1003 uses `<MemorizeIcon />` but it's not listed in the icon import block (lines 12-19). Vite would error on build.

8. **`openMemorizeTab` undefined** — Line 1002: `onClick={() => openMemorizeTab()}` — no function with this name exists in App.jsx. Would throw TypeError at runtime.

### P1 — Deployment

9. **Stale IP in docs** — `docs/deployment.md`, `MEMORY.md`, and comment in `scripts/deploy.sh` all reference old Hetzner IP `46.224.171.239`. Deploy script's actual `HOST` variable uses `40.160.241.74` (the new VPS). 8 total occurrences to update.

### P2 — Infrastructure

10. **`frontend/node_modules/` not installed** — Need `npm install` before building.

11. **`data/processed/scripture.db` doesn't exist** — Database needs to be created via `./run.sh ingest` or copied from the other machine.

12. **No `.env` file** — `DEEPSEEK_API_KEY` and potentially other env vars missing.

## Root Cause

The files in items 1-6 are listed in `.gitignore` under a comment header:
```
# Generated frontend files
frontend/src/cache.js
frontend/src/bookNames.js
frontend/src/utils.js
frontend/src/debug.js
frontend/src/settings.jsx
frontend/src/progress.jsx
frontend/src/useAgentControl.js
frontend/src/main.jsx
frontend/src/index.css
```

These were never committed, existing only on the other development laptop. The project was likely initialized with a one-time generation script or manual creation that wasn't tracked.

Items 7-8 are code bugs introduced in commits that added the Memorize tab without completing the import/definition wiring.
