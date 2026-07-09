# Scripture Knowledge Engine — Standards

## Rules — What you must NEVER do

1. Never treat English as the authoritative text for gematria — gematria only applies to Hebrew (and Greek).
2. Never claim a pattern is "confirmed" without noting discovery method (human/algorithm/AI).
3. Never delete or overwrite the raw data — always work from processed copies.
4. Never expose the database as a public API without authentication (copyright considerations).

## Practices

### Research workflow
- Start with Hebrew when analyzing OT passages
- Check all 11 connection layers for a complete picture
- Cross-reference findings with `scripture_intertext` to trace influence
- Note confidence levels on detected patterns

### Data integrity
- Always run `scripts/ingest.py` after adding new data sources
- Verify gematria values with manual calculation for key words
- Document the original source of every connection

## Patterns

### Reference format
- Verse IDs: `book.chapter.verse` (e.g., `gen.1.1`)
- Book IDs: 3-5 letter abbreviations (`gen`, `isa`, `1ne`, `dc1`)
- All lower case, no spaces

### Gematria systems
| System | Name | Usage |
|--------|------|-------|
| Standard | Mispar Hechrachi | Default system (א=1, ת=400) |
| Ordinal | Mispar Siduri | Letter position (א=1, ת=22) |
| Reduced | Mispar Katan | Standard reduced to single digit |
| Gadol | Mispar Gadol | Final forms have extended values |

### Connection discovery
| Source | Confidence | Usage |
|--------|-----------|-------|
| Human | 1.0 | Editorial annotations, known connections |
| Algorithm | 0.5–0.8 | Automated pattern detection |
| AI | 0.3–0.7 | AI-suggested connections (needs verification) |
