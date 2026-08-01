#!/bin/bash
# Seed all Hebrew lesson content in the correct order.
# Specialized seeders run first (INSERT OR IGNORE creates their content).
# seed_hebrew_content.py runs last (INSERT OR REPLACE for its 80+ curated
# lessons; INSERT OR IGNORE for the rest — won't overwrite specialized content).
#
# Usage:
#   bash scripts/seed_hebrew_all.sh
#   bash scripts/seed_hebrew_all.sh --reset  # Full rebuild

set -euo pipefail
cd "$(dirname "$0")/.."

RESET=""
DB="data/memorize.db"

for arg in "$@"; do
    if [ "$arg" == "--reset" ]; then
        RESET="--reset"
    elif [ "${arg#--db=}" != "$arg" ]; then
        DB="${arg#--db=}"
    fi
done

if [ "$RESET" == "--reset" ]; then
    echo "=== Full reset: dropping existing lesson content ==="
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB')
conn.execute('DELETE FROM hebrew_lessons')
conn.execute('DELETE FROM hebrew_practice_items')
conn.commit()
conn.close()
print('  Cleared hebrew_lessons and hebrew_practice_items')
"
fi

echo "=== Seeding Hebrew Lesson Content ==="
echo "DB: $DB"

echo ""
echo "[1/11] Vocabulary lessons (500+ frequency-ranked words)..."
python3 scripts/seed_hebrew_vocabulary.py --db "$DB"

python3 scripts/align_hebrew_vocabulary.py --db "$DB"
python3 scripts/repair_vocabulary_metadata.py --db "$DB"

# Existing databases may predate the practice-item uniqueness invariant.
python3 scripts/repair_hebrew_learning_content.py --db "$DB"

echo ""
echo "[2/11] Grammar lessons (begadkefat, clauses, etc.)..."
python3 scripts/seed_hebrew_grammar.py --db "$DB"

echo ""
echo "[3/11] Phrase lessons (formulaic expressions)..."
python3 scripts/seed_hebrew_phrases.py --db "$DB"

echo ""
echo "[4/11] Root lessons (triconsonantal root families)..."
python3 scripts/seed_hebrew_roots.py --db "$DB"

echo ""
echo "[5/11] Graded reading progression (Bullard ETCBC-ordered chapters)..."
python3 scripts/seed_hebrew_reading.py --db "$DB"

echo ""
echo "[6/11] Lesson content builder (curated letters/vowels + fills gaps)..."
python3 scripts/seed_hebrew_content.py --db "$DB"

echo ""
echo "[7/11] Vocabulary examples are retained only when already source-validated..."

echo ""
echo "[8/11] Production practice items (cloze, free recall)..."
python3 scripts/seed_hebrew_production.py --db "$DB"

echo ""
echo "[9/11] Masoretic reading skills..."
python3 scripts/seed_hebrew_masoretic_reading.py --db "$DB"

echo ""
echo "[10/11] Quarantine non-OT examples and remove invalid generated practice..."
python3 scripts/repair_hebrew_learning_content.py --db "$DB"

echo ""
echo "[11/11] Validate learning content..."
python3 scripts/validate_hebrew_learning_content.py --db "$DB"

echo ""
echo "=== Done ==="

# Quick verification
echo ""
echo "=== Quick Stats ==="
python3 -c "
import sqlite3, json
conn = sqlite3.connect('$DB')
conn.row_factory = sqlite3.Row

lessons = conn.execute('SELECT COUNT(*) as c FROM hebrew_lessons').fetchone()['c']
practice = conn.execute('SELECT COUNT(*) as c FROM hebrew_practice_items').fetchone()['c']
nodes = conn.execute('SELECT COUNT(*) as c FROM hebrew_nodes').fetchone()['c']

# Count non-generic lessons (explanations that aren't the fallback text)
generic_count = 0
detail_count = 0
for r in conn.execute('SELECT node_id, content_json FROM hebrew_lessons'):
    try:
        lesson = json.loads(r['content_json'])
        exp = lesson.get('explanation', '')
        if 'key concept in Biblical Hebrew' in exp:
            generic_count += 1
        else:
            detail_count += 1
    except:
        generic_count += 1

print(f'  Nodes: {nodes}')
print(f'  Lessons: {lessons}')
print(f'    - Detailed: {detail_count}')
print(f'    - Generic (placeholder): {generic_count}')
print(f'  Practice items: {practice}')

# Practice items by type
types = conn.execute('SELECT question_type, COUNT(*) as c FROM hebrew_practice_items GROUP BY question_type ORDER BY c DESC').fetchall()
for r in types:
    print(f'    {r[\"question_type\"]:20s} {r[\"c\"]}')

conn.close()
"
