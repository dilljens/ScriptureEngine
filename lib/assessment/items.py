"""Assessment item generation from knowledge domain."""

import json
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.db import get_db


class ItemGenerator:
    """Generates assessment questions from knowledge items."""

    def __init__(self, conn):
        self.conn = conn
        self.pardes_levels = ["p'shat", "remez", "drash", "sod"]

    def generate_mc_question(self, item):
        """Multiple choice: which verse connects to this one?

        Args:
            item: dict from knowledge_items row

        Returns:
            dict with question data
        """
        source = item["verse_id"]
        target = item["target_verse"]
        conn_type = item["connection_type"]
        layer = item["pa_r_de_s_level"]

        source_book = source.split(".")[0]

        distractors = self.conn.execute(
            """SELECT DISTINCT target_verse FROM knowledge_items
               WHERE verse_id = ? AND connection_type = ? AND target_verse != ?
               ORDER BY RANDOM() LIMIT 3""",
            (source, conn_type, target)
        ).fetchall()
        distractor_verses = [r["target_verse"] for r in distractors]

        while len(distractor_verses) < 3:
            extra = self.conn.execute(
                """SELECT target_verse FROM knowledge_items
                   WHERE verse_id LIKE ? AND target_verse != ?
                   ORDER BY RANDOM() LIMIT ?""",
                (f"{source_book}.%", target, 3 - len(distractor_verses))
            ).fetchall()
            for r in extra:
                if r["target_verse"] not in distractor_verses and r["target_verse"] != target:
                    distractor_verses.append(r["target_verse"])

        options = [target] + distractor_verses[:3]
        random.shuffle(options)

        return {
            "type": "multiple_choice",
            "knowledge_item_id": item["id"],
            "question": f"Which verse connects to {source} via a {conn_type} connection?",
            "options": options,
            "correct_answer": target,
            "layer": layer,
            "bloom_level": item.get("bloom_level", "remember"),
        }

    def generate_tf_question(self, item, fake_pair=None):
        """True/False: does this connection exist?

        Args:
            item: dict from knowledge_items row
            fake_pair: optional (source, target, type) for a FALSE question

        Returns:
            dict with question data
        """
        if fake_pair:
            source, target, conn_type = fake_pair
            is_true = False
        else:
            source = item["verse_id"]
            target = item["target_verse"]
            conn_type = item["connection_type"]
            is_true = True

        return {
            "type": "true_false",
            "knowledge_item_id": item["id"] if is_true else None,
            "question": f"Is there a {conn_type} connection between {source} and {target}?",
            "correct_answer": is_true,
            "layer": item["pa_r_de_s_level"] if not fake_pair else random.choice(["p'shat", "remez"]),
            "bloom_level": item.get("bloom_level", "remember"),
        }

    def generate_classification_question(self, item):
        """PaRDeS classification: what level is this connection?"""
        source = item["verse_id"]
        target = item["target_verse"]
        conn_type = item["connection_type"]
        correct = item["pa_r_de_s_level"]

        wrong = [l for l in self.pardes_levels if l != correct]
        options = [correct] + wrong
        random.shuffle(options)

        return {
            "type": "classification",
            "knowledge_item_id": item["id"],
            "question": f"What PaRDeS level is the {conn_type} connection between {source} and {target}?",
            "options": options,
            "correct_answer": correct,
            "layer": correct,
            "bloom_level": "analyze",
        }

    def generate_all(self, limit_per_type=2000, mc_ratio=0.5, tf_ratio=0.3, cl_ratio=0.2):
        """Generate a set of assessment items from the knowledge domain."""
        items = []

        all_items = self.conn.execute(
            """SELECT id, verse_id, connection_type, target_verse,
                      pa_r_de_s_level, layer, difficulty, bloom_level
               FROM knowledge_items
               WHERE difficulty >= 0.3
               ORDER BY RANDOM()"""
        ).fetchall()

        total_target = int(limit_per_type)
        mc_count = int(total_target * mc_ratio)
        tf_count = int(total_target * tf_ratio)
        cl_count = total_target - mc_count - tf_count

        for row in all_items:
            if len(items) >= mc_count:
                break
            try:
                q = self.generate_mc_question(dict(row))
                if q and len(q.get("options", [])) >= 4:
                    items.append(q)
            except Exception:
                continue

        tf_true_count = 0
        for row in all_items:
            if len(items) >= mc_count + tf_count:
                break
            if tf_true_count < tf_count // 2:
                try:
                    q = self.generate_tf_question(dict(row))
                    items.append(q)
                    tf_true_count += 1
                except Exception:
                    continue

        fake_sources = self.conn.execute(
            """SELECT DISTINCT verse_id FROM knowledge_items
               ORDER BY RANDOM() LIMIT 200"""
        ).fetchall()
        for s in fake_sources:
            if len(items) >= mc_count + tf_count:
                break
            existing_targets = set(
                r["target_verse"] for r in
                self.conn.execute(
                    "SELECT target_verse FROM knowledge_items WHERE verse_id = ?",
                    (s["verse_id"],)
                ).fetchall()
            )
            rand_target = self.conn.execute(
                "SELECT id FROM verses WHERE id != ? ORDER BY RANDOM() LIMIT 1",
                (s["verse_id"],)
            ).fetchone()
            if rand_target and rand_target["id"] not in existing_targets:
                fake_item = {
                    "id": -1,
                    "pa_r_de_s_level": random.choice(["p'shat", "remez"]),
                    "bloom_level": "remember",
                }
                q = self.generate_tf_question(
                    fake_item,
                    fake_pair=(s["verse_id"], rand_target["id"],
                               random.choice(["same_lemma", "direct_quotation", "same_root"]))
                )
                items.append(q)

        for row in all_items:
            if len(items) >= total_target:
                break
            try:
                q = self.generate_classification_question(dict(row))
                items.append(q)
            except Exception:
                continue

        return items


