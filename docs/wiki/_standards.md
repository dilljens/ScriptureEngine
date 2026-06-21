# Codebase Standards

## Rules

### Python
- Use Python 3.13+ type hints on all function signatures
- `snake_case` for functions and variables, `PascalCase` for classes
- Module-level docstrings in all `.py` files
- Prefer `pathlib.Path` over `os.path`
- Use `sys.path.insert(0, ...)` pattern for relative imports (no pip install -e)
- Never use `from x import *`

### Database
- All schema changes go through `lib/db.py` (`SCHEMA_SQL` constant)
- Add columns via `ALTER TABLE`, never drop/recreate tables with data
- Use `ON CONFLICT DO UPDATE` for upserts
- WAL mode enabled by default
- JSON metadata columns for extensibility

### API Tools
- Every tool function signature: `def my_tool(conn, **kwargs) -> dict`
- Register in `lib/api/__init__.py` with JSON Schema for params
- Docstring becomes the tool description
- Return plain dicts (not JSON-RPC or HTTP wrapped)

### Connection Generators
- Every generator exports `def run(conn, book_ids=None) -> int`
- Register in `generators/__init__.py` with metadata
- Do NOT commit inside the generator — caller handles commit
- Use `add_connection()` from `lib/db.py` for inserts

### Agent-Driven Data
The agent (this coding session) reads scripture text directly and writes data. No external API, no cost.

- Reuse infrastructure from `data/agent_connections/` pattern
- Pre-filter candidates with SQL queries, then read verse texts with the Read tool
- Judge each connection systematically: is it real? why? what does the text actually say?
- Write judgment JSON files to `data/agent_connections/{type}_judgments.json`
- Always set `discovered_by='ai'` on agent-generated data
- Always include a `reasoning` field in metadata — this is the product
- Start connections at low confidence (0.3-0.5), let confirmation system promote

### Anti-Hallucination
- Never override higher-confidence human or algorithmic connections
- New agent-generated connections start as `quality_level='speculative'`
- Distinguish between what the text says vs. what interpreters added
- Label linguistic vs. interpretive connections clearly
- The `null_text.py` controls validate against null-text baselines
- P-values must meet significance thresholds before promotion

## Practices

- Connection graph uses "compute once, cache forever" pattern
- RAM cache at startup — load all passage guides for sub-ms responses
- Pre-compute materialized views (passage_guides) rather than live joins
- All tool logic lives in `lib/api/*.py` — both MCP and HTTP consume the same registry
- Study guides (angel_of_the_lord, covenant, etc.) use the guided study framework

## Patterns

### Adding a New Tool
1. Implement the function in `lib/api/<module>.py`
2. Import and register it in `lib/api/__init__.py`
3. It's immediately available as MCP tool + HTTP API endpoint

### Adding a New Connection Generator
1. Implement `run(conn, book_ids=None) -> int` in `generators/*.py`
2. Add definition to `GENERATOR_DEFS` in `generators/__init__.py`
3. Run via: `python3 scripts/generate_connections.py --name "My Generator"`

### Adding Agent-Driven Classification
1. Pre-filter candidates with SQL: query the DB for candidate verse pairs
2. Read verse texts: use the Read tool to examine source + target texts
3. Judge systematically: is this connection real? what does the text say?
4. Write judgment JSON to `data/agent_connections/{type}_judgments.json`
5. Apply to DB: INSERT INTO connections with `discovered_by='ai'`
6. Verify: check DB counts match expectations

## Enforcement

- `./run.sh test` — smoke tests
- git hooks — installed via install-wiki-hooks (post-commit staleness check)
- Type hints are advisory (no mypy in CI yet)
