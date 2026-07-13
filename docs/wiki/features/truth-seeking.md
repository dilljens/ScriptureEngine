# Truth-Seeking Framework

Systematic distinction between textual truth (what scripture actually says) and interpretive tradition (what later commentators added).

## Overview

The engine's core principle: **what the text actually says** is the primary datum. Interpretive traditions (Rashi, Calvin, Talmud, midrash, etc.) are valuable secondary sources but must be clearly labeled as such.

## Components

### Disagreements System
Cross-references contradictory readings across traditions:

| Feature | Description |
|---------|-------------|
| `scripture_disagreements` tool | Get contradictory readings for a verse |
| `scripts/seed_disagreements.py` | Seed data with known interpretive disagreements |
| `scripture_consensus` tool | Get ecumenical consensus data (which traditions engage with a verse) |

### Connection Labeling
Every connection in the graph carries tradition labels:

| Label | Meaning |
|-------|---------|
| `none` | Algorithmic/linguistic (52% of connections) |
| `multiple` | Multiple traditions agree (23%) |
| `jewish` | Jewish interpretive tradition (22%) |
| `christian` | Christian interpretive tradition (2%) |
| `lds` | Latter-day Saint interpretive tradition (2%) |

### Hermeneutical Framework
The engine uses PaRDeS levels to separate interpretive layers:

| Level | Name | What it captures |
|-------|------|-----------------|
| P'shat | פשט | Simple/literal — what the text says |
| Remez | רמז | Hinted — what the text alludes to |
| Drash | דרש | Inquired — cross-canon connections |
| Sod | סוד | Hidden — deep structural/numerical patterns |

## Source Provenance

Every connection records its source:

- **discovered_by**: 'algorithm' (generator), 'ai' (agent judgment), or 'human' (curated)
- **tradition**: which interpretive tradition(s) the connection belongs to
- **reasoning**: human-readable explanation (required for AI-generated connections)

## Key Files

| File | Purpose |
|------|---------|
| `lib/controls/` | Anti-hallucination (p-values, null-text, preregistration) |
| `lib/connections/pardes.py` | PaRDeS level classification |
| `lib/connections/types.py` | Connection type definitions with tradition metadata |
| `scripts/seed_disagreements.py` | Interpretive disagreement seed data |

## Key Tools

| Tool | Description |
|------|-------------|
| `scripture_disagreements` | Get interpretive disagreements for a verse |
| `scripture_consensus` | Get ecumenical consensus data |
| `scripture_sources` | Get source provenance for a verse's connections |
| `scripture_pardes` | View connections grouped by PaRDeS level |

## Path Scope

- `lib/controls/` — Anti-hallucination infrastructure
- `lib/connections/pardes.py` — PaRDeS classification
- `lib/connections/types.py` — Types with tradition metadata
- `scripts/seed_disagreements.py` — Seed data
