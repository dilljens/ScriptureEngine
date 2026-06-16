#!/usr/bin/env bash
# Scripture Knowledge Engine — convenience commands
# Usage: ./run.sh <command> [args]

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-help}" in
  ingest)
    python3 "$DIR/scripts/ingest.py"
    ;;
  seed)
    python3 "$DIR/scripts/seed_known_patterns.py"
    ;;
  verse)
    shift
    python3 "$DIR/tools/verse.py" "$@"
    ;;
  search)
    shift
    python3 "$DIR/tools/search.py" "$@"
    ;;
  gematria)
    shift
    python3 "$DIR/tools/gematria.py" "$@"
    ;;
  patterns)
    shift
    python3 "$DIR/tools/patterns.py" "$@"
    ;;
  connections)
    shift
    python3 "$DIR/tools/connections.py" "$@"
    ;;
  intertext)
    shift
    python3 "$DIR/tools/intertext.py" "$@"
    ;;
  frequency)
    shift
    python3 "$DIR/tools/frequency.py" "$@"
    ;;
  compare)
    shift
    python3 "$DIR/tools/compare.py" "$@"
    ;;
  word_counts)
    shift
    python3 "$DIR/tools/word_counts.py" "$@"
    ;;
  keyword_dist)
    shift
    python3 "$DIR/tools/keyword_distribution.py" "$@"
    ;;
  formulas)
    shift
    python3 "$DIR/tools/structural_formulas.py" "$@"
    ;;
  section_compare)
    shift
    python3 "$DIR/tools/section_compare.py" "$@"
    ;;
  chiasm_scan)
    shift
    python3 "$DIR/tools/chiasm_scan.py" "$@"
    ;;
  known_patterns)
    shift
    python3 "$DIR/tools/known_patterns.py" "$@"
    ;;
  pattern_ingest)
    shift
    python3 "$DIR/tools/pattern_ingest.py" "$@"
    ;;
  guide)
    shift
    python3 "$DIR/tools/guided_study.py" "$@"
    ;;
  layers)
    shift
    python3 "$DIR/tools/layers.py" "$@"
    ;;
  generate)
    shift
    python3 "$DIR/scripts/generate_connections.py" "$@"
    ;;
  skeptic)
    shift
    python3 "$DIR/tools/skeptic.py" "$@"
    ;;
  audit)
    shift
    python3 "$DIR/tools/audit.py" "$@"
    ;;
  validate)
    python3 "$DIR/scripts/validate_connections.py"
    ;;
  cleanup)
    shift
    python3 "$DIR/scripts/cleanup_connections.py" "$@"
    ;;
  web)
    cd "$DIR/web"
    if [ -f "$DIR/.venv/bin/python3" ]; then
      "$DIR/.venv/bin/python3" -m uvicorn server:app --port 8000 --host 0.0.0.0
    else
      python3 -m uvicorn server:app --port 8000 --host 0.0.0.0
    fi
    ;;
  embed)
    if [ -f "$DIR/.venv/bin/python3" ]; then
      "$DIR/.venv/bin/python3" "$DIR/scripts/embed_verses.py" "$@"
    else
      python3 "$DIR/scripts/embed_verses.py" "$@"
    fi
    ;;
  xlingual)
    shift
    python3 "$DIR/tools/search_xlingual.py" "$@"
    ;;
  info)
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DIR/data/processed/scripture.db')
conn.row_factory = sqlite3.Row
v = conn.execute('SELECT COUNT(*) as c FROM verses').fetchone()['c']
h = conn.execute('SELECT COUNT(*) as c FROM verses WHERE has_hebrew=1').fetchone()['c']
g = conn.execute('SELECT COUNT(*) as c FROM gematria').fetchone()['c']
cn = conn.execute('SELECT COUNT(*) as c FROM connections').fetchone()['c']
dn = conn.execute('SELECT COUNT(*) as c FROM divine_names').fetchone()['c']
kc = conn.execute('SELECT COUNT(*) as c FROM known_chiasms').fetchone()['c']
sf = conn.execute('SELECT COUNT(*) as c FROM structural_formulas').fetchone()['c']
print(f'Verses: {v:,}  Hebrew: {h:,}  Gematria words: {g:,}  Connections: {cn:,}  Divine names: {dn}')
print(f'Known chiasms: {kc}  Structural formulas: {sf}')
qc = conn.execute('SELECT quality_level, COUNT(*) as c FROM connections GROUP BY quality_level ORDER BY quality_level').fetchall()
print('Quality:', {r[\"quality_level\"]: r[\"c\"] for r in qc})
conn.close()
"
    ;;
  test)
    echo "=== Test: Genesis 1:1 ==="
    python3 "$DIR/tools/verse.py" '{"book": "gen", "chapter": 1, "verse": 1}' | python3 -c "import sys,json; d=json.load(sys.stdin); gt=d.get('gematria_totals',{}) or {}; print(f'  {d[\"reference\"]}: {d[\"text_english\"][:60]}...\n  Hebrew: {d[\"text_hebrew\"][:40] if d[\"text_hebrew\"] else \"none\"}...\n  Gematria words: {len(d.get(\"gematria_words\",[]))}, Total: {gt.get(\"total_std\",0)}')"
    
    echo "=== Test: YHWH Gematria ==="
    python3 "$DIR/tools/gematria.py" '{"word": "יהוה"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  YHWH = {d[\"gematria\"][\"standard\"]} (standard), matches: {[m[\"name\"] for m in d[\"divine_name_matches\"]]}')"
    
    echo "=== Test: Isaiah 6 Patterns ==="
    result=$(python3 "$DIR/tools/patterns.py" '{"book": "isa", "chapter": 6}')
    chiasm_count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('chiasms',[])))")
    para_count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('parallelisms',[])))")
    echo "  Detected $chiasm_count chiasms, $para_count parallelisms in Isaiah 6"
    
    echo "=== Test: Gen 1:1 vs John 1:1 ==="
    python3 "$DIR/tools/compare.py" '{"verse_a": "gen.1.1", "verse_b": "john.1.1"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Gen 1:1 gematria: {d[\"verse_a\"][\"total_gematria_standard\"]}, John 1:1 gematria: {d[\"verse_b\"][\"total_gematria_standard\"]}')"
    
    echo "=== Test: Genesis Word Counts ==="
    python3 "$DIR/tools/word_counts.py" '{"book": "gen", "mode": "per_chapter"}' | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('signals',{}); print(f'  Chapters: {d[\"chapter_count\"]}, Total words: {d[\"total_word_count\"]}'); print(f'  First/last ratio: {s.get(\"first_last_ratio\",{}).get(\"ratio\",\"N/A\")}')"
    
    echo "=== Test: Genesis Chiasm Scan ==="
    python3 "$DIR/tools/chiasm_scan.py" '{"book": "gen"}' | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('summary',{}); print(f'  Candidates: {s.get(\"total_candidates\",0)}, Best score: {s.get(\"top_candidate_score\",0)}')"
    
    echo "=== Test: Known Patterns (Welch) ==="
    python3 "$DIR/tools/known_patterns.py" '{"scholar": "welch"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Welch: {d[\"total_patterns\"]} patterns')"
    
    echo "=== Test: Known Patterns (Giliadi) ==="
    python3 "$DIR/tools/known_patterns.py" '{"scholar": "giliadi"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Giliadi: {d[\"total_patterns\"]} patterns')"
    
    echo "=== Test: Genesis Structural Formulas ==="
    python3 "$DIR/tools/structural_formulas.py" '{"book": "gen"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Formulas: {d[\"total_markers\"]} markers, types: {list(d[\"by_type\"].keys())}')"
    
    echo ""
    echo "=== ALL TESTS PASSED ==="
    ;;
  *)
    echo "Scripture Knowledge Engine"
    echo ""
    echo "Core tools:"
    echo "  ingest             — Import/refresh all data"
    echo "  seed               — Seed known patterns from scholars"
    echo "  verse <json>       — Look up a verse"
    echo "  search <json>      — Search by keyword"
    echo "  gematria <json>    — Gematria lookup"
    echo "  patterns <json>    — Detect literary patterns"
    echo "  connections <json> — Get typed connections"
    echo "  intertext <json>   — Trace intertextual links"
    echo "  frequency <json>   — Word frequency analysis"
    echo "  compare <json>     — Compare two verses"
    echo ""
    echo "Chiasm detection tools:"
    echo "  word_counts <json>      — Hebrew word counts per chapter/section"
    echo "  keyword_dist <json>     — Key term distribution across book"
    echo "  formulas <json>         — Structural formula markers"
    echo "  section_compare <json>  — Compare two sections"
    echo "  chiasm_scan <json>      — Algorithmic chiastic pre-scan"
    echo ""
    echo "Pattern management:"
    echo "  known_patterns <json>   — Query known patterns"
    echo "  pattern_ingest <json>   — Save discovered pattern"
    echo ""
    echo "Layer tools:"
    echo "  layers <json>           — Multi-layer connection viewer
  skeptic <json>          — Quality-filtered connections
  audit <json>            — Connection provenance audit"
    echo "  generate                — Run all connection generators
  validate                — Revalidate connections against null-text controls"
    echo ""
    echo "  info                    — Database stats"
    echo "  test                    — Run smoke tests"
    echo ""
    echo "Examples:"
    echo "  ./run.sh verse '{\"book\": \"gen\", \"chapter\": 1, \"verse\": 1}'"
    echo "  ./run.sh gematria '{\"word\": \"יהוה\"}'"
    echo "  ./run.sh chiasm_scan '{\"book\": \"gen\"}'"
    echo "  ./run.sh known_patterns '{\"scholar\": \"welch\"}'"
    echo "  ./run.sh compare '{\"verse_a\": \"gen.1.1\", \"verse_b\": \"john.1.1\"}'"
    echo "  ./run.sh layers '{\"verse\": \"isa.6.1\"}'"
    echo "  ./run.sh layers '{\"stats\": true}'"
    echo "  ./run.sh generate --list"
    echo "  ./run.sh info"
    echo "  ./run.sh test"
    ;;
esac
