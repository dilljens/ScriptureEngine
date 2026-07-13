# Findings: Full Codebase Audit

## Baseline State (collected 2026-07-13)

### Codebase Profile
| Metric | Value |
|--------|-------|
| Python files | 276 |
| JS/JSX files (frontend/src) | 98 |
| Go files | 12 |
| Convention violations | 129 (82 errors, 47 warnings) |
| Ruff errors | 5969 (3207 auto-fixable) |
| MyPy | Configured strict but binary not installed |
| DB | 2GB SQLite production DB at data/processed/scripture.db |

### Test Results
| Test | Status | Time |
|------|--------|------|
| test_verses.py | ✅ 14 passed | 29s |
| test_search.py | ✅ included above | — |
| test_openapi_snapshot.py | ✅ 1 passed | 0.15s |
| test_health.py | ⏭️ skipped (needs SCRIPTURE_TEST_LIVE=1) | — |
| test_graph.py | ⏰ timed out >60s | — |
| test_db_schema.py | ⏰ timed out >60s | — |
| scripts/test_graph_regression.py | ⏰ timed out >30s | — |
| Go tests | ⏰ timed out >60s | — |

### Ruff Error Breakdown (Top 20)
| Code | Count | Fixable | Severity |
|------|-------|---------|----------|
| W293 blank-line-whitespace | 2533 | ✅ auto | style |
| E501 line-too-long | 1874 | ❌ | style |
| F401 unused-import | 310 | ✅ auto | quality |
| I001 unsorted-imports | 308 | ✅ auto | style |
| W291 trailing-whitespace | 138 | ✅ auto | style |
| E401 multi-imports-on-one-line | 112 | ✅ auto | style |
| F541 f-string-missing-placeholders | 100 | ✅ auto | bug |
| F841 unused-variable | 93 | ✅ auto | quality |
| E722 bare-except | 81 | ❌ | **bug** |
| E701 multi-stmts-on-one-line-colon | 79 | ❌ | style |
| B007 unused-loop-control-var | 38 | ❌ | quality |
| invalid-syntax | 31 | ❌ | **bug** |
| UP045 non-pep604-annotation | 28 | ✅ auto | style |
| E741 ambiguous-variable-name | 24 | ❌ | quality |
| F821 undefined-name | 23 | ❌ | **bug** |
| SIM108 if-else-block-instead-of-if-exp | 23 | ❌ | style |
| E402 module-import-not-at-top | 22 | ❌ | quality |
| N806 non-lowercase-var-in-function | 22 | ❌ | quality |
| SIM105 suppressible-exception | 20 | ❌ | quality |
| B033 duplicate-value | 19 | ❌ | **bug** |

### Known Bugs Found in Baseline
1. **Duplicate Operation IDs** in OpenAPI — 3 routes collide (client_error_log, get_client_logs, debug_check)
2. **FastAPI `on_event` deprecated** — should use lifespan handlers
3. **31 invalid-syntax errors** — files with actual syntax errors
4. **23 undefined-name (F821)** — could be runtime NameErrors
5. **10 duplicate dict keys (F601)** — last value silently wins (bugs)
6. **81 bare except** — catches KeyboardInterrupt/SystemExit
7. **4 raise-without-from (B904)** — loses exception chain context
