# Memory Systems Improvement Plan

Goal: Execute 6 work streams to refresh all three memory systems (codebase-memory-mcp, knowledge store, wiki) with accurate data.

## Tracks

### Track A: Refresh Aging Wiki Files `[ ]`
- A1: `_standards.md` — 27d stale, update Python version, tool/generator counts, patterns
- A2: `features/lib-core.md` — 22d stale, add missing modules, update tool count (60)
- A3: `features/generators.md` — 20d stale, update to 45 generators, add new scripts
- A4: `features/mcp-server.md` — 22d stale, list all 60 tools, add new tool groups

### Track B: Re-index Codebase Memory `[ ]`
- B1: Force re-index in fast mode
- B2: Verify index completeness

### Track C: Run Health + Stats Diagnostic `[ ]`
- C1: Run memory-health dashboard
- C2: Run memory-stats analysis
- C3: Record baseline metrics

### Track D: Consolidate Orphaned Facts `[ ]`
- D1: Extract SE-related facts from external stores
- D2: Re-store in scriptureengine knowledge store
- D3: Forget from source stores

### Track E: Improve `/memory-update` Command `[ ]`
- E1: Rewrite as prescriptive 4-phase process

### Track F: Install Wiki Drift Hook `[ ]`
- F1: Create post-commit hook checking code→wiki sync
