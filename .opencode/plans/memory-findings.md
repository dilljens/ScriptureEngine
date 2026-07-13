# Findings: Memory Systems Audit

## Drift Discovered

| Claim | Wiki Says | Actual | Delta |
|-------|-----------|--------|-------|
| MCP/HTTP tools | 23 (mcp-server.md) / 52 (AGENTS.md) | **60** | off by 8-37 |
| Registered generators | 36 | **45** | off by 9 |
| Generator contract docs | 36 listed | missing 9 generators from list |
| Connection layers | 10 layers, 88 types | **11 layers, 128 types** | - |
| Python version | 3.13 | 3.14 | - |
| Feature staleness | 4 pages AGING (20-27d) | content outdated | - |
| Git hooks | mentioned in _standards.md | NOT INSTALLED | - |
| TOOL_REGISTRY | lib/api/__init__.py | **60 tools confirmed** | - |
| GENERATOR_DEFS | generators/__init__.py | **45 generators confirmed** | - |

## Command Name Correction
- `/memory update` → `/memory-update` (kebab-case, no subcommands)
- All memory commands follow this pattern

## Orphaned Knowledge Stores
- `a307c770445015ef`: scripture-explorer project has SE-related facts
- `dc0a89c04a1da2b1`: "dillon" onboarding store has convention discussions
