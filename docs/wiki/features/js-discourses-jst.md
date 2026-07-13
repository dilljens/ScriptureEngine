# JS Discourses & JST Integration

Joseph Smith discourses corpus and full Joseph Smith Translation version.

## Overview

Two major imports:
1. **JS Discourses**: 945 texts from the TEV001-945 PDF corpus (Joseph Smith teachings and discourses)
2. **JST Version**: Full Joseph Smith Translation ingested as a selectable Bible version with 8,796 typed connections

## JS Discourses

| Metric | Value |
|--------|-------|
| Source | TEV001-945 PDF corpus |
| Texts imported | 945 |
| Import script | `scripts/import_js_discourses.py` |
| API endpoint | `GET /api/v1/js/discourses` |

### Architecture

```
PDF corpus (TEV001-945)
        │
        ▼
scripts/import_js_discourses.py
        │
        ▼
SQLite → js_sources table
        │
        ▼
web/routes/js_discourses.py → HTTP API
```

## JST Version

| Metric | Value |
|--------|-------|
| Source | Full Joseph Smith Translation text |
| Connection type | `jst_change` + `jst_addition` |
| Total connections | 8,796 |
| Import script | `scripts/import_jst_version.py` |

### Connection Types

| Type | Description | Count |
|------|-------------|-------|
| `jst_change` | JST modifies existing verse text | ~6,500 |
| `jst_addition` | JST adds new text not in original | ~2,300 |

## Key Tools

| Tool | Description |
|------|-------------|
| `python3 scripts/import_js_discourses.py` | Import JS discourses PDF corpus |
| `python3 scripts/import_jst_version.py` | Import JST as Bible version + connections |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/import_js_discourses.py` | Discourse PDF ingest |
| `scripts/import_jst_version.py` | JST text ingest + connection generation |
| `web/routes/js_discourses.py` | JS discourses API routes |

## Path Scope

- `scripts/import_js_discourses.py` — Discourse import
- `scripts/import_jst_version.py` — JST import
- `web/routes/js_discourses.py` — API
