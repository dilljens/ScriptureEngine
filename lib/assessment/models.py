"""Data models for the assessment system."""

import math


class KnowledgeState:
    """Represents a user's knowledge state across items."""

    def __init__(self, user_id=None):
        self.user_id = user_id
        # mastery_prob[item_id] = P(mastered) ∈ [0, 1]
        self.mastery_prob = {}
        # times_correct[item_id] = count
        self.times_correct = {}
        # times_wrong[item_id] = count
        self.times_wrong = {}

    def get_mastery(self, item_id):
        return self.mastery_prob.get(item_id, 0.0)

    def set_mastery(self, item_id, prob):
        self.mastery_prob[item_id] = max(0.0, min(1.0, prob))

    def record_response(self, item_id, correct, correctness=1.0):
        """Record a response with optional partial credit.

        Args:
            item_id: The item answered
            correct: Boolean True/False for simple scoring
            correctness: Float 0.0–1.0 for partial credit (default: 1.0 if correct, 0.0 if not)
        """
        if correct:
            self.times_correct[item_id] = self.times_correct.get(item_id, 0) + 1
        else:
            # For partial credit, record fractional correctness
            if correctness < 0.5:
                self.times_wrong[item_id] = self.times_wrong.get(item_id, 0) + 1
            # Between 0.5 and 1.0, it's partially correct — count in both
            if correctness > 0.0 and correctness < 1.0:
                self.times_correct[item_id] = self.times_correct.get(item_id, 0) + correctness
                self.times_wrong[item_id] = self.times_wrong.get(item_id, 0) + (1.0 - correctness)

    def overall_mastery(self):
        if not self.mastery_prob:
            return 0.0
        return sum(self.mastery_prob.values()) / len(self.mastery_prob)

    def mastery_by_layer(self, conn):
        """Group mastery by PaRDeS level."""
        if not self.mastery_prob:
            return {}
        result = {}
        for item_id_str, prob in self.mastery_prob.items():
            item_id = int(item_id_str) if not isinstance(item_id_str, int) else item_id_str
            row = conn.execute(
                "SELECT pa_r_de_s_level FROM knowledge_items WHERE id = ?",
                (item_id,)
            ).fetchone()
            if row:
                level = row["pa_r_de_s_level"]
                if level not in result:
                    result[level] = []
                result[level].append(prob)
        return {k: sum(v) / len(v) for k, v in result.items()}


class BLIM:
    """Basic Local Independence Model for item response.

    Each item has:
    - difficulty (β): higher = harder
    - discrimination (α): how well it separates ability levels
    - guess (g): P(correct | not mastered) — lower ability guessing correctly
    - slip (s): P(wrong | mastered) — higher ability slipping
    """

    def __init__(self, difficulty=0.0, discrimination=1.0, guess=0.15, slip=0.10):
        self.difficulty = difficulty
        self.discrimination = discrimination
        self.guess = guess
        self.slip = slip

    def p_correct(self, ability):
        """Probability of correct response given ability θ."""
        # 2PL IRT model: P(correct) = guess + (1 - guess - slip) * logistic(α(θ - β))
        logit = self.discrimination * (ability - self.difficulty)
        p = 1.0 / (1.0 + math.exp(-logit))
        return self.guess + (1.0 - self.guess - self.slip) * p

    def information(self, ability):
        """Fisher information at ability θ — how useful this item is."""
        p = self.p_correct(ability)
        q = 1.0 - p
        if p <= 0 or q <= 0:
            return 0.0
        # Derivative of P with respect to θ
        logit = self.discrimination * (ability - self.difficulty)
        p_star = 1.0 / (1.0 + math.exp(-logit))
        dp = self.discrimination * p_star * (1.0 - p_star)
        info = (dp ** 2) / (p * q)
        return info

    def update_bayesian(self, prior_mastery, response_correct, correctness=1.0):
        """Bayesian update of mastery probability given item response.

        Supports partial credit via `correctness` (0.0–1.0).
        For correctness = 0.0, acts as pure wrong. For correctness = 1.0, acts as pure correct.
        For intermediate values, interpolates between the two posteriors.

        Args:
            prior_mastery: P(mastered) before this response
            response_correct: Boolean True/False for simple scoring
            correctness: Float 0.0–1.0 for partial credit weighting (default 1.0)

        Returns:
            posterior_mastery: P(mastered | response)
        """
        # P(correct | mastered) = 1 - slip
        p_correct_given_mastery = 1.0 - self.slip
        # P(correct | not mastered) = guess
        p_correct_given_not = self.guess

        # Compute posterior for CORRECT response
        p_correct = (p_correct_given_mastery * prior_mastery +
                     p_correct_given_not * (1.0 - prior_mastery))
        if p_correct == 0:
            posterior_correct = prior_mastery
        else:
            posterior_correct = (p_correct_given_mastery * prior_mastery) / p_correct

        # Compute posterior for WRONG response
        p_wrong = (self.slip * prior_mastery +
                   (1.0 - self.guess) * (1.0 - prior_mastery))
        posterior_wrong = prior_mastery if p_wrong == 0 else self.slip * prior_mastery / p_wrong

        # Interpolate between correct and wrong based on correctness weight
        posterior = posterior_correct * correctness + posterior_wrong * (1.0 - correctness)

        return max(0.01, min(0.99, posterior))