def build_assessment_items(conn=None, limit=5000):
    """Build and store assessment items."""
    if conn is None:
        conn = get_db()

    generator = ItemGenerator(conn)
    items = generator.generate_all(limit_per_type=limit)

    conn.execute("""CREATE TABLE IF NOT EXISTS assessment_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        knowledge_item_id INTEGER,
        question_type TEXT NOT NULL,
        question_text TEXT NOT NULL,
        options_json TEXT DEFAULT '[]',
        correct_answer TEXT NOT NULL,
        layer TEXT NOT NULL,
        bloom_level TEXT DEFAULT 'remember',
        difficulty REAL DEFAULT 0.5,
        discrimination REAL DEFAULT 1.0,
        guess_param REAL DEFAULT 0.15,
        slip_param REAL DEFAULT 0.10,
        source_knowledge_item_id INTEGER
    )""")

    conn.execute("DELETE FROM assessment_items")

    count = 0
    for item in items:
        options_json = json.dumps(item.get("options", []))
        conn.execute(
            """INSERT INTO assessment_items
               (knowledge_item_id, question_type, question_text, options_json, correct_answer,
                layer, bloom_level, difficulty, discrimination, guess_param, slip_param)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.get("knowledge_item_id"),
                item["type"],
                item["question"],
                options_json,
                str(item["correct_answer"]),
                item.get("layer", "p'shat"),
                item.get("bloom_level", "remember"),
                0.5, 1.0, 0.15, 0.10,
            )
        )
        count += 1

    conn.commit()
    return count


if __name__ == "__main__":
    conn = get_db()
    count = build_assessment_items(conn, limit=5000)
    print(f"Built {count} assessment items")

    samples = conn.execute(
        "SELECT question_type, question_text, correct_answer FROM assessment_items LIMIT 5"
    ).fetchall()
    for s in samples:
        print(f"  [{s['question_type']}] {s['question_text'][:70]} -> {str(s['correct_answer'])[:30]}")

    conn.close()
