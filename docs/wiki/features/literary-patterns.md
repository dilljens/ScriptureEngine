# Literary Pattern Detection

Multi-verse literary structure analysis — chiasms, inclusios, mukdam u'meuchar, and other Hebrew literary forms.

## Overview

A pipeline of algorithmic detectors that scan entire books for literary structures and register them as connections in the graph.

## Detection Types

| Pattern | Description | Tool/Script |
|---------|-------------|-------------|
| **Chiasm** | A-B-C-C'-B'-A' mirror structure | `scripts/detect_chiasms.py` → v3 final |
| **Inclusio** | Same phrase opening and closing a literary unit | Part of all-pattern pipeline |
| **Mukdam u'Meuchar** | Hebrew "early/late" — chronological reordering for thematic effect | `scripts/detect_mukdam_umeuchar.py` |
| **All-pattern** | Unified scan for multiple pattern types | `scripts/detect_all_patterns.py` |

## Architecture

```
Scripts (offline detection)
        │
        ├── detect_chiasms.py         → Algorithmic chiasm candidate detection
        ├── detect_chiasms_v2.py      → Refined scoring
        ├── detect_chiasms_v3.py      → Final version with confidence calibration
        ├── detect_chiasms_final.py   → Production-ready output
        ├── detect_mukdam_umeuchar.py → Chronological reordering detection
        └── detect_all_patterns.py    → Unified pipeline (chiasm + inclusio + more)
                │
                ▼
        connection graph
                │
                ▼
        `section_compare` tool    → Verify chiasm candidates
        `section_compare` tool    → Word count + keyword overlap
        `chiasm_scan` tool        → Algorithmic multi-chapter scan
```

## Key Tools

| Tool | Purpose |
|------|---------|
| `python3 tools/word_counts.py` | Per-chapter word count distribution |
| `python3 tools/chiasm_scan.py` | Multi-chapter chiastic candidate detection |
| `python3 tools/section_compare.py` | Compare two sections for mirror structure |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/detect_chiasms.py` → v3 | Multi-pass chiasm detection |
| `scripts/detect_mukdam_umeuchar.py` | Mukdam u'Meuchar detector |
| `scripts/detect_all_patterns.py` | Unified pattern detection pipeline |

## Testing

- Results validated via `section_compare` for word count and keyword overlap
- Cross-check against `known_patterns` to avoid duplicates
- Novel discoveries saved via `pattern_ingest`

## Path Scope

- `scripts/detect_chiasms*.py` — Chiasm detectors
- `scripts/detect_mukdam_umeuchar.py` — Mukdam detector
- `scripts/detect_all_patterns.py` — Unified pipeline
- `tools/*` — CLI tools for inspection
