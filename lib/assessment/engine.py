"""Adaptive assessment engine — selects items, updates state, terminates."""

import math
import random
from .models import BLIM, KnowledgeState


class AssessmentEngine:
    """Drives an adaptive assessment session."""

    def __init__(self, conn):
        self.conn = conn
        self.items_cache = {}  # item_id -> (difficulty, discrimination, guess, slip, layer, type)

    def _load_item(self, item_id):
        if item_id not in self.items_cache:
            row = self.conn.execute(
                """SELECT id, connection_type, pa_r_de_s_level, difficulty
                   FROM knowledge_items WHERE id = ?""",
                (item_id,)
            ).fetchone()
            if row:
                diff = row["difficulty"]
                # Convert difficulty (1-quality) to IRT scale
                difficulty = (diff - 0.5) * 4  # spread to [-2, 2]
                discrimination = 1.0
                if row["pa_r_de_s_level"] == "remez":
                    discrimination = 1.2
                elif row["pa_r_de_s_level"] == "drash":
                    discrimination = 1.5
                elif row["pa_r_de_s_level"] == "sod":
                    discrimination = 2.0
                self.items_cache[item_id] = {
                    "difficulty": difficulty,
                    "discrimination": discrimination,
                    "guess": 0.15,
                    "slip": 0.10,
                    "layer": row["pa_r_de_s_level"],
                    "type": row["connection_type"],
                }
        return self.items_cache.get(item_id)

    def _get_blim(self, item_id):
        params = self._load_item(item_id)
        if not params:
            return None
        return BLIM(
            difficulty=params["difficulty"],
            discrimination=params["discrimination"],
            guess=params["guess"],
            slip=params["slip"],
        )

    def select_item(self, state, target_layer=None, n_candidates=50):
        """Select the most informative next item.

        Uses maximum information criterion + outer fringe boost.

        Args:
            state: KnowledgeState
            target_layer: Optional PaRDeS level filter
            n_candidates: Number of candidate items to consider

        Returns:
            item_id or None if assessment should terminate
        """
        # Build candidate pool
        if target_layer:
            candidates = self.conn.execute(
                """SELECT id FROM knowledge_items WHERE pa_r_de_s_level = ?
                   ORDER BY RANDOM() LIMIT ?""",
                (target_layer, n_candidates)
            ).fetchall()
        else:
            candidates = self.conn.execute(
                """SELECT id FROM knowledge_items
                   ORDER BY RANDOM() LIMIT ?""",
                (n_candidates,)
            ).fetchall()

        if not candidates:
            return None

        # Score each candidate by information gain at current ability
        ability = state.overall_mastery()
        best_item = None
        best_info = -1

        for row in candidates:
            item_id = row["id"]
            blim = self._get_blim(item_id)
            if not blim:
                continue

            info = blim.information(ability)

            # Boost items in outer fringe (near 50% mastery)
            current = state.get_mastery(item_id)
            if 0.3 < current < 0.7:
                info *= 1.5  # fringe boost

            # Boost items never seen before
            if item_id not in state.times_correct and item_id not in state.times_wrong:
                info *= 1.2

            if info > best_info:
                best_info = info
                best_item = item_id

        return best_item

    def assess_response(self, state, item_id, correct):
        """Update knowledge state after a response.

        Args:
            state: KnowledgeState (mutated in place)
            item_id: The item that was answered
            correct: True if correct, False if wrong
        """
        blim = self._get_blim(item_id)
        if not blim:
            return

        prior = state.get_mastery(item_id)
        posterior = blim.update_bayesian(prior, correct)
        state.set_mastery(item_id, posterior)
        state.record_response(item_id, correct)

        # Propagate to prerequisites and postrequisites
        self._propagate(state, item_id, posterior)

    def _propagate(self, state, item_id, mastery):
        """Propagate mastery updates through the prerequisite graph."""
        # Prerequisites: if mastered at >0.8, boost prerequisites
        if mastery > 0.8:
            prereqs = self.conn.execute(
                """SELECT prerequisite_item_id FROM knowledge_prerequisites
                   WHERE item_id = ?""",
                (item_id,)
            ).fetchall()
            for r in prereqs:
                pid = r["prerequisite_item_id"]
                current = state.get_mastery(pid)
                # If well-mastered, prerequisites should be at least 0.5
                new = max(current, 0.5)
                state.set_mastery(pid, new)

        # Postrequisites: if NOT mastered (<0.2), suppress postrequisites
        if mastery < 0.2:
            postreqs = self.conn.execute(
                """SELECT item_id FROM knowledge_prerequisites
                   WHERE prerequisite_item_id = ?""",
                (item_id,)
            ).fetchall()
            for r in postreqs:
                pid = r["item_id"]
                current = state.get_mastery(pid)
                new = min(current, 0.3)
                state.set_mastery(pid, new)

    def should_terminate(self, state, min_items=10, max_items=50, entropy_threshold=0.1):
        """Check if assessment should stop.

        Args:
            state: KnowledgeState
            min_items: Minimum items before termination allowed
            max_items: Hard maximum
            entropy_threshold: Stop when average entropy below this

        Returns:
            (should_stop, reason)
        """
        total = len(state.times_correct) + len(state.times_wrong)

        if total < min_items:
            return False, f"minimum ({total}/{min_items})"

        if total >= max_items:
            return True, f"maximum ({total})"

        # Check entropy of mastered items
        probs = list(state.mastery_prob.values())
        if probs:
            # Average entropy across all items
            entropies = []
            for p in probs:
                if 0 < p < 1:
                    e = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
                    entropies.append(e)
            if entropies:
                avg_entropy = sum(entropies) / len(entropies)
                if avg_entropy < entropy_threshold:
                    return True, f"converged (entropy={avg_entropy:.3f})"

        return False, f"in progress ({total} items)"

    def get_outer_fringe(self, state, limit=10):
        """Items the user is ready to learn next (mastery ~0.3-0.7)."""
        fringe = []
        for item_id_str, prob in state.mastery_prob.items():
            item_id = int(item_id_str)
            if 0.3 <= prob <= 0.7:
                row = self.conn.execute(
                    """SELECT connection_type, pa_r_de_s_level, verse_id, target_verse
                       FROM knowledge_items WHERE id = ?""",
                    (item_id,)
                ).fetchone()
                if row:
                    fringe.append({
                        "item_id": item_id,
                        "mastery": prob,
                        "type": row["connection_type"],
                        "layer": row["pa_r_de_s_level"],
                        "verse": row["verse_id"],
                        "target": row["target_verse"],
                    })
        fringe.sort(key=lambda x: abs(x["mastery"] - 0.5))
        return fringe[:limit]

    def run_session(self, state, target_layer=None, max_items=20):
        """Run a full assessment session.

        Args:
            state: KnowledgeState
            target_layer: Optional PaRDeS level filter
            max_items: Maximum items to administer

        Returns:
            list of (item_id, was_correct) responses
        """
        session = []
        for _ in range(max_items):
            item_id = self.select_item(state, target_layer=target_layer)
            if item_id is None:
                break

            # For simulation: assume 70% chance correct at ability 0.5
            # In real use, the MCP tool would present the question to the user
            ability = state.overall_mastery()
            blim = self._get_blim(item_id)
            p_correct = blim.p_correct(ability) if blim else 0.7
            was_correct = random.random() < p_correct

            self.assess_response(state, item_id, was_correct)
            session.append((item_id, was_correct))

            should_stop, reason = self.should_terminate(state, min_items=5, max_items=max_items)
            if should_stop:
                break

        return session
